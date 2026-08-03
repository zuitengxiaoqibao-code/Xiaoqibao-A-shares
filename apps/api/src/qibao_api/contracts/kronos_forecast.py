from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KronosForecastStatus = Literal["ready", "unavailable", "insufficient", "error"]


class KronosForecastPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_date: date
    median_close: Decimal = Field(gt=0)
    lower_close: Decimal = Field(gt=0)
    upper_close: Decimal = Field(gt=0)


class KronosForecastSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    median_return_pct: Decimal
    upper_return_pct: Decimal
    lower_return_pct: Decimal
    path_dispersion_pct: Decimal = Field(ge=0)
    downside_probability_pct: Decimal = Field(ge=0, le=100)


class KronosForecastResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: KronosForecastStatus
    symbol: str = Field(pattern=r"^\d{6}$")
    as_of: date
    observed_through: date | None = None
    model: str
    frequency: Literal["1d"] = "1d"
    lookback_bars: int = Field(ge=0)
    horizon_bars: int = Field(ge=0)
    sample_count: int = Field(ge=0)
    summary: KronosForecastSummary | None = None
    points: tuple[KronosForecastPoint, ...] = ()
    reasons: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
