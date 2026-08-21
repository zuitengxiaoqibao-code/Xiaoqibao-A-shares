from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


PageSnapshotState = Literal["ready", "partial", "stale", "unavailable", "error"]


class PageSnapshot(BaseModel):
    menu: str = Field(min_length=1)
    state: PageSnapshotState
    latency_ms: int = Field(ge=0)
    cache_frame_ms: int | None = Field(default=None, ge=0)
    usable_content: bool
    reason: str | None = None
    observed_at: datetime | None = None
    trade_date: date | None = None
    source: str = Field(min_length=1)
    coverage: float | None = Field(default=None, ge=0, le=100)
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    snapshot_versions: dict[str, int] = Field(default_factory=dict)
    refresh_policy: str = Field(min_length=1)

