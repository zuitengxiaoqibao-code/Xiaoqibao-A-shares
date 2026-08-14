from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from qibao_api.contracts.task_progress import TaskProgress, TaskStatus


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


class TaskProgressRegistry:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        max_finished: int = 200,
    ) -> None:
        if max_finished < 0:
            raise ValueError("max_finished must be non-negative")
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_finished = max_finished
        self._tasks: dict[str, TaskProgress] = {}
        self._finished: deque[str] = deque()
        self._lock = RLock()

    def create(
        self,
        kind: str,
        *,
        stage: str = "queued",
        detail: str | None = None,
        total: int | None = None,
    ) -> TaskProgress:
        now = self._clock()
        task = TaskProgress(
            task_id=uuid4().hex,
            kind=kind,
            status="queued",
            stage=stage,
            processed=0 if total is not None else None,
            total=total,
            percent=0.0 if total is not None else None,
            detail=detail,
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> TaskProgress | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        stage: str | None = None,
        processed: int | None = None,
        total: int | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> TaskProgress:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                raise KeyError(task_id)
            if current.status in TERMINAL_STATUSES:
                raise ValueError("terminal task cannot be updated")
            next_status = status or current.status
            next_total = total if total is not None else current.total
            if current.total is not None and next_total is not None:
                next_total = max(current.total, next_total)
            next_processed = processed if processed is not None else current.processed
            if current.processed is not None and next_processed is not None:
                next_processed = max(current.processed, next_processed)
            if next_total is not None:
                next_processed = min(next_total, next_processed or 0)
                next_percent = round(next_processed / next_total * 100, 2)
            else:
                next_percent = None
            if next_status == "succeeded" and next_total is not None:
                next_processed = next_total
                next_percent = 100.0
            now = self._clock()
            terminal = next_status in TERMINAL_STATUSES
            updated = current.model_copy(update={
                "status": next_status,
                "stage": stage or current.stage,
                "processed": next_processed,
                "total": next_total,
                "percent": next_percent,
                "detail": detail if detail is not None else current.detail,
                "updated_at": now,
                "finished_at": now if terminal else None,
                "error": error if error is not None else current.error,
            })
            updated = TaskProgress.model_validate(updated)
            self._tasks[task_id] = updated
            if terminal:
                self._finished.append(task_id)
                self._trim_finished()
            return updated

    def _trim_finished(self) -> None:
        while len(self._finished) > self._max_finished:
            task_id = self._finished.popleft()
            self._tasks.pop(task_id, None)
