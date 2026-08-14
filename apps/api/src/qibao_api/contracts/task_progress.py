from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class TaskProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    status: TaskStatus
    stage: str = Field(min_length=1)
    processed: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, gt=0)
    percent: float | None = Field(default=None, ge=0, le=100)
    detail: str | None = None
    started_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: datetime | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_progress(self) -> "TaskProgress":
        if self.total is None and self.percent is not None:
            raise ValueError("percent requires a real total")
        if self.processed is not None and self.total is not None and self.processed > self.total:
            raise ValueError("processed cannot exceed total")
        if self.status in {"succeeded", "failed", "cancelled"} and self.finished_at is None:
            raise ValueError("terminal task requires finished_at")
        return self

