from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.kronos_forecast import (
    KronosForecastResponse,
)
from qibao_api.dependencies import get_kronos_forecast_service, get_server_time
from qibao_api.routes.first_limit_up import router


NOW = datetime(2026, 7, 24, 8, 10, tzinfo=timezone.utc)


def response() -> KronosForecastResponse:
    return KronosForecastResponse(
        status="unavailable",
        symbol="600000",
        as_of=date(2026, 7, 24),
        observed_through=date(2026, 7, 24),
        model="Kronos-mini",
        lookback_bars=250,
        horizon_bars=0,
        sample_count=0,
        reasons=("kronos_disabled",),
        sources=("local-daily-bars",),
    )


class Service:
    def __init__(self) -> None:
        self.calls = []

    async def forecast(self, symbol, *, as_of, horizon):
        self.calls.append((symbol, as_of, horizon))
        return response().model_copy(update={"symbol": symbol, "as_of": as_of})


def client(service: Service) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_kronos_forecast_service] = lambda: service
    application.dependency_overrides[get_server_time] = lambda: NOW
    return TestClient(application)


def test_quant_forecast_validates_parameters_and_returns_status_payload() -> None:
    service = Service()
    api = client(service)

    result = api.get(
        "/api/v1/a-shares/first-limit-up/quant-forecast"
        "?symbol=600000&as_of=2026-07-24&horizon=10"
    )

    assert result.status_code == 200
    assert result.json()["status"] == "unavailable"
    assert service.calls == [("600000", date(2026, 7, 24), 10)]


def test_quant_forecast_rejects_invalid_symbol_future_date_and_horizon() -> None:
    api = client(Service())

    assert api.get("/api/v1/a-shares/first-limit-up/quant-forecast?symbol=6000").status_code == 422
    assert api.get(
        "/api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&as_of=2026-07-25"
    ).status_code == 422
    assert api.get(
        "/api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&horizon=4"
    ).status_code == 422
    assert api.get(
        "/api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&horizon=21"
    ).status_code == 422
