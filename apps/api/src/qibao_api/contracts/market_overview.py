from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.field_evidence import FieldEvidence
from qibao_api.contracts.market_review import MarketReviewSnapshot


OverviewQuality = Literal["ready", "partial", "stale", "unavailable"]
OverviewMarketPhase = Literal["premarket", "intraday", "postclose", "closed"]
OverviewMarketFreshness = Literal[
    "live", "previous_close", "final", "stale", "unavailable", "unknown"
]


class OverviewSentiment(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: Decimal | None = Field(default=None, ge=0, le=100)
    band: str
    coverage_percent: Decimal = Field(ge=0, le=100)
    quality: OverviewQuality
    observed_at: AwareDatetime


class OverviewBreadth(BaseModel):
    model_config = ConfigDict(frozen=True)

    rising_count: int = Field(ge=0)
    falling_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "OverviewBreadth":
        if self.rising_count + self.falling_count + self.flat_count != self.valid_count:
            raise ValueError("market breadth counts must equal valid count")
        return self


class OverviewLimitEcology(BaseModel):
    model_config = ConfigDict(frozen=True)

    limit_up_count: int = Field(ge=0)
    limit_down_count: int = Field(ge=0)
    broken_limit_up_count: int = Field(ge=0)
    seal_rate_percent: Decimal | None = Field(default=None, ge=0, le=100)


class OverviewLiquidity(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_amount_yi: Decimal | None = Field(default=None, ge=0)
    baseline_amount_yi: Decimal | None = Field(default=None, ge=0)
    relative_amount: Decimal | None = Field(default=None, ge=0)


class OverviewRegimeMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    up_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    zt_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    dt_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    median_ret: Decimal | None = None
    amt_heat: Decimal | None = Field(default=None, ge=0)
    strong_close_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    weak_close_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    limit_fail_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    panic_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    amp_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    net_positive_ratio: Decimal | None = Field(default=None, ge=0, le=100)
    net_positive_ratio_coverage_percent: Decimal | None = Field(
        default=None, ge=0, le=100
    )
    large_amount_strong_close_ratio: Decimal | None = Field(
        default=None, ge=0, le=100
    )
    factor_coverage_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100
    )


class OverviewRegimeAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    regime: Literal[
        "情绪主升", "指数权重进攻", "轮动震荡",
        "冰点修复", "高位退潮", "缩量混沌",
    ] | None = None
    emotion_score: Decimal | None = Field(default=None, ge=0, le=100)
    risk_score: Decimal | None = Field(default=None, ge=0, le=100)
    previous_risk_score: Decimal | None = Field(default=None, ge=0, le=100)
    heat_score: Decimal | None = Field(default=None, ge=0, le=100)
    rotation_score: Decimal | None = Field(default=None, ge=0, le=100)
    coverage_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100
    )
    market_coef: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    suitable_strategies: tuple[str, ...] = ()
    avoid_strategies: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    missing_factors: tuple[str, ...] = ()
    rule_matched: bool = False
    quality: OverviewQuality = "unavailable"
    formula_version: str = "a-share-short-regime-v2.0"


class OverviewIndexQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument: str = Field(pattern=r"^(sh|sz)\d{6}$")
    name: str = Field(min_length=1)
    value: Decimal = Field(gt=0)
    change: Decimal
    change_percent: Decimal
    observed_at: AwareDatetime
    source: str = Field(min_length=1)
    quality: OverviewQuality


class OverviewMinutePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: AwareDatetime
    price: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class OverviewStockQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    change_percent: Decimal
    amount_yi: Decimal | None = Field(default=None, ge=0)
    market_cap_yi: Decimal | None = Field(default=None, ge=0)
    turnover_rate: Decimal | None = Field(default=None, ge=0)
    observed_at: AwareDatetime


class OverviewAnomaly(BaseModel):
    model_config = ConfigDict(frozen=True)

    anomaly_id: str = Field(min_length=1)
    occurred_at: AwareDatetime
    label: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    direction: Literal["positive", "negative", "neutral", "uncertain"]
    themes: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    category: str | None = None
    strength: Literal["high", "medium", "low", "unknown"] = "unknown"
    credibility: Literal[
        "multi_source_verified", "verified", "pending", "rejected"
    ] = "pending"


class OverviewLiveFeedItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(min_length=1)
    occurred_at: AwareDatetime
    headline: str = Field(min_length=1)
    summary: str = ""
    themes: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    source: str = Field(min_length=1)
    review_state: str = Field(min_length=1)


class OverviewSectorStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    change_percent: Decimal | None = None
    amount_yi: Decimal | None = Field(default=None, ge=0)
    market_cap_yi: Decimal | None = Field(default=None, ge=0)
    first_limit_time: str | None = None
    position: str = "题材成员"
    quality: OverviewQuality = "unavailable"


class OverviewFeatureStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    previous_close: Decimal = Field(gt=0)
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    amount_yi: Decimal = Field(ge=0)
    change_percent: Decimal
    state: Literal["limit_up", "broken_limit_up", "limit_down", "active"]
    observed_at: AwareDatetime
    source: str = Field(min_length=1)
    quality: OverviewQuality


class OverviewLargeOrderFlow(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    latest_trade_date: date
    observed_at: AwareDatetime
    main_net_yi: Decimal
    large_net_yi: Decimal
    super_net_yi: Decimal
    direction: Literal["inflow", "outflow", "balanced"]
    source: str = Field(min_length=1)
    quality: OverviewQuality


class OverviewSectorFundFlowPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    sector_code: str = Field(pattern=r"^BK\d{4}$")
    sector_name: str = Field(min_length=1)
    observed_at: AwareDatetime
    main_net_yi: Decimal
    large_net_yi: Decimal | None = None
    super_net_yi: Decimal | None = None
    source: str = Field(min_length=1)
    quality: OverviewQuality


class OverviewOfficialEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(min_length=1)
    event_date: date
    event_type: Literal["subscription", "allotment", "listing"]
    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    observed_at: AwareDatetime
    source: str = Field(min_length=1)
    quality: OverviewQuality


class OverviewSector(BaseModel):
    model_config = ConfigDict(frozen=True)

    sector_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    change_percent: Decimal | None = None
    amount_yi: Decimal | None = Field(default=None, ge=0)
    limit_up_count: int = Field(default=0, ge=0)
    rising_count: int = Field(default=0, ge=0)
    falling_count: int = Field(default=0, ge=0)
    stock_count: int = Field(default=0, ge=0)


class OverviewMarketDataStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "unavailable"
    quality: OverviewQuality = "unavailable"
    observed_at: AwareDatetime | None = None
    quote_count: int = Field(default=0, ge=0)
    universe_count: int = Field(default=0, ge=0)
    phase: OverviewMarketPhase = "closed"
    freshness: OverviewMarketFreshness = "unknown"


class OverviewDataScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    market_aggregate: Literal["full_a_share_market", "unavailable"] = "unavailable"
    market_quote_count: int = Field(default=0, ge=0)
    market_universe_count: int = Field(default=0, ge=0)
    stock_sample: Literal["representative", "none"] = "none"
    stock_sample_count: int = Field(default=0, ge=0)
    sector_sample: Literal["strong_sector", "news_linked", "none"] = "none"
    sector_sample_count: int = Field(default=0, ge=0)
    large_order_sample_count: int = Field(default=0, ge=0)
    sector_fund_flow_sample_count: int = Field(default=0, ge=0)
    sector_fund_flow_snapshot_count: int = Field(default=0, ge=0)


class OverviewMarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: AwareDatetime
    source: str = Field(min_length=1)
    quality: OverviewQuality
    quote_count: int = Field(ge=0)
    universe_count: int = Field(ge=0)
    median_change_percent: Decimal | None = None
    breadth: OverviewBreadth
    limit_ecology: OverviewLimitEcology
    liquidity: OverviewLiquidity
    regime_metrics: OverviewRegimeMetrics = Field(
        default_factory=OverviewRegimeMetrics
    )
    sectors: tuple[OverviewSector, ...] = ()
    sector_stocks: dict[str, tuple[OverviewSectorStock, ...]] = Field(
        default_factory=dict
    )
    market_stocks: tuple[OverviewFeatureStock, ...] = ()


class MarketOverviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "unavailable"]
    as_of: date
    observed_at: AwareDatetime
    sentiment: OverviewSentiment
    breadth: OverviewBreadth
    limit_ecology: OverviewLimitEcology
    liquidity: OverviewLiquidity
    regime_metrics: OverviewRegimeMetrics = Field(
        default_factory=OverviewRegimeMetrics
    )
    regime: OverviewRegimeAssessment = Field(
        default_factory=OverviewRegimeAssessment
    )
    market_data: OverviewMarketDataStatus = Field(
        default_factory=OverviewMarketDataStatus
    )
    data_scope: OverviewDataScope = Field(default_factory=OverviewDataScope)
    indices: tuple[OverviewIndexQuote, ...] = ()
    minute_series: tuple[OverviewMinutePoint, ...] = ()
    anomalies: tuple[OverviewAnomaly, ...] = ()
    live_feed: tuple[OverviewLiveFeedItem, ...] = ()
    sectors: tuple[OverviewSector, ...] = ()
    sector_stocks: dict[str, tuple[OverviewSectorStock, ...]] = Field(
        default_factory=dict
    )
    market_stocks: tuple[OverviewFeatureStock, ...] = ()
    large_order_flows: tuple[OverviewLargeOrderFlow, ...] = ()
    sector_fund_flow: tuple[OverviewSectorFundFlowPoint, ...] = ()
    official_events: tuple[OverviewOfficialEvent, ...] = ()
    field_evidence: tuple[FieldEvidence, ...] = ()
    review: MarketReviewSnapshot | None = None
    warnings: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_ready_regions(self) -> "MarketOverviewResponse":
        if self.status == "ready" and (not self.indices or not self.minute_series):
            raise ValueError("ready overview requires index quotes and minute series")
        return self
