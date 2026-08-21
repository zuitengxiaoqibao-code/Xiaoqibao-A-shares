from __future__ import annotations

from datetime import datetime
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


def utc_now() -> datetime:
    """Clock seam for registry construction; callers should inject their own time in tests."""
    from datetime import timezone

    return datetime.now(timezone.utc)
