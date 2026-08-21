from datetime import date, timedelta

from qibao_api.contracts.backtest import BacktestRequest
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.backtest_portfolio import PortfolioBacktestRunner


def test_portfolio_runner_enforces_position_limit():
    start = date(2026, 1, 1)
    bars = {symbol: [DailyBar(symbol=symbol, trade_date=start + timedelta(days=i), open=100, high=101, low=99, close=100, volume=1000, amount=100000, source="test") for i in range(44)] for symbol in ("600519", "000001")}
    result = PortfolioBacktestRunner(max_positions=1).run(BacktestRequest(), bars)
    assert result.max_positions == 1
    assert result.symbols == ("000001", "600519")
