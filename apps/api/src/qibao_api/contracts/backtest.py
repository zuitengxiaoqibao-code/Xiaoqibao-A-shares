from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BacktestRequest(BaseModel):
    strategy: Literal["sma_cross", "momentum_breakout", "low_volume_pullback"] = "sma_cross"
    fast_window: int = Field(default=5, ge=2, le=120)
    slow_window: int = Field(default=20, ge=3, le=250)
    lookback_window: int = Field(default=20, ge=5, le=250)
    exit_window: int = Field(default=10, ge=2, le=120)
    volume_window: int = Field(default=20, ge=5, le=120)
    volume_ratio: Decimal = Field(default=Decimal("0.80"), gt=0, le=Decimal("2"))
    stop_loss_percent: Decimal = Field(default=Decimal("0.06"), gt=0, le=Decimal("0.30"))
    take_profit_percent: Decimal = Field(default=Decimal("0.18"), gt=0, le=Decimal("1"))
    initial_cash: Decimal = Field(default=Decimal("100000"), gt=0)
    commission_rate: Decimal = Field(default=Decimal("0.0003"), ge=0, le=Decimal("0.01"))
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=0, le=Decimal("0.02"))
    stamp_duty_rate: Decimal = Field(default=Decimal("0.0005"), ge=0, le=Decimal("0.01"))

    @model_validator(mode="after")
    def validate_windows(self) -> "BacktestRequest":
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be lower than slow_window")
        if self.exit_window > self.lookback_window:
            raise ValueError("exit_window must not exceed lookback_window")
        return self


class Trade(BaseModel):
    side: Literal["buy", "sell"]
    signal_date: date
    trade_date: date
    price: Decimal
    shares: int = Field(gt=0)
    gross_amount: Decimal
    fees: Decimal
    stamp_duty: Decimal = Field(default=Decimal("0"), ge=0)


class EquityPoint(BaseModel):
    trade_date: date
    equity: Decimal
    cash: Decimal
    shares: int = Field(ge=0)
    market_value: Decimal


class PerformanceMetrics(BaseModel):
    annualized_return: Decimal
    annualized_volatility: Decimal = Field(ge=0)
    sharpe_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    win_rate: Decimal | None = Field(default=None, ge=0, le=1)
    profit_loss_ratio: Decimal | None = Field(default=None, ge=0)
    turnover_rate: Decimal = Field(ge=0)
    closed_trade_count: int = Field(ge=0)
    expected_value: Decimal | None = None
    max_consecutive_losses: int = Field(default=0, ge=0)


class BacktestSegmentResult(BaseModel):
    name: Literal["train", "validation", "out_of_sample"]
    start_date: date
    end_date: date
    bar_count: int = Field(gt=0)
    starting_equity: Decimal = Field(gt=0)
    ending_equity: Decimal = Field(gt=0)
    total_return: Decimal
    max_drawdown: Decimal = Field(ge=0, le=1)


class BacktestRollingWindow(BaseModel):
    name: Literal["early", "middle", "recent"]
    start_date: date
    end_date: date
    bar_count: int = Field(gt=0)
    starting_equity: Decimal = Field(gt=0)
    ending_equity: Decimal = Field(gt=0)
    total_return: Decimal
    max_drawdown: Decimal = Field(ge=0, le=1)
    evaluation_status: Literal["available", "gated"]


class MarketRegimeResult(BaseModel):
    name: Literal["bull", "bear", "sideways"]
    bar_count: int = Field(ge=0)
    total_return: Decimal
    closed_trade_count: int = Field(default=0, ge=0)
    win_rate: Decimal | None = Field(default=None, ge=0, le=1)
    expected_value: Decimal | None = None
    profit_loss_ratio: Decimal | None = Field(default=None, ge=0)
    max_consecutive_losses: int = Field(default=0, ge=0)


class SignalDecayPoint(BaseModel):
    horizon: Literal[1, 3, 5, 10, 20]
    sample_count: int = Field(ge=0)
    average_return: Decimal | None = None
    hit_rate: Decimal | None = Field(default=None, ge=0, le=1)


class BacktestEvidence(BaseModel):
    sample_status: Literal["insufficient", "descriptive", "segmented"] = "insufficient"
    minimum_closed_trades: int = Field(default=5, ge=1)
    closed_trade_count: int = Field(default=0, ge=0)
    source_bar_count: int = Field(default=0, ge=0)
    lookahead_check: Literal["passed", "not_run"] = "not_run"
    segment_status: Literal["unavailable", "partial", "ready"] = "unavailable"
    parameter_policy: Literal["frozen_before_validation"] = "frozen_before_validation"
    out_of_sample_tuning: Literal["prohibited"] = "prohibited"
    parameter_snapshot_hash: str = Field(default="", pattern=r"^$|^[0-9a-f]{64}$")
    survivorship_bias_check: Literal["unresolved"] = "unresolved"
    suspension_handling: Literal["zero_volume_untradable"] = "zero_volume_untradable"
    limit_handling: Literal["opening_limit_untradable"] = "opening_limit_untradable"
    cost_policy: Literal["commission_slippage_stamp_duty"] = "commission_slippage_stamp_duty"
    conclusion_metrics_available: bool = False
    gated_metrics: tuple[str, ...] = ()


class BacktestResult(BaseModel):
    symbol: str
    strategy: str
    initial_cash: Decimal
    ending_equity: Decimal
    total_return: Decimal
    max_drawdown: Decimal
    total_cost: Decimal
    request_snapshot: BacktestRequest | None = None
    metrics: PerformanceMetrics
    segments: list[BacktestSegmentResult] = Field(default_factory=list)
    rolling_windows: list[BacktestRollingWindow] = Field(default_factory=list)
    market_regimes: list[MarketRegimeResult] = Field(default_factory=list)
    signal_decay: list[SignalDecayPoint] = Field(default_factory=list)
    evidence: BacktestEvidence = Field(default_factory=BacktestEvidence)
    trades: list[Trade]
    equity_curve: list[EquityPoint]
    warnings: list[str] = Field(default_factory=list)
