from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.backtest import BacktestRequest, SignalDecayPoint


class WalkForwardRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    backtest: BacktestRequest = Field(default_factory=BacktestRequest)
    train_bars: int = Field(default=120, ge=20, le=1000)
    validation_bars: int = Field(default=60, ge=10, le=500)
    test_bars: int = Field(default=60, ge=10, le=500)
    step_bars: int = Field(default=60, ge=1, le=500)
    minimum_closed_trades: int = Field(default=5, ge=5, le=1000)


class WalkForwardWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=1)
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    train_return: Decimal
    validation_return: Decimal
    test_return: Decimal
    test_max_drawdown: Decimal = Field(ge=0, le=1)
    test_closed_trade_count: int = Field(ge=0)


class WalkForwardReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    status: Literal["ready", "partial", "unavailable"]
    generated_at: AwareDatetime
    source: str = Field(min_length=1)
    window_count: int = Field(ge=0)
    windows: tuple[WalkForwardWindow, ...] = ()
    closed_trade_count: int = Field(ge=0)
    minimum_closed_trades: int = Field(ge=5)
    win_rate: Decimal | None = Field(default=None, ge=0, le=1)
    profit_loss_ratio: Decimal | None = Field(default=None, ge=0)
    max_drawdown: Decimal | None = Field(default=None, ge=0, le=1)
    sharpe_ratio: Decimal | None = None
    average_test_return: Decimal | None = None
    strategy_score: Decimal | None = Field(default=None, ge=0, le=100)
    score_formula: str | None = None
    factor_decay: tuple[SignalDecayPoint, ...] = ()
    parameter_policy: Literal["frozen_before_validation"] = "frozen_before_validation"
    out_of_sample_tuning: Literal["prohibited"] = "prohibited"
    parameter_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_conclusion_gate(self) -> "WalkForwardReport":
        if self.status != "ready" and any((
            self.strategy_score is not None,
            self.win_rate is not None,
            self.sharpe_ratio is not None,
        )):
            raise ValueError("non-ready walk-forward report cannot expose conclusion metrics")
        if self.status == "ready" and self.strategy_score is None:
            raise ValueError("ready walk-forward report requires strategy_score")
        if self.status in {"partial", "unavailable"} and not self.limitations:
            raise ValueError("non-ready walk-forward report requires limitations")
        return self
