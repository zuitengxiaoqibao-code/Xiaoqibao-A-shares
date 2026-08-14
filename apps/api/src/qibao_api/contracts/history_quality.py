from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


HistoryQualityStatus = Literal["ready", "partial", "unavailable"]


class HistoryQualityGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    missing_dates: tuple[date, ...] = ()
    duplicate_dates: tuple[date, ...] = ()
    future_dates: tuple[date, ...] = ()


class HistoryQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: AwareDatetime
    expected_sessions: int = Field(ge=0)
    covered_sessions: int = Field(ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0, le=1)
    symbol_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    gaps: tuple[HistoryQualityGap, ...] = ()
    status: HistoryQualityStatus
    source: str = Field(min_length=1)

