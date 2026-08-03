from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


ReviewQuality = Literal["ready", "partial", "stale", "unavailable"]
ReviewCategory = Literal[
    "consecutive_limit_up",
    "first_limit_up",
    "volume_breakout",
    "previous_high_breakout",
    "low_position_volume",
]


class MarketReviewStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    trade_date: date
    category: ReviewCategory
    close: Decimal = Field(gt=0)
    change_percent: Decimal
    amount_yi: Decimal = Field(ge=0)
    source: str = "tdx-local-day"
    board_count: int | None = Field(default=None, ge=1)
    limit_statistics: str | None = None
    turnover_rate: Decimal | None = Field(default=None, ge=0)
    seal_amount_yi: Decimal | None = Field(default=None, ge=0)
    failed_limit_count: int | None = Field(default=None, ge=0)
    first_seal_time: str | None = None
    volume_multiple: Decimal | None = Field(default=None, ge=0)
    reference_high: Decimal | None = Field(default=None, gt=0)
    window_days: int | None = Field(default=None, ge=1)
    range_position_percent: Decimal | None = Field(default=None, ge=0, le=100)


class DragonTigerSeat(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    trade_date: date
    seat_name: str = Field(min_length=1)
    direction: Literal["buy", "sell", "mixed"] = "mixed"
    buy_amount_yi: Decimal = Field(ge=0)
    sell_amount_yi: Decimal = Field(ge=0)
    net_amount_yi: Decimal
    source: str = "eastmoney-dragon-tiger"


class DragonTigerStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    trade_date: date
    reason: str = Field(min_length=1)
    change_percent: Decimal | None = None
    buy_amount_yi: Decimal = Field(ge=0)
    sell_amount_yi: Decimal = Field(ge=0)
    net_amount_yi: Decimal
    seats: tuple[DragonTigerSeat, ...] = ()
    source: str = "eastmoney-dragon-tiger"


class MarketReviewSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    observed_at: AwareDatetime
    latest_trade_date: date | None = None
    source: str = "unavailable"
    quality: ReviewQuality = "unavailable"
    universe_count: int = Field(default=0, ge=0)
    history_ready_count: int = Field(default=0, ge=0)
    consecutive_limit_up: tuple[MarketReviewStock, ...] = ()
    first_limit_up: tuple[MarketReviewStock, ...] = ()
    volume_breakouts: tuple[MarketReviewStock, ...] = ()
    previous_high_breakouts: tuple[MarketReviewStock, ...] = ()
    low_position_volume: tuple[MarketReviewStock, ...] = ()
    dragon_tiger: tuple[DragonTigerStock, ...] = ()
    warnings: tuple[str, ...] = ()
    formula_version: str = "a-share-market-review-v1"
