from __future__ import annotations

from datetime import date
from typing import Generic, Literal, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from qibao_api.contracts.task_progress import TaskProgress


SnapshotStatus = Literal["ready", "partial", "stale", "unavailable", "error"]
SnapshotFreshness = Literal["current", "delayed", "stale", "unknown"]
CacheState = Literal["live", "hit", "stale", "miss"]
PayloadT = TypeVar("PayloadT")


class SnapshotCache(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: CacheState
    cached_at: AwareDatetime | None = None


class SnapshotError(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class RuntimeSnapshot(BaseModel, Generic[PayloadT]):
    """Shared state boundary for cache-first pages and background refreshes."""

    model_config = ConfigDict(frozen=True)

    data: PayloadT | None
    status: SnapshotStatus
    freshness: SnapshotFreshness
    observed_at: AwareDatetime | None
    generated_at: AwareDatetime
    trade_date: date | None
    source: str = Field(min_length=1)
    coverage: float | None = Field(default=None, ge=0, le=100)
    cache: SnapshotCache
    progress: TaskProgress | None = None
    error: SnapshotError | None = None
    trace_id: str = Field(min_length=1)
