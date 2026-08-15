from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_precompute_snapshot_store
from qibao_api.operations.precompute_snapshots import (
    PrecomputeSnapshotConflictError,
    PrecomputeSnapshotService,
    PrecomputeSnapshotStore,
)
from qibao_api.routes.operations import router


NOW = datetime(2026, 8, 15, 8, tzinfo=UTC)
TRADE_DATE = date(2026, 8, 14)


def test_precomputed_snapshots_are_append_only_and_keep_the_last_complete_payload(tmp_path) -> None:
    store = PrecomputeSnapshotStore(tmp_path / "precomputed-snapshots.sqlite3")
    first = store.append_complete(
        "overview", trade_date=TRADE_DATE, data_version="market-v1",
        payload={"status": "ready", "advance_count": 3012},
        source="local-tdx", generated_at=NOW, compute_ms=120,
    )
    store.append_attempt(
        "overview", trade_date=TRADE_DATE, data_version="market-v2",
        status="failed", source="local-tdx", generated_at=NOW,
        compute_ms=45, limitations=("upstream_timeout",),
    )
    store.append_attempt(
        "overview", trade_date=TRADE_DATE, data_version="market-v3",
        status="partial", source="local-tdx", generated_at=NOW,
        compute_ms=60, limitations=("coverage_below_threshold",),
    )

    served = store.latest_complete("overview")
    assert served is not None
    assert served.snapshot_id == first.snapshot_id
    assert served.payload == {"status": "ready", "advance_count": 3012}
    assert store.summary()[0]["latest_attempt_status"] == "partial"
    assert store.summary()[0]["served_data_version"] == "market-v1"

    with pytest.raises(PrecomputeSnapshotConflictError):
        store.append_complete(
            "overview", trade_date=TRADE_DATE, data_version="market-v1",
            payload={"status": "ready", "advance_count": 1},
            source="local-tdx", generated_at=NOW, compute_ms=1,
        )


class QueuedExecutor:
    def __init__(self) -> None:
        self.calls = []

    def submit(self, function, *args):
        self.calls.append((function, args))

    def run_all(self) -> None:
        for function, args in tuple(self.calls):
            function(*args)
        self.calls.clear()


def test_service_serves_previous_complete_snapshot_then_refreshes_in_background(tmp_path) -> None:
    store = PrecomputeSnapshotStore(tmp_path / "precomputed-snapshots.sqlite3")
    store.append_complete(
        "quant", trade_date=TRADE_DATE, data_version="bars-v1",
        payload={"status": "partial", "candidates": 12}, source="local-bars",
        generated_at=NOW, compute_ms=80,
    )
    executor = QueuedExecutor()
    service = PrecomputeSnapshotService(store, executor=executor)

    response = service.serve_or_schedule(
        "quant", trade_date=TRADE_DATE, data_version="bars-v2",
        source="local-bars", compute=lambda: {"status": "ready", "candidates": 15},
    )

    assert response["cache_state"] == "stale"
    assert response["refresh_scheduled"] is True
    assert response["snapshot"].data_version == "bars-v1"
    assert response["snapshot"].payload["candidates"] == 12
    executor.run_all()
    assert store.latest_complete("quant", data_version="bars-v2").payload["candidates"] == 15


def test_failed_background_refresh_never_replaces_a_complete_snapshot(tmp_path) -> None:
    store = PrecomputeSnapshotStore(tmp_path / "precomputed-snapshots.sqlite3")
    original = store.append_complete(
        "research", trade_date=TRADE_DATE, data_version="finance-v1",
        payload={"status": "ready", "symbol": "600519"}, source="local-f10",
        generated_at=NOW, compute_ms=90,
    )
    executor = QueuedExecutor()
    service = PrecomputeSnapshotService(store, executor=executor)

    def fail():
        raise RuntimeError("provider failed")

    service.serve_or_schedule(
        "research", trade_date=TRADE_DATE, data_version="finance-v2",
        source="local-f10", compute=fail,
    )
    executor.run_all()

    assert store.latest_complete("research").snapshot_id == original.snapshot_id
    summary = next(item for item in store.summary() if item["domain"] == "research")
    assert summary["latest_attempt_status"] == "failed"
    assert summary["served_data_version"] == "finance-v1"


def test_precompute_snapshot_routes_expose_inventory_and_only_complete_payloads(tmp_path) -> None:
    store = PrecomputeSnapshotStore(tmp_path / "precomputed-snapshots.sqlite3")
    store.append_complete(
        "overview", trade_date=TRADE_DATE, data_version="market-v1",
        payload={"status": "ready", "advance_count": 3012},
        source="local-tdx", generated_at=NOW, compute_ms=120,
    )
    store.append_attempt(
        "overview", trade_date=TRADE_DATE, data_version="market-v2",
        status="failed", source="local-tdx", generated_at=NOW,
        compute_ms=30, limitations=("refresh_failed",),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_precompute_snapshot_store] = lambda: store
    client = TestClient(app)

    inventory = client.get("/api/v1/operations/precompute-snapshots")
    served = client.get("/api/v1/operations/precompute-snapshots/overview")

    assert inventory.status_code == 200
    assert inventory.json()["snapshots"][0]["served_data_version"] == "market-v1"
    assert served.status_code == 200
    assert served.json()["data_version"] == "market-v1"
    assert served.json()["payload"]["advance_count"] == 3012
