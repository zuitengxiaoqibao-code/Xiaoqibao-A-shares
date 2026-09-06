from datetime import date, datetime, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.market_sentiment import (
    MarketSentimentNotTradingDay,
    MarketSentimentResponse,
    MarketSentimentWrongPhase,
)
from qibao_api.contracts.market_sentiment import MarketSentimentSnapshot
from qibao_api.dependencies import get_market_sentiment_service, get_server_time
from qibao_api.gongbu.tencent_market_sentiment import (
    MarketSentimentSourceUnavailable,
)
from qibao_api.libu_compliance.repository import SourceAuthorizationError
from qibao_api.routes.market_sentiment import router


NOW = datetime(2026, 7, 18, 2, 30, tzinfo=timezone.utc)


def snapshot() -> MarketSentimentSnapshot:
    return MarketSentimentSnapshot(
        snapshot_id="sentiment-route-fixture",
        trading_date=date(2026, 7, 18),
        phase="intraday",
        quality="partial",
        freshness="current",
        score=Decimal("64.50"),
        band="active",
        coverage_percent=Decimal("80"),
        components=(),
        drivers=("breadth",),
        risks=("partial coverage",),
        beginner_guidance="Observe confirmation.",
        observed_at=NOW,
        generated_at=NOW,
        source_snapshot_ids=("source-1",),
        formula_version="a-share-sentiment-v1",
    )


class Service:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = []
        self.thread_names = []

    def current(self, now):
        self.thread_names.append(threading.current_thread().name)
        self.calls.append(("current", now))
        if self.error:
            raise self.error
        item = snapshot()
        return MarketSentimentResponse(
            trading_date=item.trading_date,
            phase="intraday",
            display_mode="current",
            current=item,
            previous_close=None,
            trajectory=(item,),
        )

    def history(self, trading_date):
        self.calls.append(("history", trading_date))
        if self.error:
            raise self.error
        return (snapshot(),)

    def refresh(self, now):
        self.calls.append(("refresh", now))
        if self.error:
            raise self.error
        return snapshot()


def client(service: Service, *, read_executor=None) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_market_sentiment_service] = lambda: service
    application.dependency_overrides[get_server_time] = lambda: NOW
    if read_executor is not None:
        application.state.read_executor = read_executor
    return TestClient(application)


def test_current_uses_the_latency_critical_read_executor() -> None:
    service = Service()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="latency-critical-read") as executor:
        response = client(service, read_executor=executor).get(
            "/api/v1/a-shares/market-sentiment/current"
        )

    assert response.status_code == 200
    assert service.thread_names == ["latency-critical-read_0"]


def test_current_history_and_refresh_return_frozen_sentiment() -> None:
    service = Service()
    api = client(service)

    current = api.get("/api/v1/a-shares/market-sentiment/current")
    history = api.get("/api/v1/a-shares/market-sentiment/2026-07-18")
    refresh = api.post("/api/v1/a-shares/market-sentiment/refresh")

    assert current.status_code == 200
    assert current.json()["current"]["snapshot_id"] == "sentiment-route-fixture"
    assert history.status_code == 200
    assert history.json()["trajectory"][0]["formula_version"] == (
        "a-share-sentiment-v1"
    )
    assert refresh.status_code == 200
    assert service.calls == [
        ("current", NOW),
        ("history", date(2026, 7, 18)),
        ("refresh", NOW),
    ]


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (
            MarketSentimentWrongPhase("internal phase"),
            409,
            "market_sentiment_wrong_phase",
        ),
        (
            MarketSentimentNotTradingDay("internal calendar"),
            409,
            "market_sentiment_not_trading_day",
        ),
        (
            SourceAuthorizationError("tencent:missing secret"),
            403,
            "market_sentiment_source_not_authorized",
        ),
        (
            MarketSentimentSourceUnavailable(
                "https://qt.gtimg.cn/q=sh600000?token=secret"
            ),
            503,
            "market_sentiment_unavailable",
        ),
    ],
)
def test_refresh_maps_failures_to_safe_beginner_errors(
    error, expected_status, expected_code
) -> None:
    response = client(Service(error)).post(
        "/api/v1/a-shares/market-sentiment/refresh"
    )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    assert "qt.gtimg" not in response.text
    assert "secret" not in response.text
