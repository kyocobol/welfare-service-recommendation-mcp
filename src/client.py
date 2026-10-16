from typing import Any, Literal

import httpx
import xmltodict

from config import BASE_URL, SERVICE_KEY
from src.exceptions import (
    WelfareApiError,
    WelfareApiInvalidParameter,
    WelfareApiRateLimited,
    WelfareApiTimeout,
)
from src.models import (
    LocalGovernmentWelfare,
    LocalGovernmentWelfareDetailed,
    NationalWelfare,
    NationalWelfareDetailed,
)


class WelfareClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        service_key: str = SERVICE_KEY,
        timeout: float = 3.0,
    ) -> None:
        self._base_url = base_url
        self._service_key = service_key
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _request(
        self,
        path: str,
        params: dict[str, Any],
        *,
        force_list: tuple[str, ...],
        api_name: str,
        attempts: int = 3,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        params = {"serviceKey": self._service_key, **params}
        params = {key: value for key, value in params.items() if value is not None}

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                break

            except httpx.TimeoutException as e:
                if attempt == attempts:
                    raise WelfareApiTimeout(api_name) from e

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 429:
                    raise WelfareApiRateLimited(
                        api_name,
                        status_code=status_code,
                    ) from e
                raise WelfareApiError(api_name, status_code=status_code) from e

        return xmltodict.parse(response.text, force_list=force_list)

    async def get_national_welfare_list(
        self,
        *,
        search_word: str | None = None,
        life_cycle: str | None = None,
        household_type: str | None = None,
        interest_theme: str | None = None,
        age: int | None = None,
        page_size: int = 25,
        search_type: Literal["001", "002", "003"] = "003",
        order_by: Literal["popular", "date"] = "popular",
    ) -> list[NationalWelfare]:
        data = await self._request(
            "/NationalWelfareInformationsV001/NationalWelfarelistV001",
            {
                "callTp": "L",
                "searchWrd": search_word,
                "lifeArray": life_cycle,
                "trgterIndvdlArray": household_type,
                "intrsThemaArray": interest_theme,
                "age": age,
                "numOfRows": page_size,
                "srchKeyCode": search_type,
                "orderBy": order_by,
            },
            force_list=("servList",),
            api_name="중앙부처 복지서비스 목록 조회 API",
        )
        services = data["wantedList"].get("servList", [])
        return [NationalWelfare.from_api(s) for s in services]

    async def get_local_welfare_list(
        self,
        *,
        search_word: str | None = None,
        life_cycle: str | None = None,
        household_type: str | None = None,
        interest_theme: str | None = None,
        age: int | None = None,
        province: str | None = None,
        district: str | None = None,
        page_size: int = 25,
        search_type: Literal["001", "002", "003"] = "003",
        order_by: Literal["001", "002"] = "002",
    ) -> list[LocalGovernmentWelfare]:
        data = await self._request(
            "/LocalGovernmentWelfareInformations/LcgvWelfarelist",
            {
                "searchWrd": search_word,
                "lifeArray": life_cycle,
                "trgterIndvdlArray": household_type,
                "intrsThemaArray": interest_theme,
                "age": age,
                "ctpvNm": province,
                "sggNm": district,
                "numOfRows": page_size,
                "srchKeyCode": search_type,
                "arrgOrd": order_by,
            },
            force_list=("servList",),
            api_name="지자체 복지서비스 목록 조회 API",
        )
        services = data["wantedList"].get("servList", [])
        return [LocalGovernmentWelfare.from_api(s) for s in services]

    async def get_national_welfare_detail(
        self, service_id: str
    ) -> NationalWelfareDetailed:
        api_name = "중앙부처 복지서비스 상세 조회 API"
        data = await self._request(
            "/NationalWelfareInformationsV001/NationalWelfaredetailedV001",
            {"callTp": "D", "servId": service_id},
            force_list=(
                "applmetList",
                "inqplCtadrList",
                "inqplHmpgReldList",
                "basfrmList",
                "baslawList",
            ),
            api_name=api_name,
        )
        service_detail = data["wantedDtl"]
        result_code = service_detail["resultCode"]

        if result_code == "10":
            raise WelfareApiInvalidParameter(api_name, result_code=result_code)

        return NationalWelfareDetailed.from_api(service_detail)

    async def get_local_welfare_detail(
        self, service_id: str
    ) -> LocalGovernmentWelfareDetailed:
        api_name = "지자체 복지서비스 상세 조회 API"
        data = await self._request(
            "/LocalGovernmentWelfareInformations/LcgvWelfaredetailed",
            {"servId": service_id},
            force_list=(
                "inqplCtadrList",
                "inqplHmpgReldList",
                "basfrmList",
                "baslawList",
            ),
            api_name=api_name,
        )
        service_detail = data["wantedDtl"]
        result_code = service_detail["resultCode"]

        if result_code == "10":
            raise WelfareApiInvalidParameter(api_name, result_code=result_code)

        return LocalGovernmentWelfareDetailed.from_api(service_detail)
