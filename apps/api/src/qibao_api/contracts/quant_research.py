from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


ResearchStatus = Literal[
    "ready", "partial", "insufficient", "stale", "unavailable", "error"
]
FactorFamily = Literal[
    "trend", "momentum", "volume_price", "liquidity", "volatility",
    "quality", "valuation", "risk",
]
FactorDirection = Literal["positive", "negative", "bidirectional"]
FactorLifecycle = Literal["candidate", "active", "watch", "retired"]


class FactorDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    family: FactorFamily
    direction: FactorDirection
    required_fields: tuple[str, ...] = Field(min_length=1)
    minimum_history: int = Field(ge=2)
    formula_version: str = Field(min_length=1)
    owner: Literal["system", "ai_research"]
    lifecycle: FactorLifecycle
    registered_at: AwareDatetime
    retired_at: AwareDatetime | None = None
    retirement_reason: str | None = None

    @model_validator(mode="after")
    def validate_retirement(self) -> "FactorDefinition":
        if self.lifecycle == "retired":
            if self.retired_at is None or not (self.retirement_reason or "").strip():
                raise ValueError("retired factor requires retired_at and retirement_reason")
            if self.retired_at < self.registered_at:
                raise ValueError("retired_at must not precede registered_at")
        elif self.retired_at is not None or self.retirement_reason is not None:
            raise ValueError("non-retired factor cannot contain retirement fields")
        if len(set(self.required_fields)) != len(self.required_fields):
            raise ValueError("required_fields must be unique")
        return self


class FactorRegistrySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ResearchStatus
    as_of: AwareDatetime
    factors: tuple[FactorDefinition, ...]
    formula_version: Literal["quant-factor-registry-v1"] = "quant-factor-registry-v1"
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_unique_factor_ids(self) -> "FactorRegistrySnapshot":
        factor_ids = tuple(item.factor_id for item in self.factors)
        if len(factor_ids) != len(set(factor_ids)):
            raise ValueError("factor ids must be unique")
        return self


class FactorLifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    previous_state: FactorLifecycle | None = None
    current_state: FactorLifecycle
    reason: str = Field(min_length=1)
    occurred_at: AwareDatetime
    source_snapshot_ids: tuple[str, ...] = ()


class FactorObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    trade_date: date
    symbol: str = Field(pattern=r"^\d{6}$")
    value: Decimal | None
    forward_return: Decimal | None
    source_snapshot_ids: tuple[str, ...] = ()


class FactorHealth(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    family: FactorFamily
    status: Literal["healthy", "watch", "insufficient", "stale", "error"]
    sample_count: int = Field(ge=0)
    valid_day_count: int = Field(ge=0)
    coverage_percent: Decimal = Field(ge=0, le=100)
    missing_rate_percent: Decimal = Field(ge=0, le=100)
    rank_ic_20: Decimal | None = Field(default=None, ge=-1, le=1)
    rank_ic_60: Decimal | None = Field(default=None, ge=-1, le=1)
    rank_ic_120: Decimal | None = Field(default=None, ge=-1, le=1)
    ic_mean: Decimal | None = Field(default=None, ge=-1, le=1)
    ic_std: Decimal | None = Field(default=None, ge=0)
    icir: Decimal | None = None
    direction_accuracy_percent: Decimal | None = Field(default=None, ge=0, le=100)
    latest_valid_date: date | None = None
    max_family_correlation: Decimal | None = Field(default=None, ge=0, le=1)
    correlated_factor_id: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9_]*$"
    )
    generated_at: AwareDatetime
    formula_version: Literal["quant-factor-health-v1"] = "quant-factor-health-v1"
    source_snapshot_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


RiskGateStatus = Literal["pass", "warn", "block", "unavailable"]


class QuantRiskContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    suspended: bool | None = None
    limit_untradeable: bool | None = None
    average_amount_20d: Decimal | None = Field(default=None, ge=0)
    beneish_components: dict[str, Decimal] | None = None
    sector_exposure_percent: Decimal | None = Field(default=None, ge=0, le=100)
    theme_exposure_percent: Decimal | None = Field(default=None, ge=0, le=100)
    source_snapshot_ids: tuple[str, ...] = ()


class RiskGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal[
        "evidence", "tradability", "financial_anomaly", "signal_conflict",
        "concentration",
    ]
    label: str = Field(min_length=1)
    status: RiskGateStatus
    reason: str = Field(min_length=1)
    metric_value: Decimal | None = None
    threshold: Decimal | None = None
    source_snapshot_ids: tuple[str, ...] = ()


class QuantRiskGateSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    overall_status: Literal["pass", "warn", "block"]
    checks: tuple[RiskGateCheck, ...]
    blockers: tuple[str, ...] = ()
    formula_version: Literal["quant-risk-gates-v1"] = "quant-risk-gates-v1"

    @model_validator(mode="after")
    def require_all_unique_gates(self) -> "QuantRiskGateSummary":
        keys = tuple(item.key for item in self.checks)
        if len(keys) != len(set(keys)):
            raise ValueError("risk gate keys must be unique")
        if self.overall_status == "block" and not self.blockers:
            raise ValueError("blocked risk summary requires blockers")
        return self


class OpportunityDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    opportunity_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    applicable_regimes: tuple[str, ...] = Field(min_length=1)
    required_evidence: tuple[str, ...] = Field(min_length=1)
    score_components: tuple[str, ...] = Field(min_length=1)
    trigger_rules: tuple[str, ...] = Field(min_length=1)
    invalidation_rules: tuple[str, ...] = Field(min_length=1)
    unavailable_when: tuple[str, ...] = Field(min_length=1)
    formula_version: Literal["quant-opportunity-registry-v1"] = (
        "quant-opportunity-registry-v1"
    )


def utc_now() -> datetime:
    """Clock seam for registry construction; callers should inject their own time in tests."""
    from datetime import timezone

    return datetime.now(timezone.utc)
