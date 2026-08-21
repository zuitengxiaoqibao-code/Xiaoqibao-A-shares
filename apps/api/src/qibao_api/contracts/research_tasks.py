from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


ResearchTaskState = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class ResearchTaskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    state: ResearchTaskState
    stage: str = Field(min_length=1)
    progress: float | None = Field(default=None, ge=0, le=100)
    processed: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, gt=0)
    error_code: str | None = None
    error_message: str | None = None
    started_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def validate_progress(self) -> "ResearchTaskSnapshot":
        if self.progress is not None and self.total is None:
            raise ValueError("progress requires a real total")
        if self.processed is not None and self.total is not None and self.processed > self.total:
            raise ValueError("processed cannot exceed total")
        if self.state in {"succeeded", "failed", "cancelled"} and self.finished_at is None:
            raise ValueError("terminal task requires finished_at")
        if self.state == "failed" and not self.error_code:
            raise ValueError("failed task requires error_code")
        return self
