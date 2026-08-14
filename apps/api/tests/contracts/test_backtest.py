from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.backtest import BacktestRequest


def test_backtest_requires_fast_window_below_slow_window() -> None:
    with pytest.raises(ValidationError, match="fast_window"):
        BacktestRequest(fast_window=20, slow_window=10)


def test_backtest_requires_positive_initial_cash() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(initial_cash=Decimal("0"))


def test_backtest_accepts_parameterized_strategy_models() -> None:
    request = BacktestRequest(
        strategy="momentum_breakout",
        lookback_window=30,
        exit_window=10,
        stop_loss_percent="0.06",
        take_profit_percent="0.18",
    )

    assert request.lookback_window == 30
    assert request.exit_window == 10
    assert request.stamp_duty_rate == Decimal("0.0005")


def test_backtest_rejects_negative_stamp_duty() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(stamp_duty_rate=Decimal("-0.0001"))
