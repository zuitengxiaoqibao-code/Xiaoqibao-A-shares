from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.market_overview import (
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
)
from qibao_api.contracts.quant_strategy import QuantStrategyDashboard
from qibao_api.contracts.quant_shadow import (
    QuantShadowAnalytics,
    ShadowDecisionRecord,
    StrategyDriftAssessment,
)
from qibao_api.dependencies import get_decision_journal, get_quant_shadow_ledger, get_quant_strategy_service, get_server_time
from qibao_api.routes.quant_strategy import router


NOW = datetime(2026, 7, 31, 6, 0, tzinfo=timezone.utc)


class Service:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def current(self, now, *, as_of=None, limit=12):
        self.calls.append((now, as_of, limit))
        if self.fail:
            raise OSError("local market unavailable")
        return QuantStrategyDashboard(
            status="partial",
            as_of=date(2026, 7, 31),
            observed_at=NOW,
            generated_at=NOW,
            market_observed_at=NOW,
            data_age_seconds=0,
            refresh_mode="live",
            next_refresh_at=NOW,
            metrics=OverviewRegimeMetrics(up_ratio=Decimal("55")),
            regime=OverviewRegimeAssessment(
                regime="轮动震荡",
                emotion_score=Decimal("55"),
                risk_score=Decimal("30"),
                heat_score=Decimal("50"),
                rotation_score=Decimal("62"),
                coverage_percent=Decimal("80"),
                market_coef=Decimal("0.5"),
                suitable_strategies=("0轴低吸模型",),
                avoid_strategies=("高开追涨",),
                reasons=("轮动分达到阈值",),
                missing_factors=("net_positive_ratio",),
                quality="partial",
            ),
            candidates=(),
            discipline="轮动震荡：只做前排低吸。",
            missing_data=("net_positive_ratio",),
            sources=("tdx-local-realtime",),
        )


def application(service: Service, ledger=None, journal=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_quant_strategy_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW
    if ledger is not None:
        app.dependency_overrides[get_quant_shadow_ledger] = lambda: ledger
    if journal is not None:
        app.dependency_overrides[get_decision_journal] = lambda: journal
    return app


def test_quant_strategy_route_returns_honest_partial_dashboard() -> None:
    service = Service()

    response = TestClient(application(service)).get(
        "/api/v1/a-shares/quant-strategy?limit=8&as_of=2026-07-30"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["regime"]["regime"] == "轮动震荡"
    assert response.json()["refresh_mode"] == "live"
    assert response.json()["data_age_seconds"] == 0
    assert response.json()["candidate_scan_cached"] is False
    assert response.json()["candidate_scan_age_seconds"] is None
    assert response.json()["trigger_evidence_at"] is None
    assert service.calls == [(NOW, date(2026, 7, 30), 8)]


def test_quant_strategy_route_translates_source_failure() -> None:
    response = TestClient(application(Service(fail=True))).get(
        "/api/v1/a-shares/quant-strategy"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "quant_strategy_unavailable"


def test_quant_shadow_route_returns_frozen_decisions() -> None:
    record = ShadowDecisionRecord(
        decision_id="shadow-1", as_of=date(2026, 7, 31), symbol="600519",
        formula_version="a-share-short-strategy-v2.0", candidate_status="watch",
        strategy_score=Decimal("76.5"), reference_price=Decimal("1500"), frozen_at=NOW,
        outcomes=(),
    )

    class Ledger:
        def recent(self, *, limit):
            assert limit == 10
            return (record,)

    response = TestClient(application(Service(), Ledger())).get(
        "/api/v1/a-shares/quant-strategy/shadow?limit=10"
    )

    assert response.status_code == 200
    assert response.json()[0]["decision_id"] == "shadow-1"
    assert response.json()[0]["reference_price"] == "1500"


def test_quant_shadow_analytics_route_returns_calibration_and_drift() -> None:
    analytics = QuantShadowAnalytics(
        status="insufficient",
        horizon=5,
        mature_sample_count=7,
        pending_sample_count=3,
        drift=StrategyDriftAssessment(
            status="insufficient",
            recent_sample_count=7,
            baseline_sample_count=0,
            reasons=("样本不足",),
        ),
        generated_at=NOW,
        limitations=("成熟样本不足",),
    )

    class Ledger:
        def analytics(self, *, horizon, decision_source=None, opportunity_type=None):
            assert horizon == 5
            assert decision_source is None
            assert opportunity_type is None
            return analytics

    response = TestClient(application(Service(), Ledger())).get(
        "/api/v1/a-shares/quant-strategy/shadow/analytics?horizon=5"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"
    assert response.json()["mature_sample_count"] == 7
    assert response.json()["drift"]["status"] == "insufficient"


def test_quant_shadow_analytics_route_accepts_sixty_day_cohort_filters() -> None:
    analytics = QuantShadowAnalytics(
        status="insufficient",
        horizon=60,
        decision_source="opportunity_scan",
        opportunity_type="trend_continuation",
        mature_sample_count=0,
        pending_sample_count=4,
        drift=StrategyDriftAssessment(
            status="insufficient",
            recent_sample_count=0,
            baseline_sample_count=0,
        ),
        generated_at=NOW,
    )

    class Ledger:
        def analytics(self, *, horizon, decision_source=None, opportunity_type=None):
            assert horizon == 60
            assert decision_source == "opportunity_scan"
            assert opportunity_type == "trend_continuation"
            return analytics

    response = TestClient(application(Service(), Ledger())).get(
        "/api/v1/a-shares/quant-strategy/shadow/analytics"
        "?horizon=60&decision_source=opportunity_scan&opportunity_type=trend_continuation"
    )

    assert response.status_code == 200
    assert response.json()["horizon"] == 60
    assert response.json()["decision_source"] == "opportunity_scan"


def test_decision_journal_routes_append_and_list_manual_records() -> None:
    from qibao_api.contracts.decision_journal import DecisionJournalEntry

    entry = DecisionJournalEntry(
        entry_id="journal-1", decision_id="shadow-1", symbol="600519",
        action="observe", recorded_at=NOW, note="等待触发", created_at=NOW,
    )

    class Journal:
        def append(self, request):
            assert request.symbol == "600519"
            assert request.action == "observe"
            return entry

        def recent(self, *, limit):
            assert limit == 20
            return (entry,)

    client = TestClient(application(Service(), journal=Journal()))
    created = client.post("/api/v1/a-shares/quant-strategy/journal", json={
        "decision_id": "shadow-1",
        "symbol": "600519",
        "action": "observe",
        "recorded_at": NOW.isoformat(),
        "note": "等待触发",
    })
    listed = client.get("/api/v1/a-shares/quant-strategy/journal?limit=20")

    assert created.status_code == 201
    assert created.json()["entry_id"] == "journal-1"
    assert listed.status_code == 200
    assert listed.json()[0]["note"] == "等待触发"
