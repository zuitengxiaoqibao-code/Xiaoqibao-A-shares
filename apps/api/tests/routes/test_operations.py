from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_backup_service, get_operations_repository, get_scheduler
from qibao_api.gongbu.backup_service import BackupRecord, BackupVerification
from qibao_api.routes.operations import router


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
