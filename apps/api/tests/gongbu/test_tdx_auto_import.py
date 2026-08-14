from datetime import datetime, timezone
from pathlib import Path

from qibao_api.gongbu.tdx_auto_import import TdxAutoImportMonitor


NOW = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)


class FakeService:
    def __init__(self, current=None):
        self.current = current
        self.created = []

    def current_job(self):
        return self.current

    def create_job(self, paths):
        job = type("Job", (), {"job_id": "auto-job"})()
        self.created.append(tuple(paths))
        self.current = type("Job", (), {"state": "pending", "job_id": job.job_id})()
        return job

    def run(self, job_id):
        return job_id


class FakeExecutor:
    def __init__(self):
        self.submitted = []

    def submit(self, function, *args):
        self.submitted.append((function, args))


def test_monitor_establishes_baseline_without_importing_existing_files(tmp_path: Path) -> None:
    root = tmp_path / "vipdoc"
    root.mkdir()
    (root / "sh600000.day").write_bytes(b"day")
    service = FakeService()
    executor = FakeExecutor()
    monitor = TdxAutoImportMonitor(
        lambda: (root,), service=service, executor=executor, clock=lambda: NOW
    )

    status = monitor.poll()

    assert status["state"] == "baseline"
    assert service.created == []
    assert executor.submitted == []


def test_monitor_submits_once_when_supported_file_changes(tmp_path: Path) -> None:
    root = tmp_path / "T0002"
    root.mkdir()
    archive = root / "g3day.zip"
    archive.write_bytes(b"one")
    service = FakeService()
    executor = FakeExecutor()
    monitor = TdxAutoImportMonitor(
        lambda: (root,), service=service, executor=executor, clock=lambda: NOW
    )
    monitor.poll()

    archive.write_bytes(b"two-two")
    changed = monitor.poll()

    assert changed["state"] == "submitted"
    assert changed["submitted_job_id"] == "auto-job"
    assert len(service.created) == 1
    assert len(executor.submitted) == 1
    assert monitor.poll()["state"] == "unchanged"


def test_monitor_skips_change_while_an_import_job_is_active(tmp_path: Path) -> None:
    root = tmp_path / "T0002"
    root.mkdir()
    archive = root / "g3day.zip"
    archive.write_bytes(b"one")
    active = type("Job", (), {"state": "running", "job_id": "manual-job"})()
    service = FakeService(current=active)
    executor = FakeExecutor()
    monitor = TdxAutoImportMonitor(
        lambda: (root,), service=service, executor=executor, clock=lambda: NOW
    )
    monitor.poll()

    archive.write_bytes(b"two")
    status = monitor.poll()

    assert status["state"] == "skipped_active"
    assert status["skip_reason"] == "active_job"
    assert service.created == []


def test_monitor_records_error_without_raising(tmp_path: Path) -> None:
    def broken_paths():
        raise OSError("directory unavailable")

    monitor = TdxAutoImportMonitor(
        broken_paths, service=FakeService(), executor=FakeExecutor(), clock=lambda: NOW
    )

    status = monitor.poll()

    assert status["state"] == "error"
    assert "directory unavailable" in status["error"]
