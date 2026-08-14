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
HistoryCoverageQuality: TypeAlias = Literal[
    "ready", "partial", "stale", "unavailable", "error"
]
HistoryGapKind: TypeAlias = Literal[
    "missing_history", "insufficient_history", "behind_dominant_date"
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
    dominant_trade_date: date | None = None
    dominant_date_count: int = Field(default=0, ge=0)
    dominant_date_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    fragmented_latest_count: int = Field(default=0, ge=0)
    missing_history_count: int = Field(default=0, ge=0)
    quality: HistoryCoverageQuality = "unavailable"
    blockers: tuple[str, ...] = ()


class HistoryCoverageGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    bar_count: int = Field(ge=0)
    latest_trade_date: date | None = None
    gap_kind: HistoryGapKind


class HistoryRepairCenter(BaseModel):
    model_config = ConfigDict(frozen=True)

    coverage: HistoryCoverageSummary
    current_job: HistorySyncJob | None = None
    gaps: tuple[HistoryCoverageGap, ...] = ()
    total_gap_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)


class HistoryRepairAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    audit_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    mode: HistorySyncMode
    target_date: date
    started_at: AwareDatetime
    completed_at: AwareDatetime
    source: str = Field(min_length=1)
    gap_count_before: int = Field(ge=0)
    coverage_before_percent: float | None = Field(default=None, ge=0, le=100)
    written_rows: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    coverage_after_percent: float | None = Field(default=None, ge=0, le=100)
    final_state: HistorySyncState
    failure_reasons: tuple[str, ...] = ()
