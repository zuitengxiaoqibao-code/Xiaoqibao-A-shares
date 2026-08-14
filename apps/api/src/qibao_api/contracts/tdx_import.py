from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


TdxImportState = Literal["pending", "running", "paused", "completed", "failed"]


class TdxImportError(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class TdxImportJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    state: TdxImportState
    stage: str = Field(min_length=1)
    paths: tuple[str, ...]
    total_files: int = Field(ge=0)
    processed_files: int = Field(ge=0)
    imported_rows: int = Field(ge=0)
    replaced_rows: int = Field(ge=0)
    skipped_rows: int = Field(ge=0)
    failed_files: int = Field(ge=0)
    current_file: str | None = None
    latest_trade_date: str | None = None
    percent: float = Field(ge=0, le=100)
    errors: tuple[TdxImportError, ...] = ()
    created_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: datetime | None = None


class TdxImportScan(BaseModel):
    model_config = ConfigDict(frozen=True)

    scanned_paths: tuple[str, ...]
    day_files: int = Field(ge=0)
    archive_files: int = Field(ge=0)
    readable_files: int = Field(ge=0)
    latest_trade_date: str | None = None
    errors: tuple[TdxImportError, ...] = ()
