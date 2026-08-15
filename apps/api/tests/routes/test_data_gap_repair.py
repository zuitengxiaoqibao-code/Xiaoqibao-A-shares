from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import (
    get_full_market_history_service,
    get_history_sync_executor,
    get_server_time,
)
from qibao_api.routes.operations import router


NOW = datetime(2026, 8, 15, 8, 0, tzinfo=UTC)


class FakeJobs:
    def create_job(self, mode, target_date, symbols):
        assert mode == "incremental"
        assert target_date == date(2026, 8, 14)
        assert symbols == ("600519", "000001")
        return type("Job", (), {
            "job_id": "history-sync-gap-1",
            "state": "pending",
            "target_date": target_date,
        })()


class FakeHistoryService:
    jobs = FakeJobs()

    def current_job(self):
        return None

    def run(self, job_id):
        assert job_id == "history-sync-gap-1"


class Executor:
    def __init__(self):
        self.calls = []

    def submit(self, fn, job_id):
        self.calls.append((fn, job_id))


def test_data_gap_repair_accepts_only_explicit_gap_batch_and_submits_real_sync():
    app = FastAPI()
    app.include_router(router)
    executor = Executor()
    app.dependency_overrides[get_full_market_history_service] = lambda: FakeHistoryService()
    app.dependency_overrides[get_history_sync_executor] = lambda: executor
    app.dependency_overrides[get_server_time] = lambda: NOW
    client = TestClient(app)

    response = client.post("/api/v1/operations/data-gaps/repair", json={
        "target_date": "2026-08-14",
        "source": "mootdx",
        "gaps": [
            {"symbol": "600519", "trade_date": "2026-08-14", "fields": ["close"]},
            {"symbol": "000001", "trade_date": "2026-08-14", "fields": ["volume"]},
        ],
    })

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "history-sync-gap-1"
    assert body["state"] == "pending"
    assert body["written_rows"] == 0
    assert len(body["content_hash"]) == 64
    assert executor.calls and executor.calls[0][1] == "history-sync-gap-1"


def test_data_gap_repair_rejects_empty_or_future_batch():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_full_market_history_service] = lambda: FakeHistoryService()
    app.dependency_overrides[get_history_sync_executor] = lambda: Executor()
    app.dependency_overrides[get_server_time] = lambda: NOW
    client = TestClient(app)

    empty = client.post("/api/v1/operations/data-gaps/repair", json={
        "target_date": "2026-08-14", "source": "mootdx", "gaps": [],
    })
    future = client.post("/api/v1/operations/data-gaps/repair", json={
        "target_date": "2026-08-16", "source": "mootdx",
        "gaps": [{"symbol": "600519", "trade_date": "2026-08-16", "fields": ["close"]}],
    })

    assert empty.status_code == 422
    assert future.status_code == 422
