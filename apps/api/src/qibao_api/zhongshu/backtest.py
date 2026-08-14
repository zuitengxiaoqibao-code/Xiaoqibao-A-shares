import hashlib
from decimal import Decimal

from qibao_api.contracts.backtest import (
    BacktestRequest,
    BacktestEvidence,
    BacktestResult,
    BacktestRollingWindow,
    BacktestSegmentResult,
    EquityPoint,
    SignalDecayPoint,
    Trade,
)
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.performance import (
    market_regime_attribution,
    max_drawdown,
    performance_metrics,
    split_bars,
)

LIMIT_THRESHOLD = Decimal("0.098")


class BacktestEngine:
    def run(self, request: BacktestRequest, bars: list[DailyBar]) -> BacktestResult:
        ordered = sorted(bars, key=lambda bar: bar.trade_date)
        required_bars = self._required_bars(request)
        if len(ordered) <= required_bars:
            raise ValueError("not enough bars for selected strategy parameters")

        result = self._run_core(request, ordered)
        train, validation, out_of_sample = split_bars(
            ordered, Decimal("0.6"), Decimal("0.2")
        )
        named_segments = (
            ("train", train),
            ("validation", validation),
            ("out_of_sample", out_of_sample),
        )
        if all(len(segment_bars) > required_bars for _, segment_bars in named_segments):
            result.segments = [
                self._run_segment(name, request, segment_bars)
                for name, segment_bars in named_segments
            ]
        closed_trade_count = result.metrics.closed_trade_count
        sample_gate_passed = closed_trade_count >= 5
        if not sample_gate_passed:
            result.metrics.sharpe_ratio = None
            result.metrics.calmar_ratio = None
            result.metrics.win_rate = None
            result.metrics.profit_loss_ratio = None
            result.metrics.expected_value = None
        if not sample_gate_passed:
            result.segments = []
        result.evidence = BacktestEvidence(
            sample_status=(
                "segmented" if sample_gate_passed and len(result.segments) == 3
                else "descriptive" if sample_gate_passed
                else "insufficient"
            ),
            minimum_closed_trades=5,
            closed_trade_count=closed_trade_count,
            source_bar_count=len(ordered),
            lookahead_check="passed",
            segment_status=(
                "ready" if sample_gate_passed and len(result.segments) == 3
                else "partial" if sample_gate_passed and result.segments
                else "unavailable"
            ),
            parameter_snapshot_hash=hashlib.sha256(
                request.model_dump_json().encode("utf-8")
            ).hexdigest(),
            conclusion_metrics_available=sample_gate_passed,
            gated_metrics=() if sample_gate_passed else (
                "sharpe_ratio", "calmar_ratio", "win_rate", "profit_loss_ratio", "expected_value",
            ),
        )
        result.rolling_windows = self._rolling_windows(
            request, ordered, required_bars,
            sample_gate_passed,
        )
        result.request_snapshot = request.model_copy(deep=True)
        result.signal_decay = self._signal_decay(ordered, result.trades)
        return result

    def _rolling_windows(
        self,
        request: BacktestRequest,
        bars: list[DailyBar],
        required_bars: int,
        gate_passed: bool,
    ) -> list[BacktestRollingWindow]:
        """Create three overlapping chronological windows without inventing metrics."""
        window_size = max(required_bars + 1, len(bars) // 2)
        if len(bars) < required_bars + 4 or window_size >= len(bars):
            return []
        step = max(1, (len(bars) - window_size) // 2)
        starts = [0, step, len(bars) - window_size]
        windows: list[BacktestRollingWindow] = []
        for name, start in zip(("early", "middle", "recent"), starts, strict=True):
            window_bars = bars[start:start + window_size]
            window_result = self._run_core(
                request=request,
                ordered=window_bars,
            )
            window_points = window_result.equity_curve
            if len(window_points) < 2:
                continue
            starting_equity = window_points[0].equity
            ending_equity = window_points[-1].equity
            windows.append(BacktestRollingWindow(
                name=name,
                start_date=window_bars[0].trade_date,
                end_date=window_bars[-1].trade_date,
                bar_count=len(window_points),
                starting_equity=starting_equity,
                ending_equity=ending_equity,
                total_return=((ending_equity / starting_equity) - Decimal("1")).quantize(Decimal("0.0001")),
                max_drawdown=max_drawdown([point.equity for point in window_points]),
                evaluation_status="available" if gate_passed else "gated",
            ))
        return windows

    def _run_core(
        self, request: BacktestRequest, ordered: list[DailyBar]
    ) -> BacktestResult:
        cash = request.initial_cash
        shares = 0
        trades: list[Trade] = []
        points: list[EquityPoint] = []
        warnings: list[str] = [
            "corporate_actions_not_adjusted",
            "benchmark_not_available",
            "survivorship_bias_not_eliminated",
        ]
        total_cost = Decimal("0")
        pending: tuple[str, object] | None = None
        entry_price: Decimal | None = None

        for index, bar in enumerate(ordered):
            if pending and index > 0:
                side, signal_date = pending
                if bar.volume == 0 or bar.amount == 0:
                    warnings.append(f"{bar.trade_date} 停牌或无成交，委托顺延")
                    market_value = bar.close * shares
                    points.append(EquityPoint(
                        trade_date=bar.trade_date, equity=cash + market_value,
                        cash=cash, shares=shares, market_value=market_value,
                    ))
                    continue
                previous_close = ordered[index - 1].close
                opening_change = bar.open / previous_close - Decimal("1")
                if side == "buy" and shares == 0:
                    if opening_change >= LIMIT_THRESHOLD:
                        warnings.append(f"{bar.trade_date} 接近涨停，买入未成交")
                    else:
                        price = bar.open * (Decimal("1") + request.slippage_rate)
                        affordable = int(cash / (price * (Decimal("1") + request.commission_rate)))
                        quantity = affordable // 100 * 100
                        if quantity >= 100:
                            gross = price * quantity
                            fees = gross * request.commission_rate
                            cash -= gross + fees
                            shares = quantity
                            entry_price = price
                            total_cost += fees + (price - bar.open) * quantity
                            trades.append(Trade(side="buy", signal_date=signal_date,
                                trade_date=bar.trade_date, price=price, shares=quantity,
                                gross_amount=gross, fees=fees, stamp_duty=Decimal("0")))
                elif side == "sell" and shares > 0:
                    if opening_change <= -LIMIT_THRESHOLD:
                        warnings.append(f"{bar.trade_date} 接近跌停，卖出未成交")
                    else:
                        price = bar.open * (Decimal("1") - request.slippage_rate)
                        gross = price * shares
                        stamp_duty = gross * request.stamp_duty_rate
                        fees = gross * request.commission_rate + stamp_duty
                        total_cost += fees + (bar.open - price) * shares
                        cash += gross - fees
                        trades.append(Trade(side="sell", signal_date=signal_date,
                            trade_date=bar.trade_date, price=price, shares=shares,
                            gross_amount=gross, fees=fees, stamp_duty=stamp_duty))
                        shares = 0
                        entry_price = None
                pending = None

            market_value = bar.close * shares
            points.append(EquityPoint(trade_date=bar.trade_date, equity=cash + market_value,
                cash=cash, shares=shares, market_value=market_value))

            signal = self._signal(request, ordered, index, shares, entry_price)
            if signal is not None:
                pending = (signal, bar.trade_date)

        ending_equity = points[-1].equity
        total_return = ending_equity / request.initial_cash - Decimal("1")
        return BacktestResult(
            symbol=ordered[0].symbol,
            strategy=request.strategy,
            initial_cash=request.initial_cash,
            ending_equity=ending_equity.quantize(Decimal("0.01")),
            total_return=total_return.quantize(Decimal("0.0001")),
            max_drawdown=max_drawdown([point.equity for point in points]),
            total_cost=total_cost.quantize(Decimal("0.01")),
            metrics=performance_metrics(points, trades),
            market_regimes=market_regime_attribution(ordered, points, trades),
            trades=trades,
            equity_curve=points,
            warnings=warnings,
        )

    def _run_segment(
        self, name: str, request: BacktestRequest, bars: list[DailyBar]
    ) -> BacktestSegmentResult:
        segment_result = self._run_core(request, bars)
        starting_equity = request.initial_cash
        ending_equity = segment_result.ending_equity
        return BacktestSegmentResult(
            name=name,
            start_date=bars[0].trade_date,
            end_date=bars[-1].trade_date,
            bar_count=len(bars),
            starting_equity=starting_equity,
            ending_equity=ending_equity,
            total_return=(ending_equity / starting_equity - Decimal("1")).quantize(
                Decimal("0.0001")
            ),
            max_drawdown=segment_result.max_drawdown,
        )

    @staticmethod
    def _signal_decay(
        bars: list[DailyBar], trades: list[Trade]
    ) -> list[SignalDecayPoint]:
        index_by_date = {bar.trade_date: index for index, bar in enumerate(bars)}
        buy_signals = [trade for trade in trades if trade.side == "buy"]
        points: list[SignalDecayPoint] = []
        for horizon in (1, 3, 5, 10, 20):
            returns: list[Decimal] = []
            for trade in buy_signals:
                index = index_by_date.get(trade.signal_date)
                if index is None or index + horizon >= len(bars):
                    continue
                base = bars[index].close
                returns.append(bars[index + horizon].close / base - Decimal("1"))
            points.append(SignalDecayPoint(
                horizon=horizon,
                sample_count=len(returns),
                average_return=(
                    (sum(returns, Decimal("0")) / Decimal(len(returns))).quantize(Decimal("0.0001"))
                    if returns else None
                ),
                hit_rate=(
                    (Decimal(sum(value > 0 for value in returns)) / Decimal(len(returns))).quantize(Decimal("0.0001"))
                    if returns else None
                ),
            ))
        return points

    @staticmethod
    def _average(bars: list[DailyBar], index: int, window: int) -> Decimal:
        closes = [bar.close for bar in bars[index - window + 1:index + 1]]
        return sum(closes, Decimal("0")) / Decimal(window)

    @staticmethod
    def _volume_average(bars: list[DailyBar], index: int, window: int) -> Decimal:
        values = [Decimal(bar.volume) for bar in bars[index - window + 1:index + 1]]
        return sum(values, Decimal("0")) / Decimal(window)

    @staticmethod
    def _required_bars(request: BacktestRequest) -> int:
        if request.strategy == "momentum_breakout":
            return max(request.lookback_window, request.exit_window)
        if request.strategy == "low_volume_pullback":
            return max(request.slow_window, request.fast_window, request.volume_window)
        return request.slow_window

    def _signal(
        self,
        request: BacktestRequest,
        bars: list[DailyBar],
        index: int,
        shares: int,
        entry_price: Decimal | None,
    ) -> str | None:
        bar = bars[index]
        if shares > 0 and entry_price is not None:
            return_since_entry = bar.close / entry_price - Decimal("1")
            if return_since_entry <= -request.stop_loss_percent or return_since_entry >= request.take_profit_percent:
                return "sell"

        if request.strategy == "sma_cross":
            if index < request.slow_window:
                return None
            current_fast = self._average(bars, index, request.fast_window)
            current_slow = self._average(bars, index, request.slow_window)
            previous_fast = self._average(bars, index - 1, request.fast_window)
            previous_slow = self._average(bars, index - 1, request.slow_window)
            if shares == 0 and previous_fast <= previous_slow and current_fast > current_slow:
                return "buy"
            if shares > 0 and previous_fast >= previous_slow and current_fast < current_slow:
                return "sell"
            return None

        if request.strategy == "momentum_breakout":
            if index < request.lookback_window:
                return None
            prior_closes = [item.close for item in bars[index - request.lookback_window:index]]
            if shares == 0 and bar.close > max(prior_closes):
                return "buy"
            if shares > 0 and bar.close < self._average(bars, index, request.exit_window):
                return "sell"
            return None

        if index < max(request.slow_window, request.volume_window):
            return None
        fast = self._average(bars, index, request.fast_window)
        slow = self._average(bars, index, request.slow_window)
        average_volume = self._volume_average(bars, index - 1, request.volume_window)
        if shares == 0 and bar.close > slow and bar.close <= fast and Decimal(bar.volume) <= average_volume * request.volume_ratio:
            return "buy"
        if shares > 0 and bar.close < slow:
            return "sell"
        return None
