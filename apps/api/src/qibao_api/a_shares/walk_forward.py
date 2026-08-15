from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean, pstdev
from typing import Any

from qibao_api.contracts.backtest import BacktestRequest, BacktestResult, SignalDecayPoint
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.walk_forward import (
    WalkForwardReport,
    WalkForwardRequest,
    WalkForwardWindow,
)
from qibao_api.zhongshu.backtest import BacktestEngine


FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")


def _q(value: Decimal, places: Decimal = FOUR_PLACES) -> Decimal:
    return value.quantize(places, rounding=ROUND_HALF_UP)


def _closed_returns(result: BacktestResult) -> list[Decimal]:
    entry = None
    returns: list[Decimal] = []
    for trade in result.trades:
        if trade.side == "buy":
            entry = trade.gross_amount + trade.fees
        elif entry is not None and trade.side == "sell":
            exit_value = trade.gross_amount - trade.fees
            returns.append(exit_value / entry - Decimal("1"))
            entry = None
    return returns


def _daily_returns(result: BacktestResult) -> list[float]:
    values = [point.equity for point in result.equity_curve]
    return [
        float(values[index] / values[index - 1] - Decimal("1"))
        for index in range(1, len(values))
        if values[index - 1] > 0
    ]


def _aggregate_decay(results: Sequence[BacktestResult]) -> tuple[SignalDecayPoint, ...]:
    points: list[SignalDecayPoint] = []
    for horizon in (1, 3, 5, 10, 20):
        selected = [
            item
            for result in results
            for item in result.signal_decay
            if item.horizon == horizon and item.sample_count > 0
        ]
        sample_count = sum(item.sample_count for item in selected)
        average_return = None
        hit_rate = None
        if sample_count:
            average_return = _q(sum(
                (item.average_return or Decimal("0")) * item.sample_count
                for item in selected
            ) / sample_count)
            hit_rate = _q(sum(
                (item.hit_rate or Decimal("0")) * item.sample_count
                for item in selected
            ) / sample_count)
        points.append(SignalDecayPoint(
            horizon=horizon,
            sample_count=sample_count,
            average_return=average_return,
            hit_rate=hit_rate,
        ))
    return tuple(points)


def _parameter_hash(request: WalkForwardRequest) -> str:
    return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()


def run_walk_forward(
    dataset: Sequence[DailyBar],
    windows: WalkForwardRequest,
    costs: Mapping[str, Any] | None = None,
    *,
    generated_at: datetime | None = None,
) -> WalkForwardReport:
    generated_at = generated_at or datetime.now(timezone.utc)
    ordered = sorted(dataset, key=lambda item: item.trade_date)
    symbol = ordered[0].symbol if ordered else "000001"
    sources = tuple(dict.fromkeys(item.source for item in ordered))
    source = " / ".join(sources) if sources else "unavailable"
    limitations: list[str] = [
        "survivorship_bias_unresolved",
        "corporate_actions_not_adjusted",
        "benchmark_not_available",
    ]
    if len({item.symbol for item in ordered}) > 1:
        limitations.append("mixed_symbols_in_dataset")
        ordered = [item for item in ordered if item.symbol == symbol]
    if len({item.trade_date for item in ordered}) != len(ordered):
        limitations.append("duplicate_trade_dates")
        deduplicated = {item.trade_date: item for item in ordered}
        ordered = [deduplicated[key] for key in sorted(deduplicated)]
    if len(sources) > 1:
        limitations.append("mixed_bar_sources")

    request = windows.backtest
    if costs:
        allowed = {
            "commission_rate", "slippage_rate", "stamp_duty_rate", "initial_cash"
        }
        request = request.model_copy(update={
            key: value for key, value in costs.items() if key in allowed
        })
        request = BacktestRequest.model_validate(request)
    total_width = windows.train_bars + windows.validation_bars + windows.test_bars
    if len(ordered) < total_width:
        limitations.append("insufficient_bars_for_walk_forward")
        return WalkForwardReport(
            symbol=symbol,
            status="unavailable",
            generated_at=generated_at,
            source=source,
            window_count=0,
            closed_trade_count=0,
            minimum_closed_trades=windows.minimum_closed_trades,
            parameter_snapshot_hash=_parameter_hash(windows),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    engine = BacktestEngine()
    window_rows: list[WalkForwardWindow] = []
    test_results: list[BacktestResult] = []
    for start in range(0, len(ordered) - total_width + 1, windows.step_bars):
        train_end = start + windows.train_bars
        validation_end = train_end + windows.validation_bars
        test_end = validation_end + windows.test_bars
        train = ordered[start:train_end]
        validation = ordered[train_end:validation_end]
        test = ordered[validation_end:test_end]
        try:
            train_result = engine.run(request, train)
            validation_result = engine.run(request, validation)
            test_result = engine.run(request, test)
        except ValueError:
            limitations.append("window_has_insufficient_strategy_history")
            continue
        test_results.append(test_result)
        window_rows.append(WalkForwardWindow(
            index=len(window_rows) + 1,
            train_start=train[0].trade_date,
            train_end=train[-1].trade_date,
            validation_start=validation[0].trade_date,
            validation_end=validation[-1].trade_date,
            test_start=test[0].trade_date,
            test_end=test[-1].trade_date,
            train_return=train_result.total_return,
            validation_return=validation_result.total_return,
            test_return=test_result.total_return,
            test_max_drawdown=test_result.max_drawdown,
            test_closed_trade_count=test_result.metrics.closed_trade_count,
        ))

    if not window_rows:
        limitations.append("no_valid_walk_forward_window")
        return WalkForwardReport(
            symbol=symbol,
            status="unavailable",
            generated_at=generated_at,
            source=source,
            window_count=0,
            closed_trade_count=0,
            minimum_closed_trades=windows.minimum_closed_trades,
            parameter_snapshot_hash=_parameter_hash(windows),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    closed_returns = [value for result in test_results for value in _closed_returns(result)]
    closed_count = len(closed_returns)
    max_drawdown = max(result.max_drawdown for result in test_results)
    average_test_return = _q(
        sum((result.total_return for result in test_results), Decimal("0"))
        / Decimal(len(test_results))
    )
    sample_ready = closed_count >= windows.minimum_closed_trades
    if not sample_ready:
        limitations.append("closed_trade_sample_below_minimum")
        return WalkForwardReport(
            symbol=symbol,
            status="partial",
            generated_at=generated_at,
            source=source,
            window_count=len(window_rows),
            windows=tuple(window_rows),
            closed_trade_count=closed_count,
            minimum_closed_trades=windows.minimum_closed_trades,
            max_drawdown=max_drawdown,
            average_test_return=average_test_return,
            factor_decay=_aggregate_decay(test_results),
            parameter_snapshot_hash=_parameter_hash(windows),
            limitations=tuple(dict.fromkeys(limitations)),
        )

    wins = [value for value in closed_returns if value > 0]
    losses = [value for value in closed_returns if value < 0]
    win_rate = _q(Decimal(len(wins)) / Decimal(closed_count))
    average_win = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")
    average_loss = abs(sum(losses, Decimal("0")) / len(losses)) if losses else Decimal("0")
    profit_loss_ratio = _q(average_win / average_loss) if average_loss > 0 else Decimal("0")
    daily_returns = [value for result in test_results for value in _daily_returns(result)]
    sharpe = None
    if len(daily_returns) >= 2 and pstdev(daily_returns) > 0:
        sharpe = _q(Decimal(str(fmean(daily_returns) / pstdev(daily_returns) * math.sqrt(252))))
    if sharpe is None:
        limitations.append("out_of_sample_sharpe_unavailable")
        return WalkForwardReport(
            symbol=symbol,
            status="partial",
            generated_at=generated_at,
            source=source,
            window_count=len(window_rows),
            windows=tuple(window_rows),
            closed_trade_count=closed_count,
            minimum_closed_trades=windows.minimum_closed_trades,
            max_drawdown=max_drawdown,
            average_test_return=average_test_return,
            profit_loss_ratio=profit_loss_ratio,
            factor_decay=_aggregate_decay(test_results),
            parameter_snapshot_hash=_parameter_hash(windows),
            limitations=tuple(dict.fromkeys(limitations)),
        )
    bounded_sharpe = max(Decimal("-1"), min(Decimal("2"), sharpe))
    bounded_odds = min(Decimal("3"), profit_loss_ratio)
    score = max(Decimal("0"), min(Decimal("100"), (
        Decimal("40")
        + win_rate * Decimal("30")
        + (bounded_sharpe + Decimal("1")) / Decimal("3") * Decimal("15")
        + bounded_odds / Decimal("3") * Decimal("15")
        - max_drawdown * Decimal("40")
    )))
    return WalkForwardReport(
        symbol=symbol,
        status="ready",
        generated_at=generated_at,
        source=source,
        window_count=len(window_rows),
        windows=tuple(window_rows),
        closed_trade_count=closed_count,
        minimum_closed_trades=windows.minimum_closed_trades,
        win_rate=win_rate,
        profit_loss_ratio=profit_loss_ratio,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        average_test_return=average_test_return,
        strategy_score=_q(score, TWO_PLACES),
        score_formula="oos-v1:win_rate+sharpe+profit_loss_ratio-max_drawdown",
        factor_decay=_aggregate_decay(test_results),
        parameter_snapshot_hash=_parameter_hash(windows),
        limitations=tuple(dict.fromkeys(limitations)),
    )
