from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.stock_realtime import StockQuotePulse
from qibao_api.dependencies import get_stock_realtime_quote_service
from qibao_api.routes.research import router


class FakePulseService:
    def __init__(self):
        self.watched = []

    async def watch(self, symbol: str) -> None:
        self.watched.append(symbol)

    def snapshot(self, symbol: str) -> StockQuotePulse:
        return StockQuotePulse(
            symbol=symbol,
            name="贵州茅台",
            price=Decimal("1500"),
            previous_close=Decimal("1490"),
            change=Decimal("10"),
            change_percent=Decimal("0.6711"),
            observed_at=datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc),
            fetched_at=datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc),
            status="ready",
            freshness="live",
        )


def test_quote_pulse_registers_symbol_and_returns_memory_snapshot():
    app = FastAPI()
    app.include_router(router)
    service = FakePulseService()
    app.dependency_overrides[get_stock_realtime_quote_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/a-shares/600519/quote-pulse")

    assert response.status_code == 200
    assert service.watched == ["600519"]
    assert response.json()["status"] == "ready"
    assert response.json()["price"] == "1500"
