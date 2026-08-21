from datetime import date, timedelta

from qibao_api.contracts.backtest import BacktestRequest
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.backtest_matrix import BacktestMatrixRunner


def _bars(symbol="600519"):
    start = date(2026, 1, 1)
    return [DailyBar(symbol=symbol, trade_date=start + timedelta(days=i), open=100+i, high=101+i, low=99+i, close=100+i, volume=1000, amount=100000, source="test") for i in range(44)]


def test_matrix_runner_returns_reproducibility_hash_and_results():
    result = BacktestMatrixRunner().run(BacktestRequest(), {"600519": _bars()})
    assert len(result.results) == 1
    assert len(result.reproducibility_hash) == 64
