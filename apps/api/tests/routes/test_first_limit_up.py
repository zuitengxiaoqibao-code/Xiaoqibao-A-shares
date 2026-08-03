from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.first_limit_up import FirstLimitUpBoard
from qibao_api.dependencies import get_first_limit_up_service, get_server_time
from qibao_api.routes.first_limit_up import router


NOW = datetime(2026, 7, 24, 8, 10, tzinfo=timezone.utc)


def board() -> FirstLimitUpBoard:
    return FirstLimitUpBoard(
        status="empty",
        as_of=date(2026, 7, 24),
        scanned_count=0,
        qualified_count=0,
        pullback_window_count=0,
        no_buy_count=0,
    )


class Service:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = []

    def current(self, as_of):
        self.calls.append(("current", as_of))
        return board()

    async def refresh(self, as_of):
        self.calls.append(("refresh", as_of))
        if self.fail:
            raise OSError("source unavailable with secret detail")
        return board()


def client(service: Service) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_first_limit_up_service] = lambda: service
    application.dependency_overrides[get_server_time] = lambda: NOW
    return TestClient(application)


def test_current_and_refresh_use_beijing_trading_date() -> None:
    service = Service()
    api = client(service)

    current = api.get("/api/v1/a-shares/first-limit-up")
    refreshed = api.post("/api/v1/a-shares/first-limit-up/refresh")

    assert current.status_code == 200
    assert refreshed.status_code == 200
    assert refreshed.json()["rule_version"] == "first-limit-up-v1"
    assert service.calls == [
        ("current", date(2026, 7, 24)),
        ("refresh", date(2026, 7, 24)),
    ]


def test_refresh_maps_source_failure_to_safe_error() -> None:
    response = client(Service(fail=True)).post(
        "/api/v1/a-shares/first-limit-up/refresh"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "first_limit_up_unavailable"
    assert "secret" not in response.text
