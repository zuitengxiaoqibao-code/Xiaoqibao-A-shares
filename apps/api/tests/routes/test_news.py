from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.news import (
    AIInterpretation,
    EvidenceCitation,
    InterpretationStatement,
    NormalizedNewsEvent,
)
from qibao_api.dependencies import (
    get_decision_calendar,
    get_hotspot_service,
    get_news_alert_service,
    get_news_repository,
    get_news_service,
    get_realtime_snapshot_bus,
    get_server_time,
    get_shared_snapshot_registry,
)
from qibao_api.contracts.news_alerts import (
    BreakingNewsAlert,
    BreakingNewsAlertResponse,
)
from qibao_api.routes.news import router
from qibao_api.libu_compliance.repository import SourceAuthorizationError


NOW = datetime(2026, 7, 14, 1, 0, tzinfo=UTC)


class Service:
    synced_symbols = []

    async def sync(self):
        return {"fetched": 3, "inserted": 2, "clusters": 2, "events": 2}

    async def sync_symbol(self, symbol):
        self.synced_symbols.append(symbol)
        return {"fetched": 1, "inserted": 1, "clusters": 1, "events": 1}


class Repository:
    saved_corrections = []

    def articles(self):
        return [object()]

    def clusters(self):
        return [{"cluster": object()}]

    def events(self):
        return [NormalizedNewsEvent(
            event_id="event-news-1", event_type="market_news", headline="政策发布",
            occurred_at=NOW, normalized_at=NOW, affected_instruments=(),
            industries=(), themes=("政策支持",),
            citations=(EvidenceCitation(
                citation_id="citation-news-1", article_id="news-1",
                canonical_url="https://news.example/1", publisher="测试来源",
                published_at=NOW, quoted_text="政策发布", content_hash="a" * 64,
            ),),
            association_confidence=Decimal("0.60"), review_state="pending",
        )]

    def interpretations(self):
        citation = self.events()[0].citations[0]
        return [AIInterpretation(
            interpretation_id="interpretation-1", event_id="event-news-1",
            generated_at=NOW, provider="deterministic", model="evidence-summary-v1",
            prompt_version="news-v1", latency_ms=2, degraded=True,
            statements=(InterpretationStatement(
                statement_id="s1", kind="fact", text="政策发布",
                citation_ids=(citation.citation_id,),
            ),), citations=(citation,),
        )]

    def effective_events(self, *, cutoff=None):
        return self.events()

    def latest_interpretations_by_event(self, event_ids, cutoff):
        return {item.event_id: item for item in self.interpretations() if item.event_id in event_ids}

    def append_correction(self, correction):
        self.saved_corrections.append(correction)
        return True

    def corrections(self):
        return list(self.saved_corrections)


class AlertService:
    calls = []

    def current(self, cutoff, *, symbol=None, limit=30):
        self.calls.append((cutoff, symbol, limit))
        return BreakingNewsAlertResponse(
            status="ready",
            observed_at=cutoff,
            alerts=(BreakingNewsAlert(
                event_id="event-alert-1",
                headline="公司发布经核验的重要公告",
                occurred_at=NOW,
                verification_state="multi_source_confirmed",
                urgency="breaking",
                association_kind="direct",
                association_reasons=("company_alias:贵州茅台",),
                affected_symbols=("600519",),
                themes=("白酒",),
                publishers=("上交所", "证券时报"),
                source_urls=(
                    "https://news.example/official",
                    "https://news.example/media",
                ),
                source_count=2,
                impact_direction="uncertain",
                impact_confidence=None,
                ai_degraded=True,
            ),),
            sources=("上交所", "证券时报"),
        )


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_news_service] = lambda: Service()
    app.dependency_overrides[get_news_repository] = lambda: Repository()
    app.dependency_overrides[get_news_alert_service] = lambda: AlertService()
    app.dependency_overrides[get_server_time] = lambda: NOW
    return TestClient(app)


def test_alert_route_filters_by_symbol_and_uses_server_cutoff() -> None:
    AlertService.calls = []

    with client() as test_client:
        response = test_client.get("/api/v1/news/alerts?symbol=600519&limit=10")

    assert response.status_code == 200
    assert all(
        "600519" in item["affected_symbols"]
        for item in response.json()["alerts"]
    )
    assert AlertService.calls == [(NOW, "600519", 10)]


def test_alert_route_rejects_invalid_symbol_and_limit() -> None:
    with client() as test_client:
        bad_symbol = test_client.get("/api/v1/news/alerts?symbol=519&limit=10")
        bad_limit = test_client.get("/api/v1/news/alerts?limit=101")

    assert bad_symbol.status_code == 422
    assert bad_limit.status_code == 422


def test_news_sync_and_event_routes_expose_auditable_results() -> None:
    with client() as test_client:
        synced = test_client.post("/api/v1/news/sync")
        events = test_client.get("/api/v1/news/events")
        interpretations = test_client.get("/api/v1/news/interpretations")

    assert synced.status_code == 200
    assert synced.json()["inserted"] == 2
    assert events.status_code == 200
    assert events.json()[0]["citations"][0]["article_id"] == "news-1"
    assert interpretations.status_code == 200
    assert interpretations.json()[0]["degraded"] is True


def test_news_event_read_registers_repository_snapshot_reuse() -> None:
    calls = []

    class Registry:
        def record(self, kind, **payload):
            calls.append((kind, payload))

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_news_repository] = lambda: Repository()
    app.dependency_overrides[get_shared_snapshot_registry] = lambda: Registry()
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/news/events")

    assert response.status_code == 200
    assert calls[0][0] == "news_events"
    assert calls[0][1]["reused"] is True
    assert calls[0][1]["trade_date"] == NOW.date()
    assert len(calls[0][1]["content_hash"]) == 64


def test_news_event_read_publishes_only_changed_verified_snapshot() -> None:
    calls = []

    class VerifiedRepository(Repository):
        def events(self):
            return [self._event("verified", "verified-event"), self._event("pending", "pending-event")]

        @staticmethod
        def _event(review_state, event_id):
            return NormalizedNewsEvent(
                event_id=event_id, event_type="market_news", headline=event_id,
                occurred_at=NOW, normalized_at=NOW, affected_instruments=(),
                industries=(), themes=(), citations=(EvidenceCitation(
                    citation_id=f"citation-{event_id}", article_id=f"article-{event_id}",
                    canonical_url="https://news.example/event", publisher="测试来源",
                    published_at=NOW, quoted_text=event_id, content_hash="c" * 64,
                ),), association_confidence=Decimal("0.80"),
                review_state=review_state,
            )

    class Bus:
        def __init__(self):
            self.latest_event = None

        def latest(self, kind):
            return self.latest_event if kind == "news_events" else None

        def publish(self, kind, payload, **kwargs):
            self.latest_event = {"payload": payload}
            calls.append((kind, payload, kwargs))

    bus = Bus()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_news_repository] = lambda: VerifiedRepository()
    app.dependency_overrides[get_realtime_snapshot_bus] = lambda: bus
    with TestClient(app) as test_client:
        first = test_client.get("/api/v1/news/events")
        second = test_client.get("/api/v1/news/events")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == "news_events"
    assert calls[0][1]["verified_count"] == 1
    assert [item["event_id"] for item in calls[0][1]["events"]] == ["verified-event"]
    assert calls[0][2]["source"] == "news-repository"


def test_unified_event_route_reuses_real_event_ids_and_keeps_unknown_effects_explicit() -> None:
    with client() as test_client:
        response = test_client.get("/api/v1/news/unified-events")

    assert response.status_code == 200
    projected = response.json()[0]
    assert projected["event_id"] == "event-news-1"
    assert projected["category"] == "rumor_unverified"
    assert projected["direction"] == "uncertain"
    assert projected["duration"] == "unknown"
    assert projected["price_reflection"] == "unknown"


def test_news_sync_for_selected_a_share_delegates_to_symbol_source() -> None:
    Service.synced_symbols = []

    with client() as test_client:
        synced = test_client.post("/api/v1/news/sync/600519")

    assert synced.status_code == 200
    assert synced.json()["inserted"] == 1
    assert Service.synced_symbols == ["600519"]


def test_news_sync_rejects_invalid_a_share_symbol() -> None:
    Service.synced_symbols = []

    with client() as test_client:
        synced = test_client.post("/api/v1/news/sync/123")

    assert synced.status_code == 422
    assert Service.synced_symbols == []


def test_news_sync_maps_missing_authorization_to_clear_403() -> None:
    class Unauthorized:
        async def sync(self):
            raise SourceAuthorizationError("eastmoney")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_news_service] = lambda: Unauthorized()

    response = TestClient(app).post("/api/v1/news/sync")

    assert response.status_code == 403
    assert response.json()["detail"] == "A 股新闻数据源尚未授权：eastmoney"


def test_hotspot_sync_defaults_to_china_date_and_accepts_explicit_trading_date() -> None:
    class HotspotService:
        calls = []

        def sync(self, trading_date, *, fetched_at):
            self.calls.append((trading_date, fetched_at))
            return {"fetched": 2, "inserted": 2, "clusters": 2, "events": 2}

    class Calendar:
        def is_trading_day(self, value):
            return value in {date(2026, 7, 16), date(2026, 7, 17)}

    service = HotspotService()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_hotspot_service] = lambda: service
    app.dependency_overrides[get_decision_calendar] = lambda: Calendar()
    app.dependency_overrides[get_server_time] = lambda: datetime(
        2026, 7, 16, 23, 30, tzinfo=UTC
    )

    with TestClient(app) as test_client:
        defaulted = test_client.post("/api/v1/news/hotspots/sync")
        explicit = test_client.post(
            "/api/v1/news/hotspots/sync?trading_date=2026-07-16"
        )

    assert defaulted.status_code == 200
    assert explicit.status_code == 200
    assert [call[0] for call in service.calls] == [
        date(2026, 7, 17),
        date(2026, 7, 16),
    ]
    assert all(call[1].tzinfo is not None for call in service.calls)


def test_hotspot_sync_validates_dates_and_isolates_authorization_and_upstream_errors() -> None:
    class Calendar:
        def is_trading_day(self, value):
            return value == date(2026, 7, 17)

    class FailingService:
        error = SourceAuthorizationError("tonghuashun")

        def sync(self, trading_date, *, fetched_at):
            raise self.error

    service = FailingService()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_hotspot_service] = lambda: service
    app.dependency_overrides[get_decision_calendar] = lambda: Calendar()
    app.dependency_overrides[get_server_time] = lambda: datetime(
        2026, 7, 17, 2, 0, tzinfo=UTC
    )

    with TestClient(app) as test_client:
        future = test_client.post(
            "/api/v1/news/hotspots/sync?trading_date=2026-07-18"
        )
        closed = test_client.post(
            "/api/v1/news/hotspots/sync?trading_date=2026-07-16"
        )
        unauthorized = test_client.post("/api/v1/news/hotspots/sync")
        service.error = OSError("offline")
        unavailable = test_client.post("/api/v1/news/hotspots/sync")

    assert future.status_code == 422
    assert future.json()["detail"]["code"] == "future_trading_date"
    assert closed.status_code == 422
    assert closed.json()["detail"]["code"] == "not_trading_day"
    assert unauthorized.status_code == 403
    assert "tonghuashun" in unauthorized.json()["detail"]
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "hotspot_upstream_unavailable"


def test_news_quality_and_human_correction_routes() -> None:
    Repository.saved_corrections = []
    with client() as test_client:
        corrected = test_client.post("/api/v1/news/corrections", json={
            "event_id": "event-news-1", "reason": "人工确认事件分类",
            "review_state": "verified", "industries": ["高端制造"],
        })
        quality = test_client.get("/api/v1/news/quality")

    assert corrected.status_code == 200
    assert corrected.json()["correction_id"].startswith("correction-")
    assert quality.status_code == 200
    assert quality.json()["human_correction_rate"] == "1.0000"
