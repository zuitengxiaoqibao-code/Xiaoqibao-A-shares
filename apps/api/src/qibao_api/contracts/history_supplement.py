from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OfficialTdxPackageInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    size_label: str = Field(min_length=1)
    modified_at: AwareDatetime


class OfficialTdxArchiveInspection(BaseModel):
    model_config = ConfigDict(frozen=True)

    day_file_count: int = Field(ge=0)
    supported_file_count: int = Field(ge=0)
    latest_trade_date: date | None = None


class HistorySupplementSourceAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    state: Literal["pending", "running", "completed", "failed", "skipped"]
    detail: str = Field(min_length=1)
    observed_at: AwareDatetime


class HistorySupplementJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    state: Literal["pending", "running", "completed", "partial", "failed"]
    stage: Literal[
        "queued", "checking_metadata", "checking_cache", "validating_cache",
        "downloading", "validating",
        "importing", "extracting", "scanning", "online_repair", "final_review",
        "completed", "partial", "failed",
    ]
    percent: float = Field(ge=0, le=100)
    source_url: str
    package_modified_at: AwareDatetime | None = None
    package_size_label: str | None = None
    downloaded_bytes: int = Field(ge=0)
    total_bytes: int | None = Field(default=None, ge=0)
    package_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    package_path: str | None = None
    day_file_count: int = Field(ge=0)
    supported_file_count: int = Field(ge=0)
    latest_trade_date: date | None = None
    imported_rows: int = Field(ge=0)
    replaced_rows: int = Field(ge=0)
    skipped_rows: int = Field(ge=0)
    failed_files: int = Field(ge=0)
    error_stage: str | None = None
    error_detail: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    validated_bytes: int = Field(default=0, ge=0)
    total_validation_bytes: int = Field(default=0, ge=0)
    extracted_files: int = Field(default=0, ge=0)
    total_extract_files: int = Field(default=0, ge=0)
    processed_files: int = Field(default=0, ge=0)
    total_import_files: int = Field(default=0, ge=0)
    online_total: int = Field(default=0, ge=0)
    online_ready: int = Field(default=0, ge=0)
    online_failed: int = Field(default=0, ge=0)
    online_pending: int = Field(default=0, ge=0)
    final_target_date: date | None = None
    final_dominant_trade_date: date | None = None
    final_dominant_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    final_history_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    remaining_gap_count: int = Field(default=0, ge=0)
    final_quality: str | None = None
    final_blockers: tuple[str, ...] = ()
    result_detail: str | None = None
    source_attempts: tuple[HistorySupplementSourceAttempt, ...] = ()
