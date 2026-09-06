from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.overseas_market import OverseasMarketSnapshot
from qibao_api.dependencies import get_overseas_market_service
from qibao_api.routes.overseas_market import router


class StubService:
    async def current(self):
        return OverseasMarketSnapshot(
            indices=(),
            mag7=(),
            observed_at=datetime.now(timezone.utc),
            source="test",
            trading_label="美股 2026-09-02 最近收盘",
            quality="unavailable",
            reason="测试无数据",
        )


def test_overseas_market_route_returns_snapshot() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_overseas_market_service] = lambda: StubService()

    with TestClient(app) as client:
        response = client.get("/api/v1/market/overseas")

    assert response.status_code == 200
    assert response.json()["quality"] == "unavailable"
    assert response.json()["reason"] == "测试无数据"
