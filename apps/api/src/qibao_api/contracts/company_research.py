from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.contracts.field_evidence import FieldEvidence


ResearchStatus = Literal["ready", "partial", "unavailable"]
EvidenceStatus = Literal["ready", "clear", "triggered", "unavailable"]
LatestTipCategory = Literal["公告与合同", "业绩预告", "资金与融资", "交易异动", "风险提醒", "其他"]
LatestTipTone = Literal["positive", "neutral", "risk", "unknown"]
ResearchConclusionKind = Literal["fact", "inference", "judgement", "unavailable"]
ResearchSectionKey = Literal[
    "business_model", "industry_space", "financial_trend", "profit_quality",
    "competitive_position", "valuation_percentile", "future_catalysts",
    "contrary_risks", "invalidation_conditions", "verification_checklist",
]


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


class ValuationScenarioRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["available", "unavailable"] = "unavailable"
    conservative: Decimal | None = None
    neutral: Decimal | None = None
    optimistic: Decimal | None = None
    eps_basis: Decimal | None = None
    peer_pe_basis: Decimal | None = None
    institution_sample_count: int = Field(default=0, ge=0)
    latest_report_date: date | None = None
    reason: str = "机构预测或同行估值证据不足，不计算情景区间。"


class ValuationObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    pe_ttm: Decimal | None
    pb: Decimal | None
    market_cap_yi: Decimal | None
    peer_pe_median: Decimal | None = None
    peer_pb_median: Decimal | None = None
    forward_eps_median: Decimal | None = None
    forward_eps_sample_count: int = Field(default=0, ge=0)
    forecast_latest_report_date: date | None = None
    forecast_age_days: int | None = Field(default=None, ge=0)
    forecast_freshness: Literal["fresh", "stale", "unavailable"] = "unavailable"
    forward_pe: Decimal | None = None
    forward_pe_status: Literal["available", "low_confidence", "unavailable"] = "unavailable"
    forward_pe_reason: str = "缺少足够机构预测样本。"
    scenario_range: ValuationScenarioRange = Field(default_factory=ValuationScenarioRange)
    observation_range_status: Literal["available", "unavailable"]
    observation_range_reason: str
    source: str
    observed_at: datetime | None


class LatestTipItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: LatestTipCategory
    title: str
    date: str | None
    tone: LatestTipTone
    summary: str
    source: str
    observed_at: datetime | None
    raw_text: str


class CompanyProfileEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    company_overview: str | None
    industry_analysis: str | None
    latest_tips: str | None
    latest_tip_items: tuple[LatestTipItem, ...] = ()
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


class ResearchReportEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    title: str
    publish_date: date
    organization: str
    rating: str | None = None
    industry: str | None = None
    eps_this_year: Decimal | None = None
    eps_next_year: Decimal | None = None
    eps_next_two_year: Decimal | None = None
    pdf_url: str | None = None


class UnlockEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    free_date: date
    stock_type: str | None = None
    shares: Decimal | None = None
    ratio_percent: Decimal | None = None


class MarginEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_date: date
    financing_balance: Decimal | None = None
    financing_buy: Decimal | None = None
    securities_lending_balance: Decimal | None = None
    total_balance: Decimal | None = None


class HolderEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    period: date
    holder_count: Decimal | None = None
    change_ratio_percent: Decimal | None = None
    average_free_shares: Decimal | None = None


class PeerCandidateEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    industry: str | None = None
    price: Decimal | None = None
    change_percent: Decimal | None = None
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    market_cap_yi: Decimal | None = None


class ResearchEnrichmentEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus = "unavailable"
    observed_at: datetime | None = None
    stock_reports: tuple[ResearchReportEvidence, ...] = ()
    industry_reports: tuple[ResearchReportEvidence, ...] = ()
    industry_name: str | None = None
    industry_code: str | None = None
    industry_board_code: str | None = None
    peer_candidates: tuple[PeerCandidateEvidence, ...] = ()
    unlocks: tuple[UnlockEvidence, ...] = ()
    margin: tuple[MarginEvidence, ...] = ()
    holders: tuple[HolderEvidence, ...] = ()
    sources: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class ResearchDecisionLedgerRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal["peer_context", "valuation", "catalysts", "contrary", "invalidation"]
    label: str
    status: Literal["ready", "partial", "unavailable", "clear", "triggered"]
    summary: str
    facts: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    limitation: str | None = None


class CompanyResearchSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: ResearchSectionKey
    label: str
    status: Literal["ready", "partial", "unavailable", "clear", "triggered"]
    summary: str
    facts: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    limitation: str | None = None


class ResearchConclusion(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: ResearchSectionKey
    label: str = Field(min_length=1)
    kind: ResearchConclusionKind
    claim: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    source_count: int = Field(ge=0)
    observed_at: datetime | None = None
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_evidence_boundary(self) -> "ResearchConclusion":
        evidence_count = len(set(self.evidence_ids))
        if self.source_count != evidence_count:
            raise ValueError("source_count must equal distinct evidence count")
        if self.kind == "unavailable":
            if self.evidence_ids or self.observed_at is not None or not self.limitations:
                raise ValueError("unavailable conclusion requires only an explicit limitation")
        elif not self.evidence_ids or self.observed_at is None:
            raise ValueError("research conclusion requires evidence and observation time")
        return self


class CompanyResearchVersionChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: Literal["conclusion", "data", "source"]
    label: str
    before: str | None = None
    after: str | None = None


class CompanyResearchVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    version_number: int = Field(ge=1)
    previous_snapshot_id: str | None = None
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_at: datetime
    changes: tuple[CompanyResearchVersionChange, ...] = ()


class CompanyResearchAIEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class CompanyResearchAIRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    symbol: str = Field(pattern=r"^\d{6}$")
    generated_at: datetime
    evidence: tuple[CompanyResearchAIEvidence, ...]
    deterministic_conclusions: tuple[str, ...]


class CompanyResearchAIContraryRisk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]


class CompanyResearchAIAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    executive_summary: str = Field(min_length=1)
    contrary_risks: tuple[CompanyResearchAIContraryRisk, ...]
    verification_questions: tuple[str, ...]


class CompanyResearchAIResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "unconfigured", "timeout", "http_error", "invalid"]
    snapshot_id: str
    analysis: CompanyResearchAIAnalysis | None = None
    provider: str
    model: str
    prompt_version: str = "company-research-ai-v1"
    generated_at: datetime


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
    enrichment: ResearchEnrichmentEvidence = Field(default_factory=ResearchEnrichmentEvidence)
    decision_ledger: tuple[ResearchDecisionLedgerRow, ...] = ()
    research_sections: tuple[CompanyResearchSection, ...] = ()
    conclusions: tuple[ResearchConclusion, ...] = ()
    research_version: CompanyResearchVersion | None = None
    evidence_ledger: tuple[EvidenceLedgerEntry, ...] = ()
    field_evidence: tuple[FieldEvidence, ...] = ()
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
        if self.decision_ledger:
            expected = ("peer_context", "valuation", "catalysts", "contrary", "invalidation")
            if tuple(item.key for item in self.decision_ledger) != expected:
                raise ValueError("decision ledger must contain the five ordered research sections")
        if self.research_sections:
            expected_sections = (
                "business_model", "industry_space", "financial_trend", "profit_quality",
                "competitive_position", "valuation_percentile", "future_catalysts",
                "contrary_risks", "invalidation_conditions", "verification_checklist",
            )
            if tuple(item.key for item in self.research_sections) != expected_sections:
                raise ValueError("company research must contain the ten ordered research sections")
        return self
