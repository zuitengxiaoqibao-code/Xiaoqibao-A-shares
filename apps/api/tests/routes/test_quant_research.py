from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.factor_registry import build_default_factor_registry
from qibao_api.contracts.quant_research import QuantResearchSnapshot
from qibao_api.dependencies import get_quant_research_service, get_server_time
from qibao_api.routes.quant_research import router


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


class Service:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def current(self, now):
        self.calls.append(now)
        if self.fail:
            raise OSError("snapshot unavailable")
        return QuantResearchSnapshot(
            status="partial",
            as_of=date(2026, 8, 21),
            observed_at=NOW,
            generated_at=NOW,
            snapshot_source="cache",
            refresh_state="ready",
            factor_registry=build_default_factor_registry(
                registered_at=NOW,
            ).snapshot(as_of=NOW),
            limitations=("因子健康样本正在积累",),
        )


def application(service: Service) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_quant_research_service] = lambda: service
    app.dependency_overrides[get_server_time] = lambda: NOW
    return app


def test_quant_research_route_returns_cached_structured_snapshot() -> None:
    service = Service()

    response = TestClient(application(service)).get(
        "/api/v1/a-shares/quant-research"
    )

    assert response.status_code == 200
    assert response.json()["formula_version"] == "quant-research-intelligence-v1"
    assert response.json()["snapshot_source"] == "cache"
    assert response.json()["factor_registry"]["status"] == "ready"
    assert service.calls == [NOW]


def test_quant_research_route_translates_unexpected_failure_to_chinese() -> None:
    response = TestClient(application(Service(fail=True))).get(
        "/api/v1/a-shares/quant-research"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "quant_research_unavailable",
        "message": "量化研究快照暂不可用，请稍后重试或检查本地数据状态",
    }
