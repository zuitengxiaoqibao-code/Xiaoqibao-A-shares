from datetime import UTC, datetime

import pytest

from qibao_api.tasks.progress import TaskProgressRegistry


NOW = datetime(2026, 8, 12, 8, 0, tzinfo=UTC)


def test_progress_omits_percent_without_a_real_total() -> None:
    registry = TaskProgressRegistry(clock=lambda: NOW)

    task = registry.create("company-research", stage="queued", detail="等待执行")
    running = registry.update(task.task_id, status="running", stage="profile", processed=2)

    assert running.processed == 2
    assert running.total is None
    assert running.percent is None


def test_progress_uses_real_processed_total_and_clamps_to_total() -> None:
    registry = TaskProgressRegistry(clock=lambda: NOW)
    task = registry.create("candidate-scan", total=8)

    halfway = registry.update(task.task_id, status="running", processed=4)
    complete = registry.update(task.task_id, status="succeeded", processed=99)

    assert halfway.percent == 50.0
    assert complete.processed == 8
    assert complete.percent == 100.0
    assert complete.finished_at == NOW


def test_terminal_task_cannot_return_to_running() -> None:
    registry = TaskProgressRegistry(clock=lambda: NOW)
    task = registry.create("company-research", total=1)
    registry.update(task.task_id, status="failed", error="source unavailable")

    with pytest.raises(ValueError, match="terminal"):
        registry.update(task.task_id, status="running")


def test_registry_evicts_oldest_finished_tasks_but_keeps_active_tasks() -> None:
    registry = TaskProgressRegistry(clock=lambda: NOW, max_finished=1)
    active = registry.create("active")
    first = registry.create("first")
    registry.update(first.task_id, status="succeeded")
    second = registry.create("second")
    registry.update(second.task_id, status="succeeded")

    assert registry.get(active.task_id) is not None
    assert registry.get(first.task_id) is None
    assert registry.get(second.task_id) is not None

