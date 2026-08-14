from datetime import date, timedelta
from decimal import Decimal

from qibao_api.contracts.backtest import BacktestRequest
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.backtest import BacktestEngine


def bars_from_prices(closes: list[str], opens: list[str] | None = None) -> list[DailyBar]:
    opens = opens or closes
    start = date(2026, 7, 1)
    bars = []
    for index, (open_value, close_value) in enumerate(zip(opens, closes, strict=True)):
        open_price = Decimal(open_value)
        close_price = Decimal(close_value)
        bars.append(DailyBar(
            symbol="600000", trade_date=start + timedelta(days=index), open=open_price,
            high=max(open_price, close_price) + Decimal("0.10"),
            low=min(open_price, close_price) - Decimal("0.10"), close=close_price,
            volume=100000, amount=Decimal("1000000"), source="fixture",
        ))
    return bars


def test_cross_signal_executes_at_next_day_open() -> None:
    bars = bars_from_prices(["10", "9", "8", "12", "13"])
    request = BacktestRequest(fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0)

    result = BacktestEngine().run(request, bars)

    assert len(result.trades) == 1
    assert result.trades[0].signal_date == bars[3].trade_date
    assert result.trades[0].trade_date == bars[4].trade_date
    assert result.trades[0].price == bars[4].open


def test_costs_reduce_ending_equity() -> None:
    bars = bars_from_prices(
        ["10", "9", "8", "12", "14"],
        ["10", "9", "8", "12", "12.50"],
    )
    free = BacktestEngine().run(BacktestRequest(fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0), bars)
    costly = BacktestEngine().run(BacktestRequest(fast_window=2, slow_window=3), bars)

    assert costly.ending_equity < free.ending_equity
    assert costly.total_cost > 0


def test_sell_cost_includes_a_share_stamp_duty() -> None:
    bars = bars_from_prices(
        ["10", "9", "8", "12", "15", "8", "8"],
        ["10", "9", "8", "12", "12.5", "15", "8"],
    )
    without_tax = BacktestEngine().run(BacktestRequest(
        fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0,
        stamp_duty_rate=0,
    ), bars)
    taxed = BacktestEngine().run(BacktestRequest(
        fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0,
        stamp_duty_rate=Decimal("0.0005"),
    ), bars)

    sell = next(trade for trade in taxed.trades if trade.side == "sell")
    assert sell.stamp_duty == sell.gross_amount * Decimal("0.0005")
    assert sell.fees == sell.stamp_duty
    assert taxed.ending_equity < without_tax.ending_equity


def test_suspended_bar_defers_pending_order_until_the_next_tradable_open() -> None:
    bars = bars_from_prices(["10", "9", "8", "12", "12", "13"])
    bars[4] = bars[4].model_copy(update={"volume": 0, "amount": Decimal("0")})
    request = BacktestRequest(
        fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0,
    )

    result = BacktestEngine().run(request, bars)

    assert result.trades[0].signal_date == bars[3].trade_date
    assert result.trades[0].trade_date == bars[5].trade_date
    assert any("停牌" in warning for warning in result.warnings)


def test_backtest_discloses_unadjusted_and_uncontrolled_data_biases() -> None:
    bars = bars_from_prices(["10", "9", "8", "12", "14"])

    result = BacktestEngine().run(
        BacktestRequest(fast_window=2, slow_window=3),
        bars,
    )

    assert "corporate_actions_not_adjusted" in result.warnings
    assert "benchmark_not_available" in result.warnings
    assert "survivorship_bias_not_eliminated" in result.warnings


def test_backtest_exposes_sample_policy_and_lookahead_check() -> None:
    bars = bars_from_prices([str(10 + ((index // 4) % 2) * 3 + (index % 4)) for index in range(90)])

    result = BacktestEngine().run(
        BacktestRequest(fast_window=2, slow_window=3),
        bars,
    )

    assert result.evidence.sample_status == "segmented"
    assert result.evidence.minimum_closed_trades == 5
    assert result.evidence.source_bar_count == 90
    assert result.evidence.lookahead_check == "passed"
    assert result.evidence.segment_status == "ready"
    assert result.request_snapshot is not None
    assert result.request_snapshot.fast_window == 2
    assert result.request_snapshot.slow_window == 3


def test_limit_up_open_rejects_buy() -> None:
    bars = bars_from_prices(
        ["10", "9", "8", "12", "13.20"],
        ["10", "9", "8", "12", "13.20"],
    )

    result = BacktestEngine().run(BacktestRequest(fast_window=2, slow_window=3), bars)

    assert result.trades == []
    assert any("涨停" in warning for warning in result.warnings)


def test_momentum_breakout_uses_configured_lookback_and_next_open() -> None:
    bars = bars_from_prices(["10", "10.1", "10.2", "10.3", "10.4", "11", "11.2"])
    request = BacktestRequest(
        strategy="momentum_breakout", lookback_window=5, exit_window=2,
        commission_rate=0, slippage_rate=0,
    )

    result = BacktestEngine().run(request, bars)

    assert result.trades[0].side == "buy"
    assert result.trades[0].signal_date == bars[5].trade_date
    assert result.trades[0].trade_date == bars[6].trade_date


def test_long_history_returns_independent_train_validation_and_out_of_sample_results() -> None:
    closes = [str(10 + ((index // 5) % 2) * 3 + (index % 5)) for index in range(90)]
    bars = bars_from_prices(closes)

    result = BacktestEngine().run(
        BacktestRequest(fast_window=2, slow_window=3, commission_rate=0, slippage_rate=0),
        bars,
    )

    assert [segment.name for segment in result.segments] == ["train", "validation", "out_of_sample"]
    assert result.segments[0].start_date == bars[0].trade_date
    assert result.segments[0].end_date < result.segments[1].start_date
    assert result.segments[1].end_date < result.segments[2].start_date
    assert all(segment.bar_count > 3 for segment in result.segments)
    assert all(segment.starting_equity == result.initial_cash for segment in result.segments)
    assert result.evidence.parameter_policy == "frozen_before_validation"
    assert result.evidence.out_of_sample_tuning == "prohibited"
    assert result.evidence.survivorship_bias_check == "unresolved"
    assert len(result.evidence.parameter_snapshot_hash) == 64
    assert {regime.name for regime in result.market_regimes} == {"bull", "bear", "sideways"}
    assert len(result.rolling_windows) == 3
    assert result.rolling_windows[0].end_date > result.rolling_windows[0].start_date
    assert result.rolling_windows[0].end_date > result.rolling_windows[1].start_date
    assert result.rolling_windows[-1].evaluation_status == "available"
    assert {point.horizon for point in result.signal_decay} == {1, 3, 5, 10, 20}
    assert all(point.sample_count >= 0 for point in result.signal_decay)
    assert result.metrics.max_consecutive_losses >= 0
    assert all(regime.closed_trade_count >= 0 for regime in result.market_regimes)


def test_rolling_evaluation_is_gated_when_closed_trade_sample_is_small() -> None:
    bars = bars_from_prices(["10" for _ in range(30)])

    result = BacktestEngine().run(BacktestRequest(fast_window=2, slow_window=3), bars)

    assert result.metrics.closed_trade_count < 5
    assert len(result.rolling_windows) == 3
    assert all(window.evaluation_status == "gated" for window in result.rolling_windows)
    assert result.evidence.conclusion_metrics_available is False
    assert result.metrics.win_rate is None
    assert result.metrics.sharpe_ratio is None
    assert "win_rate" in result.evidence.gated_metrics


def test_segment_evidence_is_unavailable_when_closed_trade_sample_is_small() -> None:
    bars = bars_from_prices(["10" for _ in range(30)])

    result = BacktestEngine().run(
        BacktestRequest(fast_window=2, slow_window=3),
        bars,
    )

    assert result.metrics.closed_trade_count < result.evidence.minimum_closed_trades
    assert result.segments == []
    assert result.evidence.sample_status == "insufficient"
    assert result.evidence.segment_status == "unavailable"
    assert all(window.evaluation_status == "gated" for window in result.rolling_windows)
