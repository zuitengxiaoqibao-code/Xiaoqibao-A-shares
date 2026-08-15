from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from qibao_api.a_shares.walk_forward import run_walk_forward
from qibao_api.contracts.backtest import BacktestRequest
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.walk_forward import WalkForwardRequest


NOW = datetime(2026, 8, 15, 8, 0, tzinfo=UTC)


def bars(count: int) -> list[DailyBar]:
    result = []
    for index in range(count):
        phase = index % 8
        close = Decimal("10") + Decimal(phase if phase < 4 else 8 - phase)
        result.append(DailyBar(
            symbol="600519",
            trade_date=date(2025, 1, 1) + timedelta(days=index),
            open=close,
            high=close + Decimal("0.10"),
            low=close - Decimal("0.10"),
            close=close,
            volume=100000,
            amount=Decimal("1000000"),
            source="local-tdx",
        ))
    return result


def request(**overrides) -> WalkForwardRequest:
    values = {
        "backtest": BacktestRequest(
            fast_window=2,
            slow_window=3,
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0005"),
            stamp_duty_rate=Decimal("0.0005"),
        ),
        "train_bars": 64,
        "validation_bars": 32,
        "test_bars": 32,
        "step_bars": 32,
        "minimum_closed_trades": 5,
    }
    values.update(overrides)
    return WalkForwardRequest(**values)


def test_walk_forward_keeps_train_validation_and_test_chronological():
    report = run_walk_forward(bars(224), request(), generated_at=NOW)

    assert report.status in {"ready", "partial"}
    assert len(report.windows) == 4
    assert all(
        item.train_end < item.validation_start <= item.validation_end < item.test_start
        for item in report.windows
    )
    assert report.parameter_policy == "frozen_before_validation"
    assert report.out_of_sample_tuning == "prohibited"
    assert len(report.parameter_snapshot_hash) == 64
    assert report.source == "local-tdx"


def test_walk_forward_with_insufficient_bars_returns_unavailable_without_score():
    report = run_walk_forward(bars(80), request(), generated_at=NOW)

    assert report.status == "unavailable"
    assert report.strategy_score is None
    assert report.closed_trade_count == 0
    assert "insufficient_bars_for_walk_forward" in report.limitations


def test_walk_forward_gates_conclusion_metrics_below_closed_trade_threshold():
    report = run_walk_forward(
        bars(128),
        request(minimum_closed_trades=50),
        generated_at=NOW,
    )

    assert report.status == "partial"
    assert report.closed_trade_count < 50
    assert report.strategy_score is None
    assert report.win_rate is None
    assert report.sharpe_ratio is None
    assert "closed_trade_sample_below_minimum" in report.limitations
