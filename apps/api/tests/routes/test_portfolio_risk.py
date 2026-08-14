from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.portfolio_risk import PortfolioRiskResponse
from qibao_api.dependencies import (
    get_portfolio_risk_service,
    get_portfolio_risk_store,
    get_quant_strategy_service,
    get_server_time,
)
from qibao_api.routes.portfolio_risk import router


NOW = datetime(2026, 8, 11, 8, tzinfo=timezone.utc)


def test_portfolio_risk_route_uses_current_market_regime_without_running_orders() -> None:
    class PortfolioService:
        def analyze(self, positions, *, as_of, market_regime):
            assert positions[0].symbol == "600519"
            assert as_of == date(2026, 8, 11)
            assert market_regime == "轮动震荡"
            return PortfolioRiskResponse(
                status="ready", as_of=as_of, observed_at=NOW,
                total_market_value=Decimal("1000"), market_regime=market_regime,
            )

    class QuantService:
        def current(self, now, *, as_of, limit):
            assert limit == 1
            return type("Dashboard", (), {"regime": type("Regime", (), {"regime": "轮动震荡"})()})()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_portfolio_risk_service] = lambda: PortfolioService()
    app.dependency_overrides[get_quant_strategy_service] = lambda: QuantService()
    app.dependency_overrides[get_server_time] = lambda: NOW

    response = TestClient(app).post("/api/v1/a-shares/portfolio-risk", json={
        "positions": [{"symbol": "600519", "shares": "100", "cost_price": "10"}],
        "as_of": "2026-08-11",
    })

    assert response.status_code == 200
    assert response.json()["market_regime"] == "轮动震荡"
    assert response.json()["total_market_value"] == "1000"


def test_portfolio_risk_routes_persist_load_and_delete_positions() -> None:
    class Store:
        def __init__(self):
            self.positions = {}

        def current(self):
            return tuple(self.positions[key] for key in sorted(self.positions))

        def upsert(self, position):
            self.positions[position.symbol] = position
            return position

        def delete(self, symbol):
            return self.positions.pop(symbol, None) is not None

    class PortfolioService:
        def analyze(self, positions, *, as_of, market_regime):
            return PortfolioRiskResponse(
                status="partial" if positions else "unavailable",
                as_of=as_of,
                observed_at=NOW,
                positions=tuple(
                    {
                        "symbol": item.symbol,
                        "shares": item.shares,
                        "cost_price": item.cost_price,
                        "status": "unavailable",
                    }
                    for item in positions
                ),
                warnings=() if positions else ("尚未录入持仓",),
            )

    class QuantService:
        def current(self, now, *, as_of, limit):
            raise OSError("market regime unavailable")

    store = Store()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_portfolio_risk_store] = lambda: store
    app.dependency_overrides[get_portfolio_risk_service] = lambda: PortfolioService()
    app.dependency_overrides[get_quant_strategy_service] = lambda: QuantService()
    app.dependency_overrides[get_server_time] = lambda: NOW
    client = TestClient(app)

    empty = client.get("/api/v1/a-shares/portfolio-risk")
    assert empty.status_code == 200
    assert empty.json()["status"] == "unavailable"

    saved = client.put("/api/v1/a-shares/portfolio-risk/positions/600519", json={
        "shares": "100",
        "cost_price": "1500",
    })
    assert saved.status_code == 200
    assert saved.json()["positions"][0]["symbol"] == "600519"

    loaded = client.get("/api/v1/a-shares/portfolio-risk")
    assert loaded.json()["positions"][0]["shares"] == "100"

    removed = client.delete("/api/v1/a-shares/portfolio-risk/positions/600519")
    assert removed.status_code == 200
    assert removed.json()["positions"] == []
