from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewBreadth,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewSentiment,
)
from qibao_api.contracts.market_review import MarketIntervalReviewSnapshot
from qibao_api.dependencies import (
    get_local_market_review_source,
    get_market_overview_service,
    get_server_time,
)
from qibao_api.routes.market_overview import router


NOW = datetime(2026, 7, 29, 2, 30, tzinfo=timezone.utc)


def overview() -> MarketOverviewResponse:
    return MarketOverviewResponse(
        status="partial", as_of=date(2026, 7, 29), observed_at=NOW,
        sentiment=OverviewSentiment(
            score=None, band="unavailable", coverage_percent=0,
            quality="unavailable", observed_at=NOW,
        ),
        breadth=OverviewBreadth(
            rising_count=0, falling_count=0, flat_count=0, valid_count=0,
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=0, limit_down_count=0, broken_limit_up_count=0,
        ),
        liquidity=OverviewLiquidity(), warnings=("index_quotes_unavailable",),
    )


class Service:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = []

    def current(self, now):
        self.calls.append(now)
        if self.error:
            raise self.error
        return overview()


class IntervalSource:
    def interval(self, *, start_date, end_date):
        return MarketIntervalReviewSnapshot(
            requested_start_date=start_date,
            requested_end_date=end_date,
            start_date=start_date,
            end_date=end_date,
            observed_at=NOW,
            source="tdx-local-day",
            quality="partial",
            universe_count=1,
            valid_count=1,
        )


def client(service: Service) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_market_overview_service] = lambda: service
    application.dependency_overrides[get_local_market_review_source] = IntervalSource
    application.dependency_overrides[get_server_time] = lambda: NOW
    return TestClient(application)


def test_market_overview_route_returns_bounded_snapshot() -> None:
    service = Service()
    response = client(service).get("/api/v1/a-shares/market-overview")

    assert response.status_code == 200
    assert response.json()["as_of"] == "2026-07-29"
    assert response.json()["live_feed"] == []
    assert service.calls == [NOW]


def test_market_overview_route_hides_internal_source_errors() -> None:
    response = client(Service(OSError("https://secret.invalid/token"))).get(
        "/api/v1/a-shares/market-overview"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "market_overview_unavailable"
    assert "secret.invalid" not in response.text


def test_interval_review_route_returns_real_date_window() -> None:
    response = client(Service()).get(
        "/api/v1/a-shares/market-overview/interval"
        "?start_date=2026-07-01&end_date=2026-07-29"
    )

    assert response.status_code == 200
    assert response.json()["formula_version"] == "a-share-interval-review-v1"
