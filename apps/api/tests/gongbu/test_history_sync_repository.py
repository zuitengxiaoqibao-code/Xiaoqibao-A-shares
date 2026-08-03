from datetime import date

from qibao_api.gongbu.history_sync_repository import HistorySyncRepository


TARGET = date(2026, 7, 24)


def test_incremental_job_is_idempotent_and_running_item_resumes_as_pending(tmp_path) -> None:
    path = tmp_path / "history-sync.sqlite3"
    first = HistorySyncRepository(path)
    job = first.create_job("incremental", TARGET, ("000001", "600000"))
    duplicate = first.create_job("incremental", TARGET, ("000001",))
    first.mark_running(job.job_id, "000001")
    first.close()

    reopened = HistorySyncRepository(path)
    reopened.recover_interrupted()

    assert duplicate.job_id == job.job_id
    assert reopened.next_pending(job.job_id).symbol == "000001"
    assert reopened.get(job.job_id).state == "pending"


def test_item_completion_updates_derived_progress_and_source_counts(tmp_path) -> None:
    repository = HistorySyncRepository(tmp_path / "history-sync.sqlite3")
    job = repository.create_job(
        "backfill", TARGET, ("000001", "600000", "688001")
    )

    repository.mark_running(job.job_id, "000001")
    repository.complete_item(
        job.job_id, "000001", state="ready", source="mootdx", written_rows=300
    )
    repository.mark_running(job.job_id, "600000")
    repository.complete_item(
        job.job_id, "600000", state="ready", source="baidu", written_rows=280
    )
    repository.complete_item(
        job.job_id, "688001", state="skipped", source=None, written_rows=0
    )
    completed = repository.finish(job.job_id)

    assert completed.state == "completed"
    assert completed.total_count == 3
    assert completed.ready_count == 2
    assert completed.skipped_count == 1
    assert completed.failed_count == 0
    assert completed.pending_count == 0
    assert completed.tdx_ready_count == 1
    assert completed.baidu_ready_count == 1


def test_pause_request_stops_new_work_and_is_persisted(tmp_path) -> None:
    repository = HistorySyncRepository(tmp_path / "history-sync.sqlite3")
    job = repository.create_job("backfill", TARGET, ("000001",))

    paused = repository.request_pause(job.job_id)

    assert paused.pause_requested is True
    assert paused.state == "paused"
    assert repository.is_pause_requested(job.job_id) is True
    assert repository.next_pending(job.job_id) is None


def test_failed_item_keeps_only_safe_error_code(tmp_path) -> None:
    repository = HistorySyncRepository(tmp_path / "history-sync.sqlite3")
    job = repository.create_job("backfill", TARGET, ("000001",))
    repository.mark_running(job.job_id, "000001")

    repository.complete_item(
        job.job_id,
        "000001",
        state="failed",
        source=None,
        written_rows=0,
        error_code="DataSourceUnavailable",
    )

    item = repository.items(job.job_id)[0]
    assert item.error_code == "DataSourceUnavailable"
    assert item.state == "failed"
    assert repository.get(job.job_id).failed_count == 1
