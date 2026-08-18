from datetime import UTC, date, datetime

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_backup_service, get_operations_read_model, get_operations_repository, get_scheduler, get_task_progress_registry, get_performance_store, get_tdx_auto_import_monitor
from qibao_api.gongbu.backup_service import BackupRecord, BackupVerification
from qibao_api.routes.operations import realtime_stream, router
from qibao_api.operations.read_model import OperationsReadModel
from qibao_api.tasks.progress import TaskProgressRegistry
from qibao_api.operations.performance_store import PerformanceStore
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


NOW = datetime(2026, 7, 14, 8, 0, tzinfo=UTC)


class Scheduler:
    def __init__(self):
        self.paused = False
        self.manual = []

    def status(self):
        return {"paused": self.paused, "jobs": []}

    def set_paused(self, value, now):
        self.paused = value

    def run_manual(self, phase, trading_date, now):
        self.manual.append((phase, trading_date))
        return type("Report", (), {"report_id": "report-manual"})()


class Backups:
    def backups(self):
        return [BackupRecord(backup_id="backup-1", created_at=NOW, file_count=3, total_bytes=42)]

    def create(self):
        return BackupRecord(backup_id="backup-2", created_at=NOW, file_count=4, total_bytes=84)

    def verify(self, backup_id, *, restore_drill):
        assert restore_drill is True
        return BackupVerification(backup_id=backup_id, valid=True,
                                  restore_drill_passed=True, checked_files=4)


class FailingBackups:
    def backups(self):
        return []

    def create(self):
        raise OSError("database locked")


class SourceHealth:
    def source_health(self, limit=20):
        assert limit == 20
        return [{
            "source": "baidu",
            "operation": "history",
            "target": "https://finance.pae.baidu.com/selfselect/getstockquotation",
            "status": "degraded",
            "attempts": 2,
            "successes": 1,
            "failures": 1,
            "empty_responses": 0,
            "success_rate": 50.0,
            "average_latency_ms": 120,
            "latest_latency_ms": 80,
            "last_success_at": "2026-07-17T08:00:00+00:00",
            "last_failure_at": "2026-07-17T07:59:00+00:00",
            "last_error_code": "DataSourceUnavailable",
            "latest_trade_date": "2026-07-16",
            "field_count": 8,
            "row_count": 250,
            "validation": "schema_ohlc_unique_dates",
        }]


def test_operations_routes_control_scheduler_and_manual_run() -> None:
    scheduler = Scheduler()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: scheduler
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    client = TestClient(app)

    paused = client.post("/api/v1/operations/scheduler/pause")
    status = client.get("/api/v1/operations/status")
    manual = client.post("/api/v1/operations/jobs/postclose/2026-07-14/run")
    resumed = client.post("/api/v1/operations/scheduler/resume")

    assert paused.status_code == 200
    assert status.json()["scheduler"]["paused"] is True
    assert status.json()["backups"][0]["backup_id"] == "backup-1"
    assert manual.json()["report_id"] == "report-manual"
    assert scheduler.manual == [("postclose", date(2026, 7, 14))]
    assert resumed.json()["paused"] is False


def test_operations_routes_create_and_restore_verify_backup() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: Scheduler()
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    client = TestClient(app)

    created = client.post("/api/v1/operations/backups")
    verified = client.post("/api/v1/operations/backups/backup-2/verify?restore_drill=true")

    assert created.status_code == 200
    assert created.json()["file_count"] == 4
    assert verified.json()["valid"] is True
    assert verified.json()["restore_drill_passed"] is True


def test_operations_route_hides_backup_creation_error_details() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_backup_service] = lambda: FailingBackups()
    client = TestClient(app)

    response = client.post("/api/v1/operations/backups")

    assert response.status_code == 503
    assert response.json()["detail"] == "一致性备份创建失败，详细原因已写入本地运行日志"
    assert "database locked" not in response.text


def test_operations_route_exposes_source_health_without_raw_errors() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: Scheduler()
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    app.dependency_overrides[get_operations_repository] = lambda: SourceHealth()
    client = TestClient(app)

    response = client.get("/api/v1/operations/source-health")

    assert response.status_code == 200
    body = response.json()
    assert body["window_size"] == 20
    assert body["sources"][0]["status"] == "degraded"
    assert body["sources"][0]["latest_trade_date"] == "2026-07-16"
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_operations_realtime_stream_requires_topics_and_sends_latest_snapshot() -> None:
    bus = RealtimeSnapshotBus()
    bus.publish(
        "quant_strategy",
        {"status": "partial", "candidates": []},
        observed_at=NOW,
        source="tdx-local",
        freshness="live",
    )
    with pytest.raises(Exception) as missing:
        await realtime_stream(type("Request", (), {})(), bus, None)
    assert missing.value.detail["code"] == "realtime_topics_required"

    class Request:
        calls = 0

        async def is_disconnected(self):
            self.calls += 1
            return self.calls > 1

    response = await realtime_stream(Request(), bus, "quant_strategy")
    chunks = [chunk async for chunk in response.body_iterator]
    body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks)
    assert "event: quant_strategy" in body
    assert '"status":"partial"' in body
    assert bus._subscribers == {}


def test_operations_status_exposes_inventory_without_running_scans(tmp_path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "cache" / "stale.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "market.duckdb").write_bytes(b"market")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: Scheduler()
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    app.dependency_overrides[get_operations_read_model] = lambda: OperationsReadModel(tmp_path)
    client = TestClient(app)

    status = client.get("/api/v1/operations/status")
    cleanup = client.post("/api/v1/operations/cache/cleanup?older_than_hours=0")

    assert status.status_code == 200
    assert status.json()["inventory"]["directories"]["cache"]["file_count"] == 1
    assert status.json()["inventory"]["databases"]["data/market.duckdb"]["bytes"] == 6
    assert status.json()["inventory"]["release"]["persistent_bytes"] >= 6
    assert status.json()["inventory"]["release"]["protected_directories"] == [
        "backups", "config", "data", "exports", "models", "news",
    ]
    assert cleanup.status_code == 200
    assert cleanup.json()["removed_count"] == 1
    assert (tmp_path / "data" / "market.duckdb").exists()


def test_operations_status_exposes_tdx_auto_import_state() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: Scheduler()
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    app.dependency_overrides[get_tdx_auto_import_monitor] = lambda: type(
        "Monitor", (), {"status": lambda self: {"state": "baseline", "file_count": 3}}
    )()
    client = TestClient(app)

    response = client.get("/api/v1/operations/status")

    assert response.status_code == 200
    assert response.json()["tdx_auto_import"]["state"] == "baseline"
    assert response.json()["tdx_auto_import"]["file_count"] == 3


def test_operations_diagnostics_is_safe_and_actionable(tmp_path) -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduler] = lambda: Scheduler()
    app.dependency_overrides[get_backup_service] = lambda: Backups()
    app.dependency_overrides[get_operations_read_model] = lambda: OperationsReadModel(tmp_path)
    app.dependency_overrides[get_operations_repository] = lambda: SourceHealth()
    app.dependency_overrides[get_tdx_auto_import_monitor] = lambda: type(
        "Monitor", (), {"status": lambda self: {"state": "unchanged", "file_count": 2, "error": None}}
    )()
    client = TestClient(app)

    response = client.get("/api/v1/operations/diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert body["backup_count"] == 1
    assert body["tdx_auto_import"]["state"] == "unchanged"
    assert body["source_health"]["ready"] == 0
    assert body["quality_matrix"]["items"][0]["domain"] == "source_probe:history"
    assert body["quality_matrix"]["items"][0]["coverage_percent"] == 50.0
    assert body["quality_matrix"]["items"][0]["valid_count"] == 1
    assert body["quality_matrix"]["items"][0]["total_count"] == 2
    assert "api_key" not in response.text.lower()
    assert "token" not in response.text.lower()


def test_operations_route_returns_real_task_progress_and_404_for_unknown() -> None:
    registry = TaskProgressRegistry(clock=lambda: NOW)
    task = registry.create("company-research", total=4)
    registry.update(task.task_id, status="running", stage="financials", processed=1)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_task_progress_registry] = lambda: registry
    client = TestClient(app)

    response = client.get(f"/api/v1/operations/tasks/{task.task_id}")
    missing = client.get("/api/v1/operations/tasks/not-found")

    assert response.status_code == 200
    assert response.json()["percent"] == 25.0
    assert response.json()["stage"] == "financials"
    assert missing.status_code == 404


def test_operations_storage_requires_preview_confirmation_and_exposes_performance(tmp_path) -> None:
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "old.json").write_text("{}", encoding="utf-8")
    performance = PerformanceStore(tmp_path / "data" / "performance.sqlite3")
    performance.record("api", "/health", latency_ms=12, success=True, cache_hit=True)
    performance.shared_snapshot_registry = type("Snapshots", (), {
        "summary": lambda _self: [{
            "kind": "market_cross_section", "snapshot_version": 2,
            "trade_date": "2026-07-14", "observed_at": NOW.isoformat(),
            "coverage_percent": 99.0, "content_hash": "a" * 64,
            "freshness": "live", "source": "local-tdx",
            "compute_count": 3, "reuse_count": 4,
            "duplicate_compute_count": 1, "cache_hit_rate": 57.14,
            "slowest_compute_ms": 320, "latest_latency_ms": 8,
        }],
    })()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_operations_read_model] = lambda: OperationsReadModel(tmp_path)
    app.dependency_overrides[get_performance_store] = lambda: performance
    client = TestClient(app)

    preview = client.get("/api/v1/operations/storage/cleanup-preview?older_than_hours=0")
    rejected = client.post("/api/v1/operations/storage/cleanup?older_than_hours=0")
    cleaned = client.post("/api/v1/operations/storage/cleanup?older_than_hours=0&confirm=true")
    metrics = client.get("/api/v1/operations/performance")
    freshness = client.get("/api/v1/operations/freshness-policies")

    assert preview.json()["candidate_count"] == 1
    assert rejected.status_code == 409
    assert cleaned.json()["removed_count"] == 1
    assert metrics.json()["metrics"][0]["p50_ms"] == 12
    assert metrics.json()["snapshots"][0]["kind"] == "market_cross_section"
    assert metrics.json()["snapshots"][0]["duplicate_compute_count"] == 1
    assert freshness.json()["policies"]["intraday_quote"]["live_seconds"] == 120
