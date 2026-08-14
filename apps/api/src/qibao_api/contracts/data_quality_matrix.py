from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


DataQualityStatus = Literal["ready", "partial", "stale", "unavailable", "error"]
CacheState = Literal["live", "cache", "mixed", "not_applicable"]


class DataQualityItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str = Field(min_length=1)
    status: DataQualityStatus
    source: str = Field(min_length=1)
    trade_date: date | None = None
    observed_at: AwareDatetime | None = None
    valid_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    cache_state: CacheState
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_quality_claim(self) -> "DataQualityItem":
        if self.valid_count is not None and self.total_count is not None:
            if self.valid_count > self.total_count:
                raise ValueError("valid_count cannot exceed total_count")
            expected = 0.0 if self.total_count == 0 else round(
                self.valid_count / self.total_count * 100, 2
            )
            if self.coverage_percent is not None and abs(self.coverage_percent - expected) > 0.01:
                raise ValueError("coverage_percent must match valid_count / total_count")
        if self.status == "ready":
            if self.observed_at is None:
                raise ValueError("ready quality requires observed_at")
            if self.valid_count is not None and self.valid_count == 0:
                raise ValueError("ready quality cannot claim zero valid samples")
        if self.status in {"unavailable", "error"} and not self.limitations:
            raise ValueError("unavailable quality requires limitations")
        return self


class DataQualityMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: AwareDatetime
    items: tuple[DataQualityItem, ...] = ()
