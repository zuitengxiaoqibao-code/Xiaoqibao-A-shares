from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataQualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    severity: Literal["warning", "blocking"]
    detail: str = Field(min_length=1)
    trade_date: date | None = None
    observed_value: Decimal | None = None


class DataQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "error"]
    blocked: bool
    sample_count: int = Field(ge=0)
    issues: tuple[DataQualityIssue, ...] = ()
