from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import (
    get_operations_repository,
    get_replay_snapshot_store,
    get_shared_snapshot_registry,
)
from qibao_api.routes.operations import router
from qibao_api.storage.replay_snapshot_store import ReplaySnapshotStore


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


class Registry:
    def summary(self):
        return [{
            "kind": "market_cross_section",
            "snapshot_version": 7,
            "trade_date": "2026-08-14",
            "observed_at": NOW.isoformat(),
            "content_hash": "a" * 64,
            "freshness": "live",
            "source": "tdx-local",
        }]


class Sources:
    def source_health_snapshot(self):
        return {"sources": [{"source": "tdx-local", "status": "ready"}]}

    def source_health(self, _limit=20):
        return []


def test_replay_snapshot_capture_and_query(tmp_path) -> None:
    store = ReplaySnapshotStore(tmp_path / "replay.sqlite3")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_replay_snapshot_store] = lambda: store
    app.dependency_overrides[get_shared_snapshot_registry] = lambda: Registry()
    app.dependency_overrides[get_operations_repository] = lambda: Sources()
    client = TestClient(app)

    captured = client.post(
        "/api/v1/operations/replay-snapshots/capture",
        json={"trading_date": "2026-08-14", "strategy_version": "strategy-v2"},
    )
    listed = client.get("/api/v1/operations/replay-snapshots?trading_date=2026-08-14")

    assert captured.status_code == 200
    assert captured.json()["snapshot_id"].startswith("replay-")
    assert listed.status_code == 200
    assert len(listed.json()["snapshots"]) == 1
    assert listed.json()["snapshots"][0]["inputs"][0]["source"] == "tdx-local"

