from datetime import datetime, timezone

from qibao_api.gongbu.tdx_import_repository import TdxImportRepository


NOW = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)


def test_import_job_progress_survives_reopen(tmp_path) -> None:
    repository = TdxImportRepository(tmp_path / "tdx-import.sqlite3", clock=lambda: NOW)
    job = repository.create_job(("D:/tdx/vipdoc", "D:/tdx/T0002"))

    repository.update(
        job.job_id,
        state="running",
        stage="importing",
        total_files=10,
        processed_files=3,
        imported_rows=120,
        skipped_rows=4,
        failed_files=1,
        current_file="sh600000.day",
    )
    repository.close()

    reopened = TdxImportRepository(tmp_path / "tdx-import.sqlite3", clock=lambda: NOW)
    current = reopened.current()

    assert current is not None
    assert current.job_id == job.job_id
    assert current.stage == "importing"
    assert current.processed_files == 3
    assert current.imported_rows == 120
    assert current.failed_files == 1
    assert current.current_file == "sh600000.day"


def test_import_job_can_be_completed_with_a_truthful_percent(tmp_path) -> None:
    repository = TdxImportRepository(tmp_path / "tdx-import.sqlite3", clock=lambda: NOW)
    job = repository.create_job(("D:/tdx/vipdoc",))

    completed = repository.update(
        job.job_id,
        state="completed",
        stage="completed",
        total_files=4,
        processed_files=4,
        imported_rows=8,
        skipped_rows=2,
    )

    assert completed.percent == 100
    assert completed.finished_at == NOW


def test_terminal_job_cannot_be_paused_or_resumed_through_service(tmp_path) -> None:
    repository = TdxImportRepository(tmp_path / "tdx-import.sqlite3", clock=lambda: NOW)
    job = repository.create_job(("D:/tdx/vipdoc",))
    repository.update(job.job_id, state="completed", stage="completed")

    from qibao_api.gongbu.tdx_local_import import TdxLocalImportService

    service = TdxLocalImportService(object(), job_repository=repository)
    try:
        service.pause(job.job_id)
    except ValueError as error:
        assert "running or pending" in str(error)
    else:
        raise AssertionError("completed import job must not be paused")
    try:
        service.resume(job.job_id)
    except ValueError as error:
        assert "paused" in str(error)
    else:
        raise AssertionError("completed import job must not be resumed")


def test_recover_interrupted_pauses_orphaned_running_and_pending_job(tmp_path) -> None:
    repository = TdxImportRepository(tmp_path / "tdx-import.sqlite3", clock=lambda: NOW)
    running = repository.create_job(("D:/tdx/vipdoc",))
    repository.update(running.job_id, state="running", stage="importing", total_files=10, processed_files=3)

    repository.recover_interrupted()

    recovered = repository.get(running.job_id)
    assert recovered.state == "paused"
    assert recovered.stage == "restart_paused"
    assert recovered.processed_files == 3
    assert recovered.finished_at == NOW
