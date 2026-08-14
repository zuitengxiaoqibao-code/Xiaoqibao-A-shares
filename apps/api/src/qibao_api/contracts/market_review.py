from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry


ReviewQuality = Literal["ready", "partial", "stale", "unavailable"]
ReviewCategory = Literal[
    "consecutive_limit_up",
    "first_limit_up",
    "new_high_100",
    "previous_limit_feedback",
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
    prior_close: Decimal | None = Field(default=None, gt=0)
    prior_change_percent: Decimal | None = None
    turnover_rate: Decimal | None = Field(default=None, ge=0)
    seal_amount_yi: Decimal | None = Field(default=None, ge=0)
    failed_limit_count: int | None = Field(default=None, ge=0)
    first_seal_time: str | None = None
    volume_multiple: Decimal | None = Field(default=None, ge=0)
    reference_high: Decimal | None = Field(default=None, gt=0)
    window_days: int | None = Field(default=None, ge=1)
    range_position_percent: Decimal | None = Field(default=None, ge=0, le=100)


class MarketIntervalReviewStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    start_date: date
    end_date: date
    start_close: Decimal = Field(gt=0)
    end_close: Decimal = Field(gt=0)
    return_percent: Decimal
    amplitude_percent: Decimal = Field(ge=0)
    amount_yi: Decimal = Field(ge=0)
    source: str = "tdx-local-day"


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


class MarketDataWatermark(BaseModel):
    model_config = ConfigDict(frozen=True)

    dominant_trade_date: date | None = None
    latest_available_trade_date: date | None = None
    universe_count: int = Field(default=0, ge=0)
    history_ready_count: int = Field(default=0, ge=0)
    coverage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    fragmented_latest_count: int = Field(default=0, ge=0)
    missing_history_count: int = Field(default=0, ge=0)
    quality: ReviewQuality = "unavailable"
    blockers: tuple[str, ...] = ()


class MarketReviewSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    observed_at: AwareDatetime
    latest_trade_date: date | None = None
    latest_available_trade_date: date | None = None
    latest_available_trade_date_count: int = Field(default=0, ge=0)
    latest_trade_date_coverage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    source: str = "unavailable"
    quality: ReviewQuality = "unavailable"
    universe_count: int = Field(default=0, ge=0)
    history_ready_count: int = Field(default=0, ge=0)
    consecutive_limit_up: tuple[MarketReviewStock, ...] = ()
    first_limit_up: tuple[MarketReviewStock, ...] = ()
    new_high_100: tuple[MarketReviewStock, ...] = ()
    previous_limit_up: tuple[MarketReviewStock, ...] = ()
    volume_breakouts: tuple[MarketReviewStock, ...] = ()
    previous_high_breakouts: tuple[MarketReviewStock, ...] = ()
    low_position_volume: tuple[MarketReviewStock, ...] = ()
    dragon_tiger: tuple[DragonTigerStock, ...] = ()
    watermark: MarketDataWatermark = Field(default_factory=MarketDataWatermark)
    evidence_ledger: tuple[EvidenceLedgerEntry, ...] = ()
    warnings: tuple[str, ...] = ()
    formula_version: str = "a-share-market-review-v2"


class MarketIntervalReviewSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_start_date: date
    requested_end_date: date
    start_date: date | None = None
    end_date: date | None = None
    observed_at: AwareDatetime
    source: str = "unavailable"
    quality: ReviewQuality = "unavailable"
    universe_count: int = Field(default=0, ge=0)
    valid_count: int = Field(default=0, ge=0)
    rows: tuple[MarketIntervalReviewStock, ...] = ()
    warnings: tuple[str, ...] = ()
    formula_version: str = "a-share-interval-review-v1"
