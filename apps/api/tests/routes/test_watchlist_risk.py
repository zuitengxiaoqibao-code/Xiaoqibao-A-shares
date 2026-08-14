from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.watchlist_risk import WatchlistRiskResponse
from qibao_api.dependencies import get_server_time, get_watchlist_risk_service
from qibao_api.routes.watchlist_risk import router


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


class Service:
    def analyze(self, symbols, *, as_of, observed_at):
        return WatchlistRiskResponse(
            status="unavailable",
            as_of=as_of,
            observed_at=observed_at,
            valid_count=0,
            total_count=len(symbols),
            coverage_percent=Decimal(0),
            items=tuple({
                "symbol": symbol, "name": symbol, "return_sample_count": 0,
                "status": "unavailable", "limitations": ("真实日线不足",),
            } for symbol in symbols),
            warnings=("部分标的缺少足够真实日线或身份数据",),
        )


def test_watchlist_risk_route_keeps_unavailable_state_honest() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_watchlist_risk_service] = lambda: Service()
    app.dependency_overrides[get_server_time] = lambda: NOW
    client = TestClient(app)

    response = client.post(
        "/api/v1/a-shares/watchlist-risk",
        json={"symbols": ["600000"], "as_of": "2026-08-14"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "observation_basket"
    assert response.json()["status"] == "unavailable"
    assert response.json()["items"][0]["limitations"] == ["真实日线不足"]
