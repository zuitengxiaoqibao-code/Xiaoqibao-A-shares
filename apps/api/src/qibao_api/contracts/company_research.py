from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ResearchStatus = Literal["ready", "partial", "unavailable"]
EvidenceStatus = Literal["ready", "clear", "triggered", "unavailable"]


class FinancialPeriod(BaseModel):
    model_config = ConfigDict(frozen=True)

    period: date
    revenue: Decimal | None = None
    revenue_yoy: Decimal | None = None
    operating_cost: Decimal | None = None
    net_profit: Decimal | None = None
    net_profit_yoy: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    total_assets: Decimal | None = None
    total_liabilities: Decimal | None = None
    total_equity: Decimal | None = None
    gross_margin: Decimal | None = None
    cash_to_profit: Decimal | None = None
    debt_ratio: Decimal | None = None


class FinancialHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    periods: tuple[FinancialPeriod, ...]
    annual_periods: tuple[FinancialPeriod, ...]
    latest_period: FinancialPeriod | None
    revenue_cagr_3y: Decimal | None
    net_profit_cagr_3y: Decimal | None
    source: str
    observed_at: datetime | None
    reasons: tuple[str, ...] = ()


class CompanyResearchDimension(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    weight: int = Field(ge=0, le=100)
    status: Literal["ready", "unavailable"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    summary: str
    metrics: dict[str, Decimal | str | None]
    evidence_ids: tuple[str, ...] = ()
    reason: str | None = None


class CounterCaseItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    title: str
    status: Literal["clear", "triggered", "unavailable"]
    detail: str
    threshold: str | None
    penalty: Decimal = Field(ge=0, le=25)
    evidence_ids: tuple[str, ...] = ()


class ValuationObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    pe_ttm: Decimal | None
    pb: Decimal | None
    market_cap_yi: Decimal | None
    peer_pe_median: Decimal | None = None
    peer_pb_median: Decimal | None = None
    observation_range_status: Literal["available", "unavailable"]
    observation_range_reason: str
    source: str
    observed_at: datetime | None


class CompanyProfileEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    company_overview: str | None
    industry_analysis: str | None
    latest_tips: str | None
    source: str
    observed_at: datetime | None
    reasons: tuple[str, ...] = ()


class ResearchSourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    label: str
    status: ResearchStatus
    observed_at: datetime | None
    detail: str


class CompanyResearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    as_of: date
    generated_at: datetime
    dimensions: tuple[CompanyResearchDimension, ...]
    evidence_coverage: Decimal = Field(ge=0, le=1)
    base_score: Decimal | None = Field(default=None, ge=0, le=100)
    risk_penalty: Decimal = Field(ge=0, le=25)
    final_score: Decimal | None = Field(default=None, ge=0, le=100)
    financial_history: FinancialHistory
    valuation: ValuationObservation
    counter_case: tuple[CounterCaseItem, ...]
    profile: CompanyProfileEvidence
    sources: tuple[ResearchSourceEvidence, ...]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_research_integrity(self) -> "CompanyResearchResponse":
        if len(self.counter_case) != 10:
            raise ValueError("company research must expose exactly ten counter-case checks")
        if self.evidence_coverage < Decimal("0.60") and self.final_score is not None:
            raise ValueError("final score requires at least sixty percent evidence coverage")
        if self.final_score is not None and self.base_score is not None:
            expected = max(Decimal("0"), self.base_score - self.risk_penalty)
            if abs(self.final_score - expected) > Decimal("0.01"):
                raise ValueError("final score must equal base score minus risk penalty")
        return self
