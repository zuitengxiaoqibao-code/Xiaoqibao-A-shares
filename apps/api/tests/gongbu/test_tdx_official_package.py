import hashlib
import io
import struct
import zipfile
from datetime import date, datetime, timezone

import httpx
import pytest

from qibao_api.gongbu.tdx_official_package import (
    OfficialTdxPackageService,
    inspect_official_archive,
    parse_official_package_info,
)


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

    reconciled = service.reconcile_current_job()

    assert reconciled is not None
    assert reconciled.state == "partial"
    assert reconciled.stage == "partial"
    assert reconciled.final_target_date == date(2026, 8, 19)
    assert reconciled.final_dominant_trade_date == date(2026, 8, 18)
    assert reconciled.final_dominant_coverage_percent == 87.27
    assert reconciled.final_history_coverage_percent == 97.42
    assert reconciled.remaining_gap_count == 154
    assert reconciled.final_quality == "stale"
    assert "主导交易日仍落后" in (reconciled.result_detail or "")


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

    assert completed.state == "completed"
    assert completed.stage == "completed"
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
