from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


OverseasQuality = Literal["ready", "stale", "unavailable"]
OverseasTradingState = Literal["盘中", "最近收盘", "休市中"]


class OverseasInstrumentQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    region: Literal["index", "mag7"]
    price: Decimal = Field(gt=0)
    change: Decimal
    change_percent: Decimal
    observed_at: AwareDatetime
    trading_state: OverseasTradingState
    quality: OverseasQuality


class OverseasMarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    indices: tuple[OverseasInstrumentQuote, ...] = ()
    mag7: tuple[OverseasInstrumentQuote, ...] = ()
    observed_at: AwareDatetime
    source: str = Field(min_length=1)
    source_trading_date: date | None = None
    trading_label: str
    quality: OverseasQuality
    reason: str | None = None
