from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


QualityStatus = Literal["ready", "partial", "stale", "unavailable"]
SourceHealthStatus = Literal["ready", "partial", "stale", "unavailable"]


class DataSourceHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    status: SourceHealthStatus
    observed_at: AwareDatetime
    coverage: float = Field(ge=0, le=100)
    latency_ms: int = Field(ge=0)
    reason: str | None = None


class NormalizedBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    as_of: date
    observed_at: AwareDatetime
    ingested_at: AwareDatetime
    records: tuple[dict[str, Any], ...]
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_status: QualityStatus
