from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


MetricStatus = Literal["ready", "partial", "stale", "unavailable", "error"]
MetricDrilldownKind = Literal["members", "aggregate_only"]


class MetricMember(BaseModel):
    """One verifiable member of an aggregate market metric."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    name: str = Field(default="名称待补齐", min_length=1)
    reason: str = Field(min_length=1)
    value: str | int | float | None = None

    @model_validator(mode="after")
    def normalize_name(self) -> "MetricMember":
        if not self.name.strip():
            return self.model_copy(update={"name": "名称待补齐"})
        return self


class MetricContract(BaseModel):
    """Shared, evidence-first contract for dashboard metrics and drill-downs."""

    model_config = ConfigDict(frozen=True)

    metric_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    value: str | int | float | None = None
    unit: str | None = None
    scope: str = Field(min_length=1)
    status: MetricStatus
    trade_date: date | None = None
    observed_at: AwareDatetime | None = None
    source: str = Field(min_length=1)
    formula_version: str | None = None
    sample_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)
    loaded_member_count: int = Field(default=0, ge=0)
    drilldown_kind: MetricDrilldownKind = "aggregate_only"
    members: tuple[MetricMember, ...] = ()
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def validate_truthful_state(self) -> "MetricContract":
        if self.loaded_member_count != len(self.members):
            raise ValueError("loaded_member_count must match members")
        if self.total_count is not None and self.total_count < self.loaded_member_count:
            raise ValueError("total_count cannot be smaller than loaded_member_count")
        if self.drilldown_kind == "aggregate_only" and not self.unavailable_reason:
            raise ValueError("aggregate_only requires unavailable_reason")
        if self.status in {"unavailable", "error"} and not self.unavailable_reason:
            raise ValueError("unavailable metric requires unavailable_reason")
        if self.status in {"ready", "partial", "stale"} and self.observed_at is None:
            raise ValueError("observed metric requires observed_at")
        return self
