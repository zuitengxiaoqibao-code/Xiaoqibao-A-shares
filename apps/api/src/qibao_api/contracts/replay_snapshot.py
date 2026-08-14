from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ReplayInputReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source: str = Field(min_length=1)
    observed_at: AwareDatetime | None = None
    status: Literal["ready", "partial", "stale", "unavailable", "error"]


class ReplaySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(pattern=r"^replay-[0-9a-f]{24}$")
    trading_date: date
    captured_at: AwareDatetime
    strategy_version: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_health_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs: tuple[ReplayInputReference, ...]


class ReplaySnapshotList(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: AwareDatetime
    trading_date: date | None = None
    snapshots: tuple[ReplaySnapshot, ...] = ()


class ReplayCaptureRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_date: date | None = None
    strategy_version: str = Field(default="a-share-short-strategy-v2.0", min_length=1)

