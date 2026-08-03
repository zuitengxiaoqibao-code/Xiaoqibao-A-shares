from datetime import date
from typing import Literal, TypeAlias

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


HistorySyncMode: TypeAlias = Literal["backfill", "incremental"]
HistorySyncState: TypeAlias = Literal[
    "pending", "running", "paused", "completed", "failed"
]
HistorySyncItemState: TypeAlias = Literal[
    "pending", "running", "ready", "failed", "skipped"
]


class HistorySyncJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    mode: HistorySyncMode
    target_date: date
    state: HistorySyncState
    pause_requested: bool = False
    total_count: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    tdx_ready_count: int = Field(ge=0)
    baidu_ready_count: int = Field(ge=0)
    created_at: AwareDatetime
    updated_at: AwareDatetime


class HistorySyncItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    symbol: str = Field(pattern=r"^\d{6}$")
    state: HistorySyncItemState
    attempts: int = Field(ge=0)
    source: Literal["mootdx", "baidu"] | None = None
    written_rows: int = Field(ge=0)
    error_code: str | None = None
    updated_at: AwareDatetime


class HistoryCoverageSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_date: date
    universe_count: int = Field(ge=0)
    backfill_complete_count: int = Field(ge=0)
    eligible_count: int = Field(ge=0)
    target_date_count: int = Field(ge=0)
