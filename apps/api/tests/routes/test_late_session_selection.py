from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_late_session_selection_service, get_server_time
from qibao_api.contracts.late_session_selection import LateSessionRuleSettings, LateSessionSelectionResponse
from qibao_api.routes.late_session_selection import router


NOW = datetime(2026, 8, 17, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


class Service:
    def __init__(self):
        self.calls = []

    def current(self, now, *, limit, settings=None):
        self.calls.append((now, limit, settings))
        return LateSessionSelectionResponse(
                status="partial", trading_date="2026-08-17", server_time=NOW,
                phase="live_monitor", refresh_interval_ms=1000, next_refresh_ms=1000,
                source_quality="partial", universe_count=1, quote_count=1, candidate_count=0,
                rules=[], candidates=[], behaviors=[], source_evidence=["通达信本地全市场实时快照"], limitations=["分时黄线不可用"],
        )


def test_late_session_route_exposes_phase_and_real_refresh_interval():
    service = Service()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_late_session_selection_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW

    response = TestClient(app).get("/api/v1/a-shares/late-session-selection?limit=20")

    assert response.status_code == 200
    assert response.json()["phase"] == "live_monitor"
    assert response.json()["refresh_interval_ms"] == 1000
    assert service.calls == [(NOW, 20, None)]


def test_late_session_filter_route_accepts_custom_settings():
    service = Service()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_late_session_selection_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW
    settings = LateSessionRuleSettings(change_min=1, change_max=2, intraday_relation="any")

    response = TestClient(app).post(
        "/api/v1/a-shares/late-session-selection/filter?limit=20",
        json=settings.model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert service.calls[0][0:2] == (NOW, 20)
    assert service.calls[0][2].change_min == 1
