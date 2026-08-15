from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.bars import DailyBar
from qibao_api.dependencies import get_market_data_service
from qibao_api.routes.walk_forward import router


def bars(count: int) -> list[DailyBar]:
    result = []
    for index in range(count):
        close = Decimal("10") + Decimal(index % 5)
        result.append(DailyBar(
            symbol="600519", trade_date=date(2025, 1, 1) + timedelta(days=index),
            open=close, high=close + Decimal("0.1"), low=close - Decimal("0.1"),
            close=close, volume=100000, amount=Decimal("1000000"), source="local-tdx",
        ))
    return result


class Repository:
    def latest(self, symbol, limit):
        assert symbol == "600519"
        assert limit == 2000
        return bars(160)


def test_walk_forward_route_uses_local_history_and_returns_evidence_status():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_market_data_service] = lambda: type(
        "Service", (), {"repository": Repository()}
    )()
    client = TestClient(app)

    response = client.post("/api/v1/a-shares/600519/walk-forward", json={
        "backtest": {"fast_window": 2, "slow_window": 3},
        "train_bars": 64,
        "validation_bars": 32,
        "test_bars": 32,
        "step_bars": 32,
    })

    assert response.status_code == 200
    assert response.json()["source"] == "local-tdx"
    assert response.json()["parameter_policy"] == "frozen_before_validation"
