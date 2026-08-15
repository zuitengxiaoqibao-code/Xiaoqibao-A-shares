from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.event_impact import EventImpactNotFoundError
from qibao_api.contracts.event_impact import EventImpactReport
from qibao_api.dependencies import get_event_impact_service, get_server_time
from qibao_api.routes.event_impact import router


NOW = datetime(2026, 8, 15, 6, tzinfo=UTC)


class Service:
    def report(self, event_id: str, *, cutoff: datetime) -> EventImpactReport:
        assert event_id == "event-1"
        assert cutoff == NOW
        return EventImpactReport(
            status="unavailable",
            event_id=event_id,
            headline="已核验公告",
            event_type="company_announcement",
            first_published_at=datetime(2026, 8, 14, 2, tzinfo=UTC),
            association_confidence=Decimal("0"),
            association_status="unavailable",
            duplicate_status="unique",
            duplicate_article_count=1,
            limitations=("association_unavailable",),
        )


def app_for(service) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_event_impact_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW
    return TestClient(app)


def test_event_impact_route_returns_the_evidence_contract() -> None:
    response = app_for(Service()).get("/api/v1/news/events/event-1/impact")

    assert response.status_code == 200
    assert response.json()["event_id"] == "event-1"
    assert response.json()["status"] == "unavailable"
    assert response.json()["targets"] == []


def test_event_impact_route_localizes_a_missing_event() -> None:
    class Missing:
        def report(self, event_id: str, *, cutoff: datetime):
            raise EventImpactNotFoundError(event_id)

    response = app_for(Missing()).get("/api/v1/news/events/missing/impact")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "news_event_not_found",
        "message": "未找到该新闻事件",
    }
