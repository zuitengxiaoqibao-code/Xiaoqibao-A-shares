from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_data_lineage_repository
from qibao_api.routes.operations import router


class FakeLineageRepository:
    def list(self, **filters):
        assert filters["domain"] == "quant_strategy"
        assert filters["symbol"] == "600519"
        assert filters["trade_date"] == date(2026, 8, 14)
        return [{
            "lineage_id": "lineage-1",
            "domain": "quant_strategy",
            "field": "close",
            "symbol": "600519",
            "trade_date": "2026-08-14",
            "observed_at": "2026-08-15T08:00:00+00:00",
            "source": "local-tdx",
            "source_version": "tdx-7.73",
            "content_hash": "a" * 64,
            "status": "ready",
            "coverage_percent": 99.5,
            "limitations": [],
        }]


def test_data_lineage_route_exposes_filterable_provenance():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_data_lineage_repository] = lambda: FakeLineageRepository()
    client = TestClient(app)

    response = client.get(
        "/api/v1/operations/data-lineage"
        "?domain=quant_strategy&symbol=600519&trade_date=2026-08-14"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["records"][0]["content_hash"] == "a" * 64
    assert body["records"][0]["source"] == "local-tdx"
