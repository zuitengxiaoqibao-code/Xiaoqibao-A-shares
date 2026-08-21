from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.operations.page_snapshots import PAGE_SNAPSHOT_POLICIES, PageSnapshotService
from qibao_api.operations.shared_snapshots import SharedSnapshotRegistry
from qibao_api.routes.operations import router


def client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.page_snapshot_service = PageSnapshotService(
        SharedSnapshotRegistry(tmp_path / "shared.sqlite3")
    )
    return TestClient(app)


def test_all_fourteen_menu_contracts_are_available_without_external_fetch(tmp_path):
    test_client = client(tmp_path)
    assert len(PAGE_SNAPSHOT_POLICIES) == 14
    for menu in PAGE_SNAPSHOT_POLICIES:
        response = test_client.get(f"/api/v1/operations/page-snapshots/{menu}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["menu"] == menu
        assert payload["latency_ms"] < 1000
        assert payload["refresh_policy"]


def test_unknown_menu_returns_a_chinese_error(tmp_path):
    response = client(tmp_path).get("/api/v1/operations/page-snapshots/not-a-menu")
    assert response.status_code == 404
    assert response.json()["detail"] == "未知页面菜单"
