from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.market_overview import (
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
)


QuantStrategyStatus = Literal["ready", "partial", "unavailable"]
CandidateActionStatus = Literal["alert", "watch", "reject", "pending_trigger"]
QuantRefreshMode = Literal["live", "delayed", "postclose", "stale"]


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
    evidence_coverage_percent: Decimal = Field(ge=0, le=100)
    buy_triggers: tuple[str, ...]
    invalidation_rules: tuple[str, ...]
    risk_flags: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
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
        return self


class QuantStrategyModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    applicable_regimes: tuple[str, ...]
    selected: bool = False
    defensive: bool = False


class QuantStrategyDashboard(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: QuantStrategyStatus
    as_of: date
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    market_observed_at: AwareDatetime
    data_age_seconds: int = Field(ge=0)
    refresh_mode: QuantRefreshMode
    next_refresh_at: AwareDatetime
    formula_version: Literal["a-share-short-strategy-v2.0"] = (
        "a-share-short-strategy-v2.0"
    )
    metrics: OverviewRegimeMetrics
    regime: OverviewRegimeAssessment
    strategy_models: tuple[QuantStrategyModel, ...] = ()
    candidates: tuple[QuantStrategyCandidate, ...]
    discipline: str = Field(min_length=1)
    missing_data: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
