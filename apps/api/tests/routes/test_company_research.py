import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    CompanyResearchDimension,
    CompanyResearchResponse,
    CounterCaseItem,
    FinancialHistory,
    ValuationObservation,
)
from qibao_api.dependencies import get_company_research_service
from qibao_api.dependencies import get_company_research_ai_task_service
from qibao_api.a_shares.company_research_versions import CompanyResearchVersionRepository
from qibao_api.routes.research import router
import qibao_api.routes.research as research_routes
from qibao_api.contracts.company_research_ai_task import CompanyResearchAITaskSnapshot
from qibao_api.contracts.task_progress import TaskProgress


NOW = datetime(2026, 8, 3, tzinfo=timezone.utc)


def sample_response() -> CompanyResearchResponse:
    return CompanyResearchResponse(
        status="partial", symbol="600519", name="贵州茅台",
        as_of=date(2026, 8, 3), generated_at=NOW,
        dimensions=(CompanyResearchDimension(
            key="valuation", label="估值吸引力", weight=15,
            status="ready", score=Decimal("60"), summary="估值原值可用。",
            metrics={"pe_ttm": Decimal("25")}, evidence_ids=("valuation",),
        ),),
        evidence_coverage=Decimal("0.15"), base_score=Decimal("60"),
        risk_penalty=Decimal("0"), final_score=None,
        financial_history=FinancialHistory(
            status="unavailable", periods=(), annual_periods=(), latest_period=None,
            revenue_cagr_3y=None, net_profit_cagr_3y=None,
            source="sina-finance", observed_at=None, reasons=("unavailable",),
        ),
        valuation=ValuationObservation(
            status="ready", pe_ttm=Decimal("25"), pb=Decimal("8"),
            market_cap_yi=Decimal("18000"), observation_range_status="unavailable",
            observation_range_reason="缺少历史估值。", source="tencent", observed_at=NOW,
        ),
        counter_case=tuple(CounterCaseItem(
            key=f"risk_{index}", title=f"风险 {index}", status="unavailable",
            detail="无法核验", threshold=None, penalty=Decimal("0"),
        ) for index in range(10)),
        profile=CompanyProfileEvidence(
            status="unavailable", company_overview=None, industry_analysis=None,
            latest_tips=None, source="mootdx-f10", observed_at=None,
            reasons=("unavailable",),
        ),
        sources=(), reasons=("部分来源不可用",),
    )


class Service:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, date | None]] = []

    async def get(self, symbol: str, as_of: date | None = None) -> CompanyResearchResponse:
        self.calls.append((symbol, as_of))
        if self.fail:
            raise OSError("financial source unavailable")
        return sample_response()


def application(service: Service) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_company_research_service] = lambda: service
    return app


def test_company_research_route_returns_evidence_contract() -> None:
    service = Service()
    response = TestClient(application(service)).get(
        "/api/v1/a-shares/600519/company-research?as_of=2026-08-03"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "贵州茅台"
    assert response.json()["final_score"] is None
    assert len(response.json()["counter_case"]) == 10
    assert service.calls == [("600519", date(2026, 8, 3))]


def test_company_research_route_rejects_invalid_a_share_code() -> None:
    response = TestClient(application(Service())).get(
        "/api/v1/a-shares/123/company-research"
    )

    assert response.status_code == 422


def test_company_research_route_translates_service_failure() -> None:
    response = TestClient(application(Service(fail=True))).get(
        "/api/v1/a-shares/600519/company-research"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "company_research_unavailable"


def test_company_research_route_returns_frozen_cache_without_waiting_for_lazy_refresh() -> None:
    started = asyncio.Event()

    class SlowRefresh:
        async def get(self, symbol, as_of=None, *, cache_first=True):
            started.set()
            await asyncio.Event().wait()

    class Versions:
        def latest(self, symbol):
            assert symbol == "600519"
            return sample_response()

    app = application(SlowRefresh())
    app.state.company_research_version_repository = Versions()

    response = TestClient(app).get(
        "/api/v1/a-shares/600519/company-research?as_of=2026-08-03"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "贵州茅台"
    assert any("本地研究缓存" in reason for reason in response.json()["reasons"])


def test_company_research_route_supports_a_cache_only_probe() -> None:
    service = Service()
    response = TestClient(application(service)).get(
        "/api/v1/a-shares/600519/company-research?cache_only=true"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "company_research_cache_miss"
    assert service.calls == []


def test_company_research_route_does_not_wait_forever_on_a_locked_cache_lookup(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(research_routes, "COMPANY_RESEARCH_CACHE_TIMEOUT_SECONDS", 0.05)
    service = Service()
    app = application(service)
    database = tmp_path / "company-research.sqlite3"
    repository = CompanyResearchVersionRepository(database)
    locker = sqlite3.connect(database)
    locker.execute("BEGIN EXCLUSIVE")
    app.state.company_research_version_repository = repository

    started = time.perf_counter()
    try:
        response = TestClient(app).get("/api/v1/a-shares/600519/company-research")
        elapsed = time.perf_counter() - started
    finally:
        locker.rollback()
        locker.close()
        repository.close()

    assert response.status_code == 200
    assert response.json()["symbol"] == "600519"
    assert elapsed < 0.80
    assert service.calls == [("600519", date.today())]


def test_company_research_ai_task_routes_start_and_read_independent_supplement() -> None:
    progress = TaskProgress(
        task_id="ai-task-1", kind="company-research-ai", status="succeeded",
        stage="complete", processed=2, total=2, percent=100,
        detail="AI 证据总结已完成", error=None, started_at=NOW, updated_at=NOW,
        finished_at=NOW,
    )
    snapshot = CompanyResearchAITaskSnapshot(progress=progress, result=None)

    class AIService:
        def start(self, snapshot_id):
            assert snapshot_id == "research-version-1"
            return snapshot

        def snapshot(self, task_id):
            assert task_id == "ai-task-1"
            return snapshot

    app = application(Service())
    app.dependency_overrides[get_company_research_ai_task_service] = lambda: AIService()
    client = TestClient(app)

    started = client.post("/api/v1/a-shares/company-research/versions/research-version-1/ai/tasks")
    polled = client.get("/api/v1/a-shares/company-research/ai/tasks/ai-task-1")

    assert started.status_code == 200
    assert polled.status_code == 200
    assert polled.json()["progress"]["stage"] == "complete"
