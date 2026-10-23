import asyncio
import time
from typing import Annotated, Any, Literal

import cohere
from cohere.core import ApiError
from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from fastmcp.utilities.logging import get_logger
from httpx import TimeoutException
from mcp.types import ToolAnnotations
from pydantic import Field

from welfare_service_recommendation_mcp.client import WelfareClient
from welfare_service_recommendation_mcp.config import LOG_LEVEL, MODEL_NAME, PORT
from welfare_service_recommendation_mcp.exceptions import (
    WelfareApiError,
    WelfareApiInvalidParameter,
    WelfareApiRateLimited,
    WelfareApiTimeout,
)
from welfare_service_recommendation_mcp.models import (
    LABEL_TO_CODE,
    District,
    HouseholdType,
    InterestTheme,
    LifeCycle,
    LocalGovernmentWelfare,
    LocalGovernmentWelfareDetailed,
    NationalWelfare,
    NationalWelfareDetailed,
    Province,
)
from welfare_service_recommendation_mcp.utils import format_options, get_elapsed_ms

logger = get_logger(__name__)

mcp = FastMCP(name="복지서비스 추천 MCP 서버", mask_error_details=True)

welfare_client = WelfareClient()
cohere_client = cohere.AsyncClientV2(timeout=10.0)


@mcp.tool(
    description="""
사용자 조건에 맞는 중앙부처 및 지자체 복지서비스를 검색합니다.

사용 조건
- 사용자 조건에 맞는 복지서비스를 조회할 때 사용합니다.
- 특정 복지서비스의 서비스 ID를 조회할 때 사용합니다.

사용 방법
- 검색어(search_word)는 핵심 키워드 1개만 사용합니다.
- 사용자가 제공한 정보를 바탕으로 검색 필터(life_cycle, household_type, interest_theme, \
province, district)의 허용값 중 가장 적합한 값을 선택합니다.
- 사용자가 제공한 정보만으로 값을 판단할 수 없는 필터는 임의로 추측하지 않고 생략합니다.
- 사용자가 제공한 정보가 없거나 부족한 경우, 추가 질문을 통해 필요한 정보를 파악한 뒤 검색합니다.
- 나이(age)는 사용자의 정확한 나이가 확인된 경우에만 사용합니다.
- 특정 복지서비스를 조회하는 경우, 서비스명을 검색어로 사용하고 검색 필터는 사용하지 않습니다.

주의 사항
- 사용자 조건에 맞는 복지서비스를 검색한 경우, 반드시 rank_candidates로 우선순위를 정한 뒤 안내합니다.
- 검색어가 너무 구체적이거나 검색 필터가 많으면 검색 결과가 나타나지 않을 수 있습니다.
- 검색 결과가 없거나 5개 미만인 경우, 검색어를 바꾸거나 검색 필터를 줄여 다시 검색합니다.
- 그래도 결과가 없으면 검색어를 제외하고 검색 필터만 사용해 다시 검색합니다.
- 검색은 최대 5회까지 시도합니다.
""".strip(),
    annotations=ToolAnnotations(
        title="복지서비스 검색",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_welfare_list(
    search_word: Annotated[
        str | None,
        Field(description='검색어 (예: "취업", "저축", "청년내일저축계좌")'),
    ] = None,
    life_cycle: Annotated[
        LifeCycle | None,
        Field(
            description=("생애주기\n" + format_options(LABEL_TO_CODE["life_cycle"])),
        ),
    ] = None,
    household_type: Annotated[
        HouseholdType | None,
        Field(
            description=(
                "가구상황\n" + format_options(LABEL_TO_CODE["household_type"])
            ),
        ),
    ] = None,
    interest_theme: Annotated[
        InterestTheme | None,
        Field(
            description=(
                "관심주제\n" + format_options(LABEL_TO_CODE["interest_theme"])
            ),
        ),
    ] = None,
    age: Annotated[
        int | None,
        Field(description="나이"),
    ] = None,
    province: Annotated[
        Province | None,
        Field(description='시도명 (예: "서울특별시", "강원특별자치도")'),
    ] = None,
    district: Annotated[
        District | None,
        Field(description='시군구명 (예: "강릉시", "양양군", "서초구")'),
    ] = None,
    scope: Annotated[
        Literal["both", "national", "local"],
        Field(
            description=(
                "검색 범위\n"
                '- "both": 중앙부처와 지자체 복지서비스 모두 검색\n'
                '- "national": 중앙부처 복지서비스만 검색\n'
                '- "local": 지자체 복지서비스만 검색'
            ),
        ),
    ] = "both",
    ctx: Context = CurrentContext(),
) -> Annotated[
    list[NationalWelfare | LocalGovernmentWelfare],
    Field(description="조회된 복지서비스 목록"),
]:
    start_time = time.perf_counter()
    request_id = ctx.request_id
    params = {
        "search_word": search_word,
        "life_cycle": life_cycle,
        "household_type": household_type,
        "interest_theme": interest_theme,
        "age": age,
        "province": province,
        "district": district,
        "scope": scope,
    }
    params = {key: value for key, value in params.items() if value is not None}

    logger.info("복지서비스 검색 시작: request_id=%s, params=%s", request_id, params)

    life_cycle_code = LABEL_TO_CODE["life_cycle"][life_cycle] if life_cycle else None
    household_type_code = (
        LABEL_TO_CODE["household_type"][household_type] if household_type else None
    )
    interest_theme_code = (
        LABEL_TO_CODE["interest_theme"][interest_theme] if interest_theme else None
    )

    try:
        if scope == "national":
            tasks = [
                welfare_client.get_national_welfare_list(
                    search_word=search_word,
                    life_cycle=life_cycle_code,
                    household_type=household_type_code,
                    interest_theme=interest_theme_code,
                    age=age,
                )
            ]
        elif scope == "local":
            tasks = [
                welfare_client.get_local_welfare_list(
                    search_word=search_word,
                    life_cycle=life_cycle_code,
                    household_type=household_type_code,
                    interest_theme=interest_theme_code,
                    age=age,
                    province=province,
                    district=district,
                )
            ]
        else:
            tasks = [
                welfare_client.get_national_welfare_list(
                    search_word=search_word,
                    life_cycle=life_cycle_code,
                    household_type=household_type_code,
                    interest_theme=interest_theme_code,
                    age=age,
                ),
                welfare_client.get_local_welfare_list(
                    search_word=search_word,
                    life_cycle=life_cycle_code,
                    household_type=household_type_code,
                    interest_theme=interest_theme_code,
                    age=age,
                    province=province,
                    district=district,
                ),
            ]

        results = await asyncio.gather(*tasks)
        services: list[NationalWelfare | LocalGovernmentWelfare] = []

        for result in results:
            services.extend(result)

        logger.info(
            "복지서비스 검색 완료: request_id=%s, count=%d, elapsed_ms=%.0f",
            request_id,
            len(services),
            get_elapsed_ms(start_time),
        )

        if not services:
            return ToolResult(
                content="조회된 복지서비스가 없습니다. 검색어를 바꾸거나 검색 필터를 줄여 다시 시도해 주세요.",
                structured_content={"result": []},
            )

        return services

    except WelfareApiTimeout as e:
        logger.warning(
            "%s 요청 타임아웃: request_id=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 검색 API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except WelfareApiRateLimited as e:
        logger.error(
            "%s 요청 한도 초과: request_id=%s, status_code=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            e.status_code,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 검색 API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except WelfareApiError as e:
        logger.error(
            "%s 응답 에러: request_id=%s, status_code=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            e.status_code,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 검색 API 요청에 실패했습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except Exception as e:
        logger.exception(
            "복지서비스 검색 실패: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError("복지서비스 검색에 실패했습니다.") from e


@mcp.tool(
    description="""
사용자 프로필과 복지서비스 후보를 비교해 관련도순으로 정렬합니다.

사용 조건
- get_welfare_list로 사용자 조건에 맞는 복지서비스를 조회한 뒤 사용합니다.
- 안내할 복지서비스의 우선순위를 정할 때 사용합니다.
- 조회된 복지서비스가 없는 경우엔 사용하지 않습니다.

사용 방법
- 사용자가 제공한 정보를 바탕으로 사용자 프로필(user_profile)을 생성합니다.
- 조회된 복지서비스 중 사용자에게 적합한 후보(candidates)를 선별합니다.
""".strip(),
    annotations=ToolAnnotations(
        title="복지서비스 추천",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def rank_candidates(
    user_profile: Annotated[
        str,
        Field(
            description=("사용자의 상황과 요구사항을 요약한 프로필"),
        ),
    ],
    candidates: Annotated[
        list[NationalWelfare | LocalGovernmentWelfare],
        Field(
            description="조회된 복지서비스 중 사용자에게 적합하다고 판단한 후보 목록"
        ),
    ],
    ctx: Context = CurrentContext(),
) -> Annotated[
    list[dict[str, Any]],
    Field(description="관련도가 높은 순으로 정렬된 복지서비스 추천 목록"),
]:
    start_time = time.perf_counter()
    request_id = ctx.request_id

    logger.info(
        "복지서비스 추천 시작: request_id=%s, count=%d",
        request_id,
        len(candidates),
    )

    try:
        documents: list[str] = []

        for candidate in candidates:
            fields = {
                "서비스명": candidate.name,
                "서비스 요약": candidate.summary,
                "생애주기": candidate.life_cycle,
                "가구상황": candidate.household_type,
                "관심주제": candidate.interest_theme,
                "지원주기": candidate.support_cycle,
                "제공유형": candidate.provision_type,
            }
            text = "\n".join(
                f"{key}: {value}" for key, value in fields.items() if value
            )
            documents.append(text)

        response = await cohere_client.rerank(
            model=MODEL_NAME,
            query=user_profile,
            documents=documents,
        )
        results: list[dict[str, Any]] = []

        for item in response.results:
            candidate = candidates[item.index]
            results.append(
                {
                    **candidate.model_dump(),
                    "score": item.relevance_score,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "복지서비스 추천 완료: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )

        return results

    except TimeoutException as e:
        logger.warning(
            "Cohere Rerank API 요청 타임아웃: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 추천 API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except ApiError as e:
        status_code = e.status_code

        if status_code == 429:
            logger.error(
                "Cohere Rerank API 요청 한도 초과: request_id=%s, status_code=%s, elapsed_ms=%.0f",
                request_id,
                status_code,
                get_elapsed_ms(start_time),
            )
            raise ToolError(
                "복지서비스 추천 API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            ) from e

        logger.error(
            "Cohere Rerank API 응답 에러: request_id=%s, status_code=%s, elapsed_ms=%.0f",
            request_id,
            status_code,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 추천 API 요청에 실패했습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except Exception as e:
        logger.exception(
            "복지서비스 추천 실패: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError("복지서비스 추천에 실패했습니다.") from e


@mcp.tool(
    description="""
중앙부처 및 지자체 복지서비스의 상세 정보를 조회합니다.

사용 조건
- 복지서비스의 지원 대상·선정 기준·신청 방법 등의 상세 정보를 조회할 때 사용합니다.

사용 방법
- 이전 대화에서 서비스 ID(service_id)를 확인할 수 있는 경우, 해당 ID를 그대로 사용합니다.
- 서비스 ID를 확인할 수 없는 경우, get_welfare_list로 서비스 ID를 조회한 뒤 사용합니다.
""".strip(),
    annotations=ToolAnnotations(
        title="복지서비스 상세 조회",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_welfare_detailed(
    service_id: Annotated[str, Field(description="복지서비스 ID")],
    provider: Annotated[
        Literal["national", "local"],
        Field(
            description=('서비스 제공처\n- "national": 중앙부처\n- "local": 지자체'),
        ),
    ],
    ctx: Context = CurrentContext(),
) -> Annotated[
    NationalWelfareDetailed | LocalGovernmentWelfareDetailed,
    Field(description="조회된 복지서비스 상세 정보"),
]:
    start_time = time.perf_counter()
    request_id = ctx.request_id

    logger.info(
        "복지서비스 상세 조회 시작: request_id=%s, service_id=%s, provider=%s",
        request_id,
        service_id,
        provider,
    )

    try:
        if provider == "national":
            service_detail = await welfare_client.get_national_welfare_detail(
                service_id
            )
        else:
            service_detail = await welfare_client.get_local_welfare_detail(service_id)

        logger.info(
            "복지서비스 상세 조회 완료: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )

        return service_detail

    except WelfareApiTimeout as e:
        logger.warning(
            "%s 요청 타임아웃: request_id=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 상세 조회 API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except WelfareApiRateLimited as e:
        logger.error(
            "%s 요청 한도 초과: request_id=%s, status_code=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            e.status_code,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 상세 조회 API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except WelfareApiInvalidParameter as e:
        logger.warning(
            "%s 유효하지 않은 서비스 ID: request_id=%s, service_id=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            service_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "유효하지 않은 서비스 ID입니다. 서비스 ID를 확인한 뒤 다시 시도해 주세요."
        ) from e

    except WelfareApiError as e:
        logger.error(
            "%s 응답 에러: request_id=%s, status_code=%s, elapsed_ms=%.0f",
            e.api_name,
            request_id,
            e.status_code,
            get_elapsed_ms(start_time),
        )
        raise ToolError(
            "복지서비스 상세 조회 API 요청에 실패했습니다. 잠시 후 다시 시도해 주세요."
        ) from e

    except Exception as e:
        logger.exception(
            "복지서비스 상세 조회 실패: request_id=%s, elapsed_ms=%.0f",
            request_id,
            get_elapsed_ms(start_time),
        )
        raise ToolError("복지서비스 상세 조회에 실패했습니다.") from e


def main() -> None:
    logger.setLevel(LOG_LEVEL)
    mcp.run(transport="http", host="0.0.0.0", port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
