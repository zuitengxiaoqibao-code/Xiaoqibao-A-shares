from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.instrument_directory import AShareInstrument
from qibao_api.contracts.market import AssetKind
from qibao_api.dependencies import (
    get_a_share_instrument_directory,
    get_a_share_universe_source,
    get_compliance_repository,
)
from qibao_api.libu_compliance.repository import SourceAuthorizationError
from qibao_api.routes.research import router


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)


def instrument() -> AShareInstrument:
    return AShareInstrument(
        symbol="600519", name="贵州茅台", exchange="sh", observed_at=NOW,
        quote_quality="unavailable",
    )


class Directory:
    def __init__(self) -> None:
        self.items: list[AShareInstrument] = []

    def observe_many(self, items) -> None:
        self.items.extend(items)


class Source:
    last_source = "cninfo-a-share-universe"

    async def fetch(self):
        return (instrument(),)


class BrokenSource:
    async def fetch(self):
        request = httpx.Request("GET", "https://push2.eastmoney.com")
        raise httpx.RemoteProtocolError("server disconnected", request=request)


class Compliance:
    def require_feature_sources(self, feature, asset):
        assert feature == "a_share_universe"
        assert asset == AssetKind.A_SHARE


class Unauthorized:
    def require_feature_sources(self, feature, asset):
        raise SourceAuthorizationError("eastmoney:missing")


def client(directory, source, compliance) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_a_share_instrument_directory] = lambda: directory
    app.dependency_overrides[get_a_share_universe_source] = lambda: source
    app.dependency_overrides[get_compliance_repository] = lambda: compliance
    return TestClient(app)


def test_universe_sync_returns_count_and_updates_directory() -> None:
    directory = Directory()
    response = client(directory, Source(), Compliance()).post("/api/v1/a-shares/universe/sync")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["count"] == 1
    assert response.json()["observed_at"] == "2026-07-17T00:00:00Z"
    assert response.json()["source"] == "cninfo-a-share-universe"
    assert [item.symbol for item in directory.items] == ["600519"]


def test_universe_sync_maps_authorization_and_upstream_failures() -> None:
    unauthorized = client(Directory(), Source(), Unauthorized()).post("/api/v1/a-shares/universe/sync")
    assert unauthorized.status_code == 403
    assert unauthorized.json()["detail"]["code"] == "source_authorization_required"

    unavailable = client(Directory(), BrokenSource(), Compliance()).post("/api/v1/a-shares/universe/sync")
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "a_share_universe_unavailable"
