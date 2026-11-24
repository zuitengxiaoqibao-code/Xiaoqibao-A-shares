import hashlib
import io
import struct
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from qibao_api.gongbu.tdx_official_package import (
    OfficialTdxPackageService,
    inspect_official_archive,
    parse_official_package_info,
)
from qibao_api.gongbu.tdx_local_import import TdxLocalDatabaseUnavailable


def _submission_service(tmp_path):
    return OfficialTdxPackageService(cache_dir=tmp_path / "cache",
        state_path=tmp_path / "job.json", tdx_import_service=object(), client=object())


class _QueuedExecutor:
    def __init__(self):
        self.future = Future()

    def submit(self, *_args):
        return self.future


def test_rejected_submission_is_persisted_and_does_not_block_retry(tmp_path):
    service = _submission_service(tmp_path)
    executor = ThreadPoolExecutor(max_workers=1)
    executor.shutdown()
    with pytest.raises(RuntimeError):
        service.start_job(executor)
    failed = service.current_job()
    assert failed.state == "failed"
    assert failed.error_stage == "submit_failed"
    assert failed.finished_at is not None
    assert "重新启动" in failed.error_detail
    assert all(item.state == "skipped" for item in failed.source_attempts)
    retry = service.start_job(_QueuedExecutor())
    assert retry.job_id != failed.job_id
    assert retry.state == "pending"


def test_cancelled_queued_task_releases_active_job(tmp_path):
    service = _submission_service(tmp_path)
    executor = _QueuedExecutor()
    service.start_job(executor)
    executor.future.cancel()
    assert service.current_job().error_stage == "task_cancelled"
    assert service.current_job().state == "failed"
    assert service.create_job().state == "pending"


def test_worker_crash_does_not_leave_fake_running_status(tmp_path):
    service = _submission_service(tmp_path)
    executor = _QueuedExecutor()
    job = service.start_job(executor)
    service._update(job, state="running", stage="online_repair")
    executor.future.set_exception(RuntimeError("worker unavailable"))
    failed = service.current_job()
    assert failed.state == "failed"
    assert failed.error_stage == "worker_failed"
    assert "worker unavailable" in failed.error_detail


def test_old_callback_cannot_overwrite_new_job_or_completed_result(tmp_path):
    service = _submission_service(tmp_path)
    executor = _QueuedExecutor()
    first = service.start_job(executor)
    completed = service._update(first, state="completed", stage="completed", percent=100)
    executor.future.set_exception(RuntimeError("late error"))
    assert service.current_job() == completed
    second = service.create_job()
    service._fail_background_job(first.job_id, "worker_failed", "stale callback")
    assert service.current_job() == second


def test_shutdown_rejects_new_tasks_without_creating_or_replacing_job(tmp_path):
    service = _submission_service(tmp_path)
    service.stop_accepting_jobs()
    with pytest.raises(RuntimeError, match="关闭"):
        service.start_job(_QueuedExecutor())
    assert service.current_job() is None


def test_real_executor_runs_job_and_completion_callback_preserves_result(tmp_path, monkeypatch):
    service = _submission_service(tmp_path)
    from threading import Event
    finished = Event()

    def run(job_id):
        job = service.current_job()
        assert job.job_id == job_id
        service._update(job, state="completed", stage="completed", percent=100)
        finished.set()

    monkeypatch.setattr(service, "run", run)
    with ThreadPoolExecutor(max_workers=1) as executor:
        job = service.start_job(executor)
        assert finished.wait(3)
    assert service.current_job().job_id == job.job_id
    assert service.current_job().state == "completed"


def test_second_start_cannot_replace_queued_job(tmp_path):
    service = _submission_service(tmp_path)
    executor = _QueuedExecutor()
    first = service.start_job(executor)
    with pytest.raises(ValueError, match="正在执行"):
        service.start_job(_QueuedExecutor())
    assert service.current_job().job_id == first.job_id


@pytest.mark.parametrize("state", ["pending", "running"])
def test_restart_recovers_active_job_preserving_counts_and_cache(tmp_path, state):
    service = _submission_service(tmp_path)
    job = service.create_job()
    service._update(job, state=state, imported_rows=123, downloaded_bytes=456)
    recovered = service.recover_interrupted()
    assert recovered.state == "failed"
    assert recovered.error_stage == "restart_recovery"
    assert recovered.imported_rows == 123
    assert recovered.downloaded_bytes == 456
    assert service.create_job().state == "pending"


def _day_record(raw_date: int, close: int = 1000) -> bytes:
    return struct.pack(
        "<IIIIIfII", raw_date, close - 2, close + 2, close - 4,
        close, 100.0, 10, 0,
    )


def _archive_bytes(*, unsafe: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("sh/lday/sh600000.day", _day_record(20260818))
        archive.writestr("sh/lday/sh511010.day", _day_record(20260818))
        if unsafe:
            archive.writestr("../escape.day", _day_record(20260818))
    return output.getvalue()


def test_official_package_info_and_archive_inspection_are_truthful(tmp_path) -> None:
    info = parse_official_package_info(
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )
    archive = tmp_path / "hsjday.zip"
    archive.write_bytes(_archive_bytes())

    inspection = inspect_official_archive(archive, as_of=date(2026, 8, 19))

    assert info.size_label == "520.67MB"
    assert info.modified_at.isoformat() == "2026-08-18T15:58:48+08:00"
    assert inspection.day_file_count == 2
    assert inspection.supported_file_count == 1
    assert inspection.latest_trade_date == date(2026, 8, 18)


def test_official_package_metadata_accepts_gb18030_response() -> None:
    metadata = (
        '// 官方日线包\n'
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    ).encode("gb18030")

    class Response:
        content = metadata

        def raise_for_status(self):
            return None

        @property
        def text(self):
            raise UnicodeDecodeError("utf-8", b"\xc1", 0, 1, "invalid start byte")

    class Client:
        def get(self, _url):
            return Response()

    service = OfficialTdxPackageService(
        cache_dir=Path("cache"),
        state_path=Path("state.json"),
        tdx_import_service=object(),
        client=Client(),
        as_of=date(2026, 8, 19),
    )

    info = service.package_info()

    assert info.size_label == "520.67MB"
    assert info.modified_at.isoformat() == "2026-08-18T15:58:48+08:00"


def test_official_package_metadata_accepts_current_vendor_response() -> None:
    metadata = (
        b'/*modified at 2026-08-24 16:20:01*/\n'
        b'window.HSJDAY_SOFT_SIZE="521.36MB";\n'
        b'window.HSJDAY_SOFT_TIME="2026-08-24 15:58:48";\n'
    )

    class Response:
        content = metadata

        def raise_for_status(self):
            return None

    class Client:
        def get(self, _url):
            return Response()

    service = OfficialTdxPackageService(
        cache_dir=Path("cache"),
        state_path=Path("state.json"),
        tdx_import_service=object(),
        client=Client(),
        as_of=date(2026, 8, 24),
    )

    info = service.package_info()

    assert info.size_label == "521.36MB"
    assert info.modified_at.isoformat() == "2026-08-24T15:58:48+08:00"


def test_official_package_rejects_zip_path_escape(tmp_path) -> None:
    archive = tmp_path / "unsafe.zip"
    archive.write_bytes(_archive_bytes(unsafe=True))

    with pytest.raises(ValueError, match="压缩包包含不安全路径"):
        inspect_official_archive(archive, as_of=date(2026, 8, 19))


def test_official_package_job_downloads_validates_imports_and_survives_reopen(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=metadata)
        return httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload))},
        )

    class ImportService:
        def __init__(self) -> None:
            self.paths = []
            self.options = None

        def import_now(self, paths, **options):
            self.paths.extend(paths)
            self.options = options
            return type("Result", (), {
                "state": "completed", "imported_rows": 1, "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    importer = ImportService()
    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache",
            state_path=tmp_path / "official-package.json",
            tdx_import_service=importer,
            client=client,
            clock=lambda: observed,
            as_of=date(2026, 8, 19),
        )
        job = service.create_job()
        completed = service.run(job.job_id)

    assert completed.state == "completed"
    assert completed.stage == "completed"
    assert completed.percent == 100
    assert completed.downloaded_bytes == len(payload)
    assert completed.total_bytes == len(payload)
    assert completed.package_sha256 == hashlib.sha256(payload).hexdigest()
    assert completed.package_modified_at.isoformat() == "2026-08-18T15:58:48+08:00"
    assert completed.latest_trade_date == date(2026, 8, 18)
    assert completed.supported_file_count == 1
    assert completed.imported_rows == 1
    assert importer.paths == [tmp_path / "cache" / "hsjday-20260818.zip"]
    assert importer.options == {
        "progress": importer.options["progress"],
        "extraction_progress": importer.options["extraction_progress"],
        "discovery_progress": importer.options["discovery_progress"],
        "incremental": True,
        "source": "tdx-package",
        "batch_size": 256,
    }
    assert not (tmp_path / "cache" / "hsjday.zip.part").exists()

    reopened = OfficialTdxPackageService(
        cache_dir=tmp_path / "cache",
        state_path=tmp_path / "official-package.json",
        tdx_import_service=importer,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: observed,
        as_of=date(2026, 8, 19),
    )
    assert reopened.current_job() == completed
    reopened.close()


def test_official_package_persists_local_scan_progress(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=metadata)
        return httpx.Response(200, content=payload, headers={"Content-Length": str(len(payload))})

    class ImportService:
        def default_paths(self):
            return (tmp_path / "vipdoc",)

        def import_now(self, _paths, **options):
            options["discovery_progress"]({
                "scanned_files": 3,
                "total_scan_files": 5,
                "day_files": 3,
                "readable_files": 2,
                "current_file": "C:/tdx/vipdoc/sh/lday/sh600001.day",
                "scan_speed": 12.5,
                "scan_eta_seconds": 0.16,
            })
            return type("Result", (), {
                "state": "completed", "imported_rows": 1, "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache",
            state_path=tmp_path / "official-package.json",
            tdx_import_service=ImportService(),
            client=client,
            clock=lambda: datetime(2026, 8, 19, 2, tzinfo=timezone.utc),
            as_of=date(2026, 8, 19),
        )
        job = service.create_job()
        completed = service.run(job.job_id)

    assert completed.scan_scanned_files == 3
    assert completed.scan_total_files == 5
    assert completed.scan_day_files == 3
    assert completed.scan_readable_files == 2
    assert completed.scan_current_file.endswith("sh600001.day")
    assert completed.scan_speed == 12.5
    assert completed.scan_eta_seconds == 0.16


def test_repair_persists_committed_counts_during_local_and_package_import(tmp_path) -> None:
    payload = _archive_bytes()
    snapshots = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=(
                'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
                'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
            ))
        return httpx.Response(200, content=payload)

    class ImportService:
        def default_paths(self):
            return (tmp_path / "vipdoc",)

        def import_now(self, paths, **options):
            local = paths == self.default_paths()
            counts = (10, 30) if local else (5, 7)
            for index, rows in enumerate(counts, start=1):
                event = {
                    "phase": "writing", "scanned_files": 2, "total_scan_files": 2,
                    "day_files": 2, "readable_files": index,
                    "processed_files": index, "total_import_files": 2,
                    "imported_rows": 0 if index == 1 else counts[0],
                    "replaced_rows": 0, "skipped_rows": 0, "failed_files": 0,
                    "pending_write_rows": rows - (counts[0] if index > 1 else 0),
                }
                options["discovery_progress"](event)
                writing = service.current_job()
                assert writing.state == "running"
                assert writing.pending_write_rows > 0
                options["discovery_progress"]({
                    **event, "phase": "batch_committed", "imported_rows": rows,
                    "pending_write_rows": 0,
                })
                committed = service.current_job()
                assert committed.pending_write_rows == 0
                snapshots.append(committed.imported_rows)
            return type("Result", (), {
                "state": "completed", "imported_rows": counts[-1], "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache", state_path=tmp_path / "job.json",
            tdx_import_service=ImportService(), client=client,
            as_of=date(2026, 8, 19),
        )
        completed = service.run(service.create_job().job_id)

    assert snapshots == [10, 30, 35, 37]
    assert completed.imported_rows == 37
    assert completed.pending_write_rows == 0


def test_current_job_reclassifies_legacy_completed_scan_database_lock(tmp_path) -> None:
    observed = datetime(2026, 8, 25, 2, tzinfo=timezone.utc)

    service = OfficialTdxPackageService(
        cache_dir=tmp_path / "cache",
        state_path=tmp_path / "official-package.json",
        tdx_import_service=object(),
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500))),
        clock=lambda: observed,
        as_of=date(2026, 8, 25),
    )
    job = service.create_job()
    service._update(
        job,
        state="failed",
        stage="failed",
        percent=5,
        error_stage="scanning",
        error_detail="本地行情数据库暂时不可读取，可能正在被其他任务占用，请等待当前任务完成后重试",
        scan_scanned_files=9497,
        scan_total_files=9497,
        scan_day_files=9497,
        scan_current_file="sz399998.day",
        result_detail="已扫描 9497 个文件 / 9497",
        finished_at=observed,
    )

    normalized = service.current_job()

    assert normalized is not None
    assert normalized.state == "partial"
    assert normalized.stage == "waiting_database"
    assert normalized.percent == 6
    assert normalized.error_detail is None
    assert "重新执行一键全面修复" in (normalized.result_detail or "")
    assert service.current_job().stage == "waiting_database"
    service.close()


def test_official_package_reuses_valid_cached_archive_after_interrupted_job(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )
    calls = {"metadata": 0, "package": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            calls["metadata"] += 1
            return httpx.Response(200, text=metadata)
        calls["package"] += 1
        return httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload))},
        )

    class ImportService:
        def import_now(self, _paths, **_options):
            return type("Result", (), {
                "state": "completed", "imported_rows": 1, "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "hsjday-20260818.zip").write_bytes(payload)
    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=cache,
            state_path=tmp_path / "official-package.json",
            tdx_import_service=ImportService(),
            client=client,
            clock=lambda: observed,
            as_of=date(2026, 8, 19),
        )
        job = service.create_job()
        completed = service.run(job.job_id)

    assert completed.state == "completed"
    assert completed.package_sha256 == hashlib.sha256(payload).hexdigest()
    assert completed.downloaded_bytes == len(payload)
    assert calls == {"metadata": 1, "package": 0}


def test_official_package_marks_orphaned_running_job_as_interrupted(tmp_path) -> None:
    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)

    class ImportService:
        pass

    service = OfficialTdxPackageService(
        cache_dir=tmp_path / "cache",
        state_path=tmp_path / "official-package.json",
        tdx_import_service=ImportService(),
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500))),
        clock=lambda: observed,
        as_of=date(2026, 8, 19),
    )
    job = service.create_job()
    service._update(job, state="running", stage="importing", percent=72)

    recovered = service.recover_interrupted()

    assert recovered is not None
    assert recovered.state == "failed"
    assert recovered.stage == "failed"
    assert recovered.error_stage == "restart_recovery"
    assert "重新执行" in (recovered.error_detail or "")


def test_terminal_legacy_job_is_reconciled_against_current_coverage(tmp_path) -> None:
    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)

    class ImportService:
        pass

    class Coverage:
        universe_count = 5000
        target_date = date(2026, 8, 19)
        dominant_trade_date = date(2026, 8, 18)
        dominant_date_coverage_percent = 87.27
        coverage_percent = 97.42
        missing_history_count = 154
        quality = "stale"
        blockers = (
            "dominant_date_coverage_below_98_percent",
            "history_coverage_below_98_percent",
            "dominant_trade_date_behind_target",
        )

    class HistoryService:
        def default_target_date(self):
            return date(2026, 8, 19)

        def coverage(self, _target):
            return Coverage()

    service = OfficialTdxPackageService(
        cache_dir=tmp_path / "cache",
        state_path=tmp_path / "official-package.json",
        tdx_import_service=ImportService(),
        history_service=HistoryService(),
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500))),
        clock=lambda: observed,
        as_of=date(2026, 8, 19),
    )
    legacy = service.create_job()
    service._update(
        legacy,
        state="completed",
        stage="completed",
        percent=100,
        latest_trade_date=date(2026, 8, 18),
        finished_at=observed,
        source_attempts=(),
    )
    service.clock = lambda: observed + timedelta(days=3)

    reconciled = service.reconcile_current_job()

    assert reconciled is not None
    assert reconciled.state == "partial"
    assert reconciled.finished_at == observed
    assert reconciled.stage == "partial"
    assert reconciled.final_target_date == date(2026, 8, 19)
    assert reconciled.final_dominant_trade_date == date(2026, 8, 18)
    assert reconciled.final_dominant_coverage_percent == 87.27
    assert reconciled.final_history_coverage_percent == 97.42
    assert reconciled.remaining_gap_count == 154
    assert reconciled.final_quality == "stale"
    assert "主导交易日仍落后" in (reconciled.result_detail or "")


def test_failed_reconciliation_does_not_mutate_terminal_task(tmp_path):
    from types import SimpleNamespace
    service = _submission_service(tmp_path)
    job = service._update(service.create_job(), state="partial", stage="partial", finished_at=service._now())

    def unavailable(_target):
        raise OSError("database is temporarily locked")

    service.history_service = SimpleNamespace(default_target_date=lambda: date(2026, 11, 23), coverage=unavailable)
    with pytest.raises(OSError):
        service.reconcile_current_job()
    assert service.current_job() == job


def test_reconciliation_cannot_overwrite_newly_started_task(tmp_path):
    from types import SimpleNamespace
    service = _submission_service(tmp_path)
    service._update(service.create_job(), state="partial", stage="partial", finished_at=service._now())
    created = []

    def coverage(target):
        created.append(service.start_job(_QueuedExecutor()))
        return SimpleNamespace(universe_count=5000, target_date=target, dominant_trade_date=target,
            dominant_date_coverage_percent=100, coverage_percent=100, missing_history_count=0,
            quality="ready", blockers=())

    service.history_service = SimpleNamespace(default_target_date=lambda: date(2026, 11, 23), coverage=coverage)
    result = service.reconcile_current_job()
    assert result == created[0]
    assert service.current_job() == created[0]
    assert result.state == "pending"


def test_full_repair_reports_real_validation_extraction_import_and_verification_progress(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=metadata)
        return httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload))},
        )

    class ImportService:
        def default_paths(self):
            return ()

        def import_now(self, _paths, **options):
            options["extraction_progress"]((1, 2, "sh600000.day"))
            options["extraction_progress"]((2, 2, "sh511010.day"))
            options["progress"]((1, 1, "600000"))
            return type("Result", (), {
                "state": "completed", "imported_rows": 1, "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    class Coverage:
        universe_count = 5000
        target_date = date(2026, 8, 18)
        dominant_trade_date = date(2026, 8, 18)
        dominant_date_coverage_percent = 99.1
        coverage_percent = 99.2
        missing_history_count = 4
        quality = "ready"
        blockers = ()

    class HistoryService:
        def default_target_date(self):
            return date(2026, 8, 18)

        def coverage(self, _target):
            return Coverage()

        def create_target_repair(self, _target):
            return None

    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache",
            state_path=tmp_path / "full-repair.json",
            tdx_import_service=ImportService(),
            history_service=HistoryService(),
            client=client,
            clock=lambda: observed,
            as_of=date(2026, 8, 19),
        )
        completed = service.run(service.create_job().job_id)

    assert completed.state == "partial"
    assert completed.stage == "partial"
    assert "不代表全部修复成功" in completed.result_detail
    assert completed.validated_bytes > 0
    assert completed.validated_bytes == completed.total_validation_bytes
    assert completed.extracted_files == 2
    assert completed.total_extract_files == 2
    assert completed.processed_files == 1
    assert completed.total_import_files == 1
    assert completed.final_target_date == date(2026, 8, 18)
    assert completed.final_dominant_trade_date == date(2026, 8, 18)
    assert completed.final_dominant_coverage_percent == 99.1
    assert completed.final_history_coverage_percent == 99.2
    assert completed.remaining_gap_count == 4
    assert [item.source for item in completed.source_attempts] == [
        "tdx_local", "tdx_official", "mootdx", "baidu",
    ]


def test_full_repair_falls_back_when_local_database_date_is_temporarily_unavailable(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=metadata)
        return httpx.Response(200, content=payload)

    class ImportService:
        def default_paths(self):
            return ()

        def import_now(self, _paths, **_options):
            return type("Result", (), {
                "state": "completed", "imported_rows": 1, "replaced_rows": 0,
                "skipped_rows": 0, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    class Coverage:
        universe_count = 5000
        target_date = date(2026, 8, 19)
        dominant_trade_date = date(2026, 8, 19)
        dominant_date_coverage_percent = 99.1
        coverage_percent = 99.2
        missing_history_count = 0
        quality = "ready"
        blockers = ()

    class HistoryService:
        def default_target_date(self):
            raise UnicodeDecodeError("utf-8", b"\\xc1", 0, 1, "database is locked")

        def create_target_repair(self, target):
            assert target == date(2026, 8, 19)
            return None

        def coverage(self, target):
            assert target == date(2026, 8, 19)
            return Coverage()

    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache",
            state_path=tmp_path / "full-repair.json",
            tdx_import_service=ImportService(),
            history_service=HistoryService(),
            client=client,
            clock=lambda: observed,
            as_of=date(2026, 8, 19),
        )
        completed = service.run(service.create_job().job_id)

    assert completed.state == "completed"
    assert completed.final_target_date == date(2026, 8, 19)


def test_full_repair_preserves_completed_scan_when_local_database_remains_locked(tmp_path) -> None:
    class ImportService:
        def default_paths(self):
            return (tmp_path / "vipdoc",)

        def import_now(self, _paths, **options):
            options["discovery_progress"]({
                "phase": "scan_complete",
                "scanned_files": 9497,
                "total_scan_files": 9497,
                "day_files": 9497,
                "readable_files": 9497,
                "current_file": None,
                "scan_speed": 256.0,
                "scan_eta_seconds": 0.0,
            })
            raise TdxLocalDatabaseUnavailable(attempts=5, scanned_files=9497, total_files=9497)

    class HistoryService:
        def default_target_date(self):
            return date(2026, 8, 25)

    service = OfficialTdxPackageService(
        cache_dir=tmp_path / "cache",
        state_path=tmp_path / "history-supplement.json",
        tdx_import_service=ImportService(),
        history_service=HistoryService(),
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500))),
        as_of=date(2026, 8, 25),
    )

    completed = service.run(service.create_job().job_id)

    assert completed.state == "partial"
    assert completed.stage == "partial"
    assert completed.percent >= 6
    assert completed.scan_scanned_files == 9497
    assert completed.scan_total_files == 9497
    assert completed.scan_current_file is None
    assert "扫描已完成" in (completed.result_detail or "")
    assert "数据库" in (completed.error_detail or "")


def test_full_repair_finishes_partial_when_final_coverage_is_still_stale(tmp_path) -> None:
    payload = _archive_bytes()
    metadata = (
        'window.HSJDAY_SOFT_SIZE="520.67MB";\n'
        'window.HSJDAY_SOFT_TIME="2026-08-18 15:58:48";'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("_hsjdayinfo.js"):
            return httpx.Response(200, text=metadata)
        return httpx.Response(200, content=payload)

    class ImportService:
        def default_paths(self):
            return ()

        def import_now(self, _paths, **options):
            options["extraction_progress"]((1, 1, "sh600000.day"))
            options["progress"]((1, 1, "600000"))
            return type("Result", (), {
                "state": "completed", "imported_rows": 0, "replaced_rows": 0,
                "skipped_rows": 1, "failed_files": 0,
                "latest_trade_date": "2026-08-18", "errors": (),
            })()

    class StaleCoverage:
        universe_count = 5000
        target_date = date(2026, 8, 18)
        dominant_trade_date = date(2026, 8, 15)
        dominant_date_coverage_percent = 91.0
        coverage_percent = 97.0
        missing_history_count = 12
        quality = "partial"
        blockers = ("dominant_date_coverage_below_98_percent",)

    class RepairJob:
        job_id = "online-repair"
        state = "completed"
        total_count = 2
        ready_count = 1
        failed_count = 1
        skipped_count = 0
        pending_count = 0
        tdx_ready_count = 1
        baidu_ready_count = 0

    class HistoryService:
        def default_target_date(self):
            return date(2026, 8, 18)

        def coverage(self, _target):
            return StaleCoverage()

        def create_target_repair(self, _target):
            return RepairJob()

        def run(self, _job_id, progress=None):
            if progress:
                progress(RepairJob())
            return RepairJob()

    observed = datetime(2026, 8, 19, 2, tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(
            cache_dir=tmp_path / "cache",
            state_path=tmp_path / "full-repair.json",
            tdx_import_service=ImportService(),
            history_service=HistoryService(),
            client=client,
            clock=lambda: observed,
            as_of=date(2026, 8, 19),
        )
        completed = service.run(service.create_job().job_id)

    assert completed.state == "partial"
    assert completed.stage == "partial"
    assert completed.percent == 100
    assert completed.online_total == 2
    assert completed.online_ready == 1
    assert completed.online_failed == 1
    assert completed.remaining_gap_count == 12
    assert "主导交易日仍落后" in (completed.result_detail or "")
