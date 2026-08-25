from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from qibao_api.contracts.bars import DataSourceState, SyncReport
from qibao_api.contracts.history_sync import (
    HistoryCoverageGap,
    HistoryCoverageSummary,
    HistoryRepairCenter,
    HistorySyncJob,
)
from qibao_api.contracts.history_supplement import HistorySupplementJob, OfficialTdxPackageInfo
from qibao_api.contracts.tdx_import import TdxImportJob, TdxImportScan
from qibao_api.dependencies import (
    get_full_market_history_service,
    get_history_sync_executor,
    get_history_supplement_executor,
    get_market_data_service,
    get_tdx_import_executor,
    get_tdx_import_service,
    get_history_supplement_service,
    get_server_time,
)
from qibao_api.main import app


class FakeRepository:
    def latest(self, symbol: str, limit: int):
        return []


class FakeMarketDataService:
    repository = FakeRepository()

    def sync_symbol(self, symbol: str, limit: int) -> SyncReport:
        return SyncReport(
            symbol=symbol,
            state=DataSourceState.READY,
            written_rows=limit,
            source="baidu",
            parquet_path=f"{symbol}.parquet",
            started_at=datetime(2026, 7, 13, 14, 0),
            finished_at=datetime(2026, 7, 13, 14, 1),
            message="同步完成",
        )


class UnexpectedRepository:
    def latest(self, symbol: str, limit: int):
        raise AssertionError(f"repository must not receive invalid A-share code {symbol}")


class UnexpectedMarketDataService:
    repository = UnexpectedRepository()

    def sync_symbol(self, symbol: str, limit: int) -> SyncReport:
        raise AssertionError(f"service must not receive invalid A-share code {symbol}")


def make_history_job(
    *,
    mode: str = "backfill",
    target_date: date = date(2026, 7, 27),
    state: str = "pending",
) -> HistorySyncJob:
    observed_at = datetime(2026, 7, 27, 9, 30, tzinfo=timezone.utc)
    return HistorySyncJob(
        job_id="history-sync-test",
        mode=mode,
        target_date=target_date,
        state=state,
        total_count=5980,
        ready_count=12,
        failed_count=0,
        skipped_count=0,
        pending_count=5968,
        tdx_ready_count=10,
        baidu_ready_count=2,
        created_at=observed_at,
        updated_at=observed_at,
    )


class RecordingFullMarketHistoryService:
    def __init__(self) -> None:
        self.current = None
        self.run_calls: list[str] = []
        self.incremental_dates: list[date] = []
        self.pause_calls: list[str] = []
        self.retry_calls: list[str] = []
        self.restart_dates: list[date] = []

    def create_backfill(self) -> HistorySyncJob:
        self.current = make_history_job()
        return self.current

    def create_incremental(self, target_date: date) -> HistorySyncJob:
        self.incremental_dates.append(target_date)
        self.current = make_history_job(mode="incremental", target_date=target_date)
        return self.current

    def current_job(self) -> HistorySyncJob | None:
        return self.current

    def coverage(self, target_date: date) -> HistoryCoverageSummary:
        return HistoryCoverageSummary(
            target_date=target_date,
            universe_count=5980,
            backfill_complete_count=12,
            eligible_count=13,
            target_date_count=7,
        )

    def repair_center(self, target_date, *, offset, limit):
        return HistoryRepairCenter(
            coverage=self.coverage(target_date),
            current_job=self.current,
            gaps=(HistoryCoverageGap(
                symbol="600001",
                bar_count=120,
                latest_trade_date=date(2026, 7, 23),
                gap_kind="insufficient_history",
            ),),
            total_gap_count=1,
            offset=offset,
            limit=limit,
        )

    def pause(self, job_id: str) -> HistorySyncJob:
        self.pause_calls.append(job_id)
        return make_history_job(state="paused")

    def resume(self, job_id: str) -> HistorySyncJob:
        self.current = make_history_job(state="pending")
        return self.current

    def retry_failed(self, job_id: str) -> HistorySyncJob:
        self.retry_calls.append(job_id)
        self.current = make_history_job(state="pending")
        return self.current

    def restart_current(self, target_date: date) -> HistorySyncJob:
        self.restart_dates.append(target_date)
        self.current = make_history_job(mode="incremental", target_date=target_date)
        return self.current

    def run(self, job_id: str) -> HistorySyncJob:
        self.run_calls.append(job_id)
        return make_history_job(state="completed")


class RecordingExecutor:
    def __init__(self) -> None:
        self.submissions = []

    def submit(self, function, *args):
        self.submissions.append((function, args))
        return object()


def make_tdx_import_job(state: str = "pending") -> TdxImportJob:
    observed_at = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)
    return TdxImportJob(
        job_id="tdx-import-test", state=state, stage="queued", paths=("D:/tdx/vipdoc",),
        total_files=10, processed_files=2, imported_rows=50, replaced_rows=0,
        skipped_rows=3, failed_files=0, current_file="sh600000.day",
        latest_trade_date="2026-08-13", percent=20, created_at=observed_at,
        updated_at=observed_at,
    )


class RecordingTdxImportService:
    def __init__(self) -> None:
        self.current = make_tdx_import_job("completed")
        self.create_calls = []
        self.run_calls = []

    def scan(self, paths):
        return TdxImportScan(
            scanned_paths=tuple(str(item) for item in paths), day_files=10,
            archive_files=1, readable_files=9, latest_trade_date="2026-08-13",
        )

    def current_job(self):
        return self.current

    def create_job(self, paths):
        self.create_calls.append(tuple(paths))
        self.current = make_tdx_import_job()
        return self.current

    def run(self, job_id):
        self.run_calls.append(job_id)

    def pause(self, job_id):
        self.current = make_tdx_import_job("paused")
        return self.current

    def resume(self, job_id):
        self.current = make_tdx_import_job()
        return self.current


class RecordingHistorySupplementService:
    def __init__(self) -> None:
        self.run_calls = []
        self.job = None

    def package_info(self):
        return OfficialTdxPackageInfo(
            size_label="520.67MB", modified_at="2026-08-18T15:58:48+08:00",
        )

    def current_job(self):
        return self.job

    def create_job(self):
        observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
        self.job = HistorySupplementJob(
            job_id="history-supplement-test", state="pending", stage="queued",
            percent=0, source_url="https://data.tdx.com.cn/vipdoc/hsjday.zip",
            downloaded_bytes=0, day_file_count=0, supported_file_count=0,
            imported_rows=0, replaced_rows=0, skipped_rows=0, failed_files=0,
            created_at=observed, updated_at=observed,
        )
        return self.job

    def run(self, job_id):
        self.run_calls.append(job_id)


def make_tdx_import_client(service, executor):
    app.dependency_overrides[get_tdx_import_service] = lambda: service
    app.dependency_overrides[get_tdx_import_executor] = lambda: executor
    return TestClient(app)


def make_client() -> TestClient:
    app.dependency_overrides[get_market_data_service] = lambda: FakeMarketDataService()
    return TestClient(app)


def make_history_client(service, executor) -> TestClient:
    app.dependency_overrides[get_full_market_history_service] = lambda: service
    app.dependency_overrides[get_history_sync_executor] = lambda: executor
    return TestClient(app)


def make_supplement_client(service, executor) -> TestClient:
    app.dependency_overrides[get_history_supplement_service] = lambda: service
    app.dependency_overrides[get_history_supplement_executor] = lambda: executor
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_sync_endpoint_returns_actual_source() -> None:
    with make_client() as client:
        response = client.post("/api/v1/a-shares/600000/history/sync?limit=20")

    assert response.status_code == 200
    assert response.json()["source"] == "baidu"
    assert response.json()["written_rows"] == 20


def test_tdx_import_scan_returns_real_file_counts() -> None:
    service = RecordingTdxImportService()
    with make_tdx_import_client(service, RecordingExecutor()) as client:
        response = client.post("/api/v1/a-shares/tdx-import/scan", json={"paths": ["D:/tdx/vipdoc"]})

    assert response.status_code == 200
    assert response.json()["readable_files"] == 9
    assert response.json()["latest_trade_date"] == "2026-08-13"


def test_tdx_import_start_submits_background_job() -> None:
    service = RecordingTdxImportService()
    executor = RecordingExecutor()
    with make_tdx_import_client(service, executor) as client:
        response = client.post("/api/v1/a-shares/tdx-import/start", json={"paths": ["D:/tdx/vipdoc"]})

    assert response.status_code == 202
    assert response.json()["job_id"] == "tdx-import-test"
    assert executor.submissions[0][1] == ("tdx-import-test",)


def test_tdx_import_current_pause_and_resume_are_exposed() -> None:
    service = RecordingTdxImportService()
    executor = RecordingExecutor()
    with make_tdx_import_client(service, executor) as client:
        current = client.get("/api/v1/a-shares/tdx-import/current")
        paused = client.post("/api/v1/a-shares/tdx-import/tdx-import-test/pause")
        resumed = client.post("/api/v1/a-shares/tdx-import/tdx-import-test/resume")

    assert current.status_code == 200
    assert current.json()["state"] == "completed"
    assert paused.json()["state"] == "paused"
    assert resumed.status_code == 202
    assert executor.submissions[-1][1] == ("tdx-import-test",)


def test_official_history_supplement_metadata_and_start_are_exposed() -> None:
    service = RecordingHistorySupplementService()
    executor = RecordingExecutor()

    with make_supplement_client(service, executor) as client:
        metadata = client.get("/api/v1/a-shares/history-supplement/official-info")
        started = client.post("/api/v1/a-shares/history-supplement/official/start")
        current = client.get("/api/v1/a-shares/history-supplement/current")

    assert metadata.status_code == 200
    assert metadata.json()["modified_at"] == "2026-08-18T15:58:48+08:00"
    assert started.status_code == 202
    assert current.json()["job_id"] == "history-supplement-test"
    assert executor.submissions[0][1] == ("history-supplement-test",)


def test_official_history_metadata_decode_error_is_localized() -> None:
    class BrokenMetadataService(RecordingHistorySupplementService):
        def package_info(self):
            raise UnicodeDecodeError("utf-8", b"\\xc1", 0, 1, "invalid start byte")

    with make_supplement_client(BrokenMetadataService(), RecordingExecutor()) as client:
        response = client.get("/api/v1/a-shares/history-supplement/official-info")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "本地行情数据库暂时不可读取，可能正在被其他任务占用，请等待当前任务完成后重试"
    )


def test_history_endpoint_returns_empty_list_before_sync() -> None:
    with make_client() as client:
        response = client.get("/api/v1/a-shares/600000/history?limit=20")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("symbol", ["113001", "123001"])
@pytest.mark.parametrize(
    ("method", "suffix"),
    [("post", "/history/sync"), ("get", "/history")],
)
def test_history_routes_reject_bond_code_before_downstream_call(
    symbol: str, method: str, suffix: str
) -> None:
    app.dependency_overrides[get_market_data_service] = lambda: UnexpectedMarketDataService()
    with TestClient(app) as client:
        response = getattr(client, method)(f"/api/v1/a-shares/{symbol}{suffix}")

    assert response.status_code == 422


def test_backfill_route_returns_before_background_work_finishes() -> None:
    service = RecordingFullMarketHistoryService()
    executor = RecordingExecutor()

    with make_history_client(service, executor) as client:
        response = client.post("/api/v1/a-shares/history-sync/backfill")

    assert response.status_code == 202
    assert response.json()["state"] == "pending"
    assert service.run_calls == []
    assert executor.submissions[0][1] == ("history-sync-test",)


def test_incremental_route_uses_requested_target_date() -> None:
    service = RecordingFullMarketHistoryService()
    executor = RecordingExecutor()

    with make_history_client(service, executor) as client:
        response = client.post(
            "/api/v1/a-shares/history-sync/incremental?target_date=2026-07-24"
        )

    assert response.status_code == 202
    assert response.json()["mode"] == "incremental"
    assert service.incremental_dates == [date(2026, 7, 24)]


def test_current_history_sync_route_returns_latest_job() -> None:
    service = RecordingFullMarketHistoryService()
    service.current = make_history_job(state="running")

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.get("/api/v1/a-shares/history-sync/current")

    assert response.status_code == 200
    assert response.json()["job_id"] == "history-sync-test"
    assert response.json()["state"] == "running"


def test_history_coverage_route_returns_verified_counts() -> None:
    service = RecordingFullMarketHistoryService()

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.get(
            "/api/v1/a-shares/history-sync/coverage?target_date=2026-07-24"
        )

    assert response.status_code == 200
    assert response.json()["universe_count"] == 5980
    assert response.json()["eligible_count"] == 13
    assert response.json()["target_date_count"] == 7


def test_history_repair_center_route_is_read_only_and_paginated() -> None:
    service = RecordingFullMarketHistoryService()

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.get(
            "/api/v1/a-shares/history-sync/repair-center"
            "?target_date=2026-07-24&offset=0&limit=50"
        )

    assert response.status_code == 200
    assert response.json()["total_gap_count"] == 1
    assert response.json()["gaps"][0]["gap_kind"] == "insufficient_history"
    assert service.run_calls == []


def test_history_repair_center_falls_back_when_database_date_is_unavailable() -> None:
    class LockedHistoryService(RecordingFullMarketHistoryService):
        def default_target_date(self):
            raise UnicodeDecodeError("utf-8", b"\\xc1", 0, 1, "invalid start byte")

    service = LockedHistoryService()
    app.dependency_overrides[get_server_time] = lambda: datetime(
        2026, 8, 25, 3, 31, tzinfo=timezone.utc
    )

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.get("/api/v1/a-shares/history-sync/repair-center")

    assert response.status_code == 200
    assert response.json()["coverage"]["target_date"] == "2026-08-24"


def test_history_quality_route_is_read_only() -> None:
    service = RecordingFullMarketHistoryService()
    service.quality_report = lambda *, limit: {
        "status": "partial", "limit": limit,
    }

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.get("/api/v1/a-shares/history-sync/quality?limit=90")

    assert response.status_code == 200
    assert response.json() == {"status": "partial", "limit": 90}
    assert service.run_calls == []


def test_pause_history_sync_route_requests_a_safe_stop() -> None:
    service = RecordingFullMarketHistoryService()

    with make_history_client(service, RecordingExecutor()) as client:
        response = client.post(
            "/api/v1/a-shares/history-sync/history-sync-test/pause"
        )

    assert response.status_code == 200
    assert response.json()["state"] == "paused"
    assert service.pause_calls == ["history-sync-test"]


def test_resume_history_sync_route_submits_the_paused_job() -> None:
    service = RecordingFullMarketHistoryService()
    service.current = make_history_job(state="paused")
    executor = RecordingExecutor()

    with make_history_client(service, executor) as client:
        response = client.post(
            "/api/v1/a-shares/history-sync/history-sync-test/resume"
        )

    assert response.status_code == 202
    assert response.json()["state"] == "pending"
    assert service.run_calls == []
    assert executor.submissions[0][1] == ("history-sync-test",)


def test_retry_failed_history_symbols_submits_only_the_existing_job() -> None:
    service = RecordingFullMarketHistoryService()
    service.current = make_history_job(state="paused")
    executor = RecordingExecutor()

    with make_history_client(service, executor) as client:
        response = client.post(
            "/api/v1/a-shares/history-sync/history-sync-test/retry-failed"
        )

    assert response.status_code == 202
    assert response.json()["state"] == "pending"
    assert service.retry_calls == ["history-sync-test"]
    assert executor.submissions[0][1] == ("history-sync-test",)


def test_restart_current_history_replaces_a_stale_paused_task() -> None:
    service = RecordingFullMarketHistoryService()
    service.current = make_history_job(target_date=date(2026, 7, 29), state="paused")
    executor = RecordingExecutor()

    with make_history_client(service, executor) as client:
        response = client.post(
            "/api/v1/a-shares/history-sync/restart-current?target_date=2026-08-19"
        )

    assert response.status_code == 202
    assert response.json()["target_date"] == "2026-08-19"
    assert service.restart_dates == [date(2026, 8, 19)]
    assert executor.submissions[0][1] == ("history-sync-test",)
