from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from qibao_api.contracts.backtest import BacktestRequest, BacktestResult
from qibao_api.contracts.bars import DailyBar
from qibao_api.zhongshu.backtest import BacktestEngine


@dataclass(frozen=True, slots=True)
class BacktestMatrixResult:
    results: tuple[BacktestResult, ...]
    reproducibility_hash: str


class BacktestMatrixRunner:
    def run(self, request: BacktestRequest, bars_by_symbol: dict[str, list[DailyBar]]) -> BacktestMatrixResult:
        results = tuple(BacktestEngine().run(request, bars_by_symbol[symbol]) for symbol in sorted(bars_by_symbol))
        payload = {"request": request.model_dump(mode="json"), "symbols": sorted(bars_by_symbol), "results": [item.model_dump(mode="json") for item in results]}
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return BacktestMatrixResult(results, digest)
