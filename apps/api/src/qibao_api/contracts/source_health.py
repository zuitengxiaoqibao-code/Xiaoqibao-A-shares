from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


SourceAttemptStatus = Literal["ready", "error", "empty"]
SourceHealthStatus = Literal["ready", "degraded", "unavailable"]
MetadataValue = str | int | float | bool | None


class SourceAttemptEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    status: SourceAttemptStatus
    latency_ms: int = Field(ge=0)
    observed_at: AwareDatetime
    error_code: str | None = Field(default=None, min_length=1)
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class SourceHealthItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    status: SourceHealthStatus
    attempts: int = Field(ge=1)
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)
    empty_responses: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)
    average_latency_ms: int = Field(ge=0)
    latest_latency_ms: int = Field(ge=0)
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error_code: str | None = None
    latest_trade_date: str | None = None
    field_count: int | None = Field(default=None, ge=0)
    row_count: int | None = Field(default=None, ge=0)
    validation: str | None = None


class SourceHealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: AwareDatetime
    window_size: int = Field(ge=1)
    sources: tuple[SourceHealthItem, ...]
