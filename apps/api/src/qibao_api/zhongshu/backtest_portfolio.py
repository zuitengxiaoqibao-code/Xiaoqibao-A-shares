from __future__ import annotations

from dataclasses import dataclass

from qibao_api.contracts.backtest import BacktestRequest, BacktestResult
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.backtest import BacktestEngine


@dataclass(frozen=True, slots=True)
class PortfolioBacktestResult:
    symbols: tuple[str, ...]
    results: tuple[BacktestResult, ...]
    max_positions: int


class PortfolioBacktestRunner:
    def __init__(self, *, max_positions: int = 5) -> None:
        if max_positions < 1:
            raise ValueError("最大持仓数必须大于0")
        self.max_positions = max_positions

    def run(self, request: BacktestRequest, bars_by_symbol: dict[str, list[DailyBar]]) -> PortfolioBacktestResult:
        symbols = tuple(sorted(bars_by_symbol))
        selected = symbols[: self.max_positions]
        results = tuple(BacktestEngine().run(request, bars_by_symbol[symbol]) for symbol in selected)
        return PortfolioBacktestResult(symbols, results, self.max_positions)
