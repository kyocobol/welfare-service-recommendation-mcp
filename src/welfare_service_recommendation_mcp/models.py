from typing import Any, ClassVar, Literal, Self

from pydantic import BaseModel, Field

from welfare_service_recommendation_mcp.config import DATA_DIR
from welfare_service_recommendation_mcp.utils import load_json

CODE_MAPS: dict[str, Any] = load_json(DATA_DIR / "code_maps.json")
PROVINCES: list[str] = load_json(DATA_DIR / "provinces.json")
DISTRICTS: list[str] = load_json(DATA_DIR / "districts.json")

LABEL_TO_CODE: dict[str, dict[str, str]] = {
    field: {label: code for code, label in mapping.items()}
    for field, mapping in CODE_MAPS.items()
}

LifeCycle = Literal[*LABEL_TO_CODE["life_cycle"]]
HouseholdType = Literal[*LABEL_TO_CODE["household_type"]]
InterestTheme = Literal[*LABEL_TO_CODE["interest_theme"]]
ServiceDetail = Literal[*CODE_MAPS["service_detail"]]
Province = Literal[*PROVINCES]
District = Literal[*DISTRICTS]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class NationalWelfare(BaseModel):
    provider: Literal["national"] = Field(
        default="national", description="서비스 제공처"
    )
    service_id: str = Field(description="서비스 ID")
    name: str = Field(description="서비스명")
    summary: str | None = Field(default=None, description="서비스 요약")
    detail_link: str | None = Field(default=None, description="서비스 상세 링크")
    registered_at: str | None = Field(default=None, description="서비스 등록일")
    ministry: str | None = Field(default=None, description="소관부처명")
    organization: str | None = Field(default=None, description="소관조직명")
    life_cycle: str | None = Field(default=None, description="생애주기")
    household_type: str | None = Field(default=None, description="가구상황")
    interest_theme: str | None = Field(default=None, description="관심주제")
    support_cycle: str | None = Field(default=None, description="지원주기")
    provision_type: str | None = Field(default=None, description="제공유형")
    online_apply: str | None = Field(default=None, description="온라인 신청 가능 여부")
    contact: str | None = Field(default=None, description="문의처")

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Self:
        return cls(
            service_id=item.get("servId"),
            name=item.get("servNm"),
            summary=item.get("servDgst"),
            detail_link=item.get("servDtlLink"),
            registered_at=item.get("svcfrstRegTs"),
            ministry=item.get("jurMnofNm"),
            organization=item.get("jurOrgNm"),
            life_cycle=item.get("lifeArray"),
            household_type=item.get("trgterIndvdlArray"),
            interest_theme=item.get("intrsThemaArray"),
            support_cycle=item.get("sprtCycNm"),
            provision_type=item.get("srvPvsnNm"),
            online_apply=item.get("onapPsbltYn"),
            contact=item.get("rprsCtadr"),
        )


class LocalGovernmentWelfare(BaseModel):
    provider: Literal["local"] = Field(default="local", description="서비스 제공처")
    service_id: str = Field(description="서비스 ID")
    name: str = Field(description="서비스명")
    summary: str | None = Field(default=None, description="서비스 요약")
    detail_link: str | None = Field(default=None, description="서비스 상세 링크")
    province: str | None = Field(default=None, description="시도명")
    district: str | None = Field(default=None, description="시군구명")
    department: str | None = Field(default=None, description="사업담당부서명")
    life_cycle: str | None = Field(default=None, description="생애주기")
    household_type: str | None = Field(default=None, description="가구상황")
    interest_theme: str | None = Field(default=None, description="관심주제")
    support_cycle: str | None = Field(default=None, description="지원주기")
    provision_type: str | None = Field(default=None, description="제공유형")
    application_method: str | None = Field(default=None, description="신청방법")

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Self:
        return cls(
            service_id=item.get("servId"),
            name=item.get("servNm"),
            summary=item.get("servDgst"),
            detail_link=item.get("servDtlLink"),
            province=item.get("ctpvNm"),
            district=item.get("sggNm"),
            department=item.get("bizChrDeptNm"),
            life_cycle=item.get("lifeNmArray"),
            household_type=item.get("trgterIndvdlNmArray"),
            interest_theme=item.get("intrsThemaNmArray"),
            support_cycle=item.get("sprtCycNm"),
            provision_type=item.get("srvPvsnNm"),
            application_method=item.get("aplyMtdNm"),
        )


class NationalWelfareDetailItem(BaseModel):
    source_code_key: ClassVar[str] = "servSeCode"
    source_name_key: ClassVar[str] = "servSeDetailNm"
    source_content_key: ClassVar[str] = "servSeDetailLink"

    code: ServiceDetail | None = Field(
        default=None,
        description="서비스 구분 코드",
    )
    category: str | None = Field(default=None, description="서비스 구분 유형")
    name: str | None = Field(default=None, description="상세명")
    content: str | None = Field(default=None, description="상세 링크 또는 연락처")

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Self:
        code = item.get(cls.source_code_key)

        return cls(
            code=code,
            category=CODE_MAPS["service_detail"].get(code),
            name=item.get(cls.source_name_key),
            content=item.get(cls.source_content_key),
        )


class NationalWelfareDetailed(BaseModel):
    service_id: str = Field(description="서비스 ID")
    name: str = Field(description="서비스명")
    summary: str | None = Field(default=None, description="서비스 요약")
    target: str | None = Field(default=None, description="대상자 상세내용")
    criteria: str | None = Field(default=None, description="선정기준 내용")
    benefits: str | None = Field(default=None, description="급여서비스 내용")
    ministry: str | None = Field(default=None, description="소관부처명")
    life_cycle: str | None = Field(default=None, description="생애주기")
    household_type: str | None = Field(default=None, description="가구상황")
    interest_theme: str | None = Field(default=None, description="관심주제")
    support_cycle: str | None = Field(default=None, description="지원주기")
    provision_type: str | None = Field(default=None, description="제공유형")
    contact: str | None = Field(default=None, description="문의처")
    applications: list[NationalWelfareDetailItem] = Field(
        default_factory=list,
        description="서비스 이용 및 신청방법 목록",
    )
    contacts: list[NationalWelfareDetailItem] = Field(
        default_factory=list,
        description="문의처 목록",
    )
    websites: list[NationalWelfareDetailItem] = Field(
        default_factory=list,
        description="관련 웹사이트 목록",
    )
    forms: list[NationalWelfareDetailItem] = Field(
        default_factory=list,
        description="서식/자료 목록",
    )
    laws: list[NationalWelfareDetailItem] = Field(
        default_factory=list,
        description="근거법령 목록",
    )

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Self:
        return cls(
            service_id=item.get("servId"),
            name=item.get("servNm"),
            summary=item.get("wlfareInfoOutlCn"),
            target=item.get("tgtrDtlCn"),
            criteria=item.get("slctCritCn"),
            benefits=item.get("alwServCn"),
            ministry=item.get("jurMnofNm"),
            life_cycle=item.get("lifeArray"),
            household_type=item.get("trgterIndvdlArray"),
            interest_theme=item.get("intrsThemaArray"),
            support_cycle=item.get("sprtCycNm"),
            provision_type=item.get("srvPvsnNm"),
            contact=item.get("rprsCtadr"),
            applications=[
                NationalWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("applmetList"))
            ],
            contacts=[
                NationalWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("inqplCtadrList"))
            ],
            websites=[
                NationalWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("inqplHmpgReldList"))
            ],
            forms=[
                NationalWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("basfrmList"))
            ],
            laws=[
                NationalWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("baslawList"))
            ],
        )


class LocalGovernmentWelfareDetailItem(NationalWelfareDetailItem):
    source_code_key: ClassVar[str] = "wlfareInfoDtlCd"
    source_name_key: ClassVar[str] = "wlfareInfoReldNm"
    source_content_key: ClassVar[str] = "wlfareInfoReldCn"


class LocalGovernmentWelfareDetailed(BaseModel):
    service_id: str = Field(description="서비스 ID")
    name: str = Field(description="서비스명")
    summary: str | None = Field(default=None, description="서비스 요약")
    target: str | None = Field(default=None, description="지원대상 내용")
    criteria: str | None = Field(default=None, description="선정기준 내용")
    benefits: str | None = Field(default=None, description="급여서비스 내용")
    start_date: str | None = Field(default=None, description="시행시작일자")
    end_date: str | None = Field(default=None, description="시행종료일자")
    province: str | None = Field(default=None, description="시도명")
    district: str | None = Field(default=None, description="시군구명")
    department: str | None = Field(default=None, description="사업담당부서명")
    life_cycle: str | None = Field(default=None, description="생애주기")
    household_type: str | None = Field(default=None, description="가구상황")
    interest_theme: str | None = Field(default=None, description="관심주제")
    support_cycle: str | None = Field(default=None, description="지원주기")
    provision_type: str | None = Field(default=None, description="제공유형")
    application_method: str | None = Field(default=None, description="신청방법")
    application_content: str | None = Field(default=None, description="신청방법 내용")
    contacts: list[LocalGovernmentWelfareDetailItem] = Field(
        default_factory=list,
        description="문의처 목록",
    )
    websites: list[LocalGovernmentWelfareDetailItem] = Field(
        default_factory=list,
        description="관련 웹사이트 목록",
    )
    forms: list[LocalGovernmentWelfareDetailItem] = Field(
        default_factory=list,
        description="서식/자료 목록",
    )
    laws: list[LocalGovernmentWelfareDetailItem] = Field(
        default_factory=list,
        description="근거법령 목록",
    )

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Self:
        return cls(
            service_id=item.get("servId"),
            name=item.get("servNm"),
            summary=item.get("servDgst"),
            target=item.get("sprtTrgtCn"),
            criteria=item.get("slctCritCn"),
            benefits=item.get("alwServCn"),
            start_date=item.get("enfcBgngYmd"),
            end_date=item.get("enfcEndYmd"),
            province=item.get("ctpvNm"),
            district=item.get("sggNm"),
            department=item.get("bizChrDeptNm"),
            life_cycle=item.get("lifeNmArray"),
            household_type=item.get("trgterIndvdlNmArray"),
            interest_theme=item.get("intrsThemaNmArray"),
            support_cycle=item.get("sprtCycNm"),
            provision_type=item.get("srvPvsnNm"),
            application_method=item.get("aplyMtdNm"),
            application_content=item.get("aplyMtdCn"),
            contacts=[
                LocalGovernmentWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("inqplCtadrList"))
            ],
            websites=[
                LocalGovernmentWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("inqplHmpgReldList"))
            ],
            forms=[
                LocalGovernmentWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("basfrmList"))
            ],
            laws=[
                LocalGovernmentWelfareDetailItem.from_api(detail)
                for detail in _as_list(item.get("baslawList"))
            ],
        )
