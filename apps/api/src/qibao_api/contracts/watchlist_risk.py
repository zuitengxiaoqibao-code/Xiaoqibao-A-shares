from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class WatchlistRiskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...] = Field(min_length=1, max_length=30)
    as_of: date | None = None


class WatchlistRiskItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    industry: str | None = None
    sectors: tuple[str, ...] = ()
    volatility_20d_percent: Decimal | None = None
    return_sample_count: int = Field(ge=0)
    status: Literal["ready", "partial", "unavailable"]
    limitations: tuple[str, ...] = ()


class WatchlistConcentration(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    symbol_count: int = Field(ge=1)
    observation_weight_percent: Decimal = Field(ge=0, le=100)
    symbols: tuple[str, ...]


class WatchlistCorrelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_symbol: str
    right_symbol: str
    correlation: Decimal = Field(ge=-1, le=1)
    overlap_days: int = Field(ge=20)


class WatchlistRiskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["observation_basket"] = "observation_basket"
    status: Literal["ready", "partial", "unavailable"]
    as_of: date
    observed_at: AwareDatetime
    valid_count: int = Field(ge=0)
    total_count: int = Field(ge=1)
    coverage_percent: Decimal = Field(ge=0, le=100)
    items: tuple[WatchlistRiskItem, ...]
    industries: tuple[WatchlistConcentration, ...] = ()
    themes: tuple[WatchlistConcentration, ...] = ()
    high_correlation_pairs: tuple[WatchlistCorrelation, ...] = ()
    warnings: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

