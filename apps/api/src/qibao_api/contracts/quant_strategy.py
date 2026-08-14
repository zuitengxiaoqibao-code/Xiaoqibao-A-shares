from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.market_overview import (
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
)
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.contracts.field_evidence import FieldEvidence


QuantStrategyStatus = Literal["ready", "partial", "unavailable"]
CandidateActionStatus = Literal["alert", "watch", "reject", "pending_trigger"]
QuantRefreshMode = Literal["live", "delayed", "postclose", "stale"]
QuantRefreshState = Literal["ready", "pending", "failed"]
CandidateScanState = Literal["ready", "pending", "failed"]
CandidateScanPhase = Literal["loading_history", "computing_factors", "ranking", "ready", "failed"]
SignalVoteDirection = Literal[-1, 0, 1]
CandidateFunnelKey = Literal[
    "universe",
    "history_ready",
    "factor_ready",
    "liquidity_ready",
    "ranked",
    "trigger_confirmed",
    "final_candidates",
]


class QuantSignalVote(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal: str = Field(min_length=1)
    vote: SignalVoteDirection
    evidence_value: Decimal


class AlertGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal[
        "regime_match",
        "strategy_score",
        "trigger_confirmed",
        "risk_penalty",
        "evidence_coverage",
        "hard_risk",
    ]
    label: str = Field(min_length=1)
    passed: bool
    detail: str = Field(min_length=1)


class AlertGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool = False
    checks: tuple[AlertGateCheck, ...] = ()
    blockers: tuple[str, ...] = ()


class QuantStrategyCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    strategy_score: Decimal = Field(ge=0, le=100)
    regime_match: Decimal = Field(ge=0, le=1)
    stock_score: Decimal = Field(ge=0, le=1)
    trigger_score: Decimal = Field(ge=0, le=1)
    rr_score: Decimal = Field(ge=0, le=1)
    risk_penalty: Decimal = Field(ge=0, le=30)
    status: CandidateActionStatus
    trigger_confirmed: bool
    position: Decimal = Field(ge=0, le=1)
    planned_position: Decimal = Field(ge=0, le=1)
    reference_price: Decimal | None = Field(default=None, gt=0)
    vote_consensus: Decimal = Field(default=Decimal("0"), ge=-1, le=1)
    vote_position: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    signal_votes: tuple[QuantSignalVote, ...] = ()
    evidence_coverage_percent: Decimal = Field(ge=0, le=100)
    buy_triggers: tuple[str, ...]
    invalidation_rules: tuple[str, ...]
    risk_flags: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    alert_gate: AlertGate = Field(default_factory=AlertGate)
    factor_as_of: date
    sources: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_trigger_safety(self) -> "QuantStrategyCandidate":
        if self.missing_evidence:
            if self.trigger_score != 0:
                raise ValueError("missing trigger evidence requires zero trigger score")
            if self.status != "pending_trigger":
                raise ValueError("missing trigger evidence requires pending status")
        if self.status in {"alert", "watch"} and not self.trigger_confirmed:
            raise ValueError("actionable status requires confirmed trigger")
        if not self.trigger_confirmed and self.position != 0:
            raise ValueError("unconfirmed trigger requires zero current position")
        if self.vote_position > self.planned_position:
            raise ValueError("vote position cannot exceed planned position ceiling")
        if self.status == "alert" and self.alert_gate.checks and not self.alert_gate.eligible:
            raise ValueError("alert status requires every strict alert gate to pass")
        return self


class QuantStrategyModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    applicable_regimes: tuple[str, ...]
    selected: bool = False
    defensive: bool = False


class CandidateFunnelStage(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: CandidateFunnelKey
    label: str = Field(min_length=1)
    count: int = Field(ge=0)


class CandidateSelectionFunnel(BaseModel):
    model_config = ConfigDict(frozen=True)

    stages: tuple[CandidateFunnelStage, ...] = ()
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    completeness: Literal["complete", "partial", "unavailable"] = "unavailable"
    blockers: tuple[str, ...] = ()


class QuantStrategyDashboard(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: QuantStrategyStatus
    as_of: date
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    market_observed_at: AwareDatetime
    data_age_seconds: int = Field(ge=0)
    refresh_mode: QuantRefreshMode
    refresh_state: QuantRefreshState = "ready"
    snapshot_at: AwareDatetime | None = None
    refresh_started_at: AwareDatetime | None = None
    refresh_finished_at: AwareDatetime | None = None
    snapshot_source: str = "computed"
    next_refresh_at: AwareDatetime
    candidate_scan_at: AwareDatetime | None = None
    candidate_scan_age_seconds: int | None = Field(default=None, ge=0)
    candidate_scan_cached: bool = False
    candidate_scan_state: CandidateScanState = "ready"
    candidate_scan_started_at: AwareDatetime | None = None
    candidate_scan_error: str | None = None
    candidate_scan_phase: CandidateScanPhase = "ready"
    candidate_scan_processed: int | None = Field(default=None, ge=0)
    candidate_scan_total: int | None = Field(default=None, ge=0)
    trigger_evidence_at: AwareDatetime | None = None
    trigger_evidence_age_seconds: int | None = Field(default=None, ge=0)
    trigger_evidence_cached: bool = False
    formula_version: Literal["a-share-short-strategy-v2.0"] = (
        "a-share-short-strategy-v2.0"
    )
    # Exact immutable source snapshots used for this strategy result.  These
    # are IDs from field evidence, never operation names or display labels.
    input_snapshot_ids: tuple[str, ...] = ()
    metrics: OverviewRegimeMetrics
    regime: OverviewRegimeAssessment
    strategy_models: tuple[QuantStrategyModel, ...] = ()
    candidate_funnel: CandidateSelectionFunnel = Field(
        default_factory=CandidateSelectionFunnel
    )
    evidence_ledger: tuple[EvidenceLedgerEntry, ...] = ()
    field_evidence: tuple[FieldEvidence, ...] = ()
    candidates: tuple[QuantStrategyCandidate, ...]
    discipline: str = Field(min_length=1)
    missing_data: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
