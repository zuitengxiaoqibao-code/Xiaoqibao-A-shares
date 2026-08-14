from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class ResearchCompareRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...] = Field(min_length=2, max_length=5)
    as_of: date | None = None

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("比较标的不能重复")
        if any(len(item) != 6 or not item.isdigit() for item in value):
            raise ValueError("比较标的必须是六位 A 股代码")
        return value


class ResearchCompareCompany(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    status: Literal["ready", "partial", "unavailable"]
    evidence_coverage_percent: Decimal = Field(ge=0, le=100)
    final_score: Decimal | None = Field(default=None, ge=0, le=100)
    business_model: str | None = None
    industry_space: str | None = None
    latest_revenue_yoy_percent: Decimal | None = None
    latest_net_profit_yoy_percent: Decimal | None = None
    latest_operating_cash_flow: Decimal | None = None
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    catalysts: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class ResearchCompareResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "unavailable"]
    as_of: date
    generated_at: AwareDatetime
    companies: tuple[ResearchCompareCompany, ...]
    sources: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

