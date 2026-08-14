from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


EvidenceLedgerStatus = Literal["ready", "partial", "stale", "unavailable", "error"]


class EvidenceLedgerEntry(BaseModel):
    """Common provenance row shared by market, quant, research and news views."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    status: EvidenceLedgerStatus
    trade_date: date | None = None
    observed_at: AwareDatetime | None = None
    formula_version: str | None = None
    sample_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_truthful_state(self) -> "EvidenceLedgerEntry":
        if self.status == "ready" and self.observed_at is None:
            raise ValueError("ready evidence requires observed_at")
        if self.status in {"unavailable", "error"} and not self.limitations:
            raise ValueError("unavailable evidence requires explicit limitations")
        if self.sample_count is not None and self.sample_count == 0 and self.status == "ready":
            raise ValueError("ready evidence cannot claim zero samples")
        if self.sample_count is not None and self.total_count is not None and self.sample_count > self.total_count:
            raise ValueError("sample_count cannot exceed total_count")
        if self.coverage_percent is not None and self.total_count == 0 and self.coverage_percent > 0:
            raise ValueError("coverage_percent must be zero when total_count is zero")
        return self


class EvidenceLedger(BaseModel):
    model_config = ConfigDict(frozen=True)

    entries: tuple[EvidenceLedgerEntry, ...] = ()

    @model_validator(mode="after")
    def require_unique_operations(self) -> "EvidenceLedger":
        keys = [(item.source, item.operation) for item in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("evidence ledger source and operation pairs must be unique")
        return self
