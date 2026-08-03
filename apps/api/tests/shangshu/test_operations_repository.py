import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.shangshu.operations_repository import OperationsRepository


def event(
    *,
    status: str,
    sequence: int,
    source: str = "mootdx",
    operation: str = "bars",
    metadata: dict[str, str | int] | None = None,
) -> SourceAttemptEvent:
    return SourceAttemptEvent(
        source=source,
        operation=operation,
        target="119.97.185.59:7709",
        status=status,
        latency_ms=sequence * 10,
        observed_at=datetime(2026, 7, 17, 8, sequence, tzinfo=UTC),
        error_code="timeout" if status != "ready" else None,
        metadata=metadata or {},
    )


def test_source_health_is_append_only_and_uses_recent_window(tmp_path: Path) -> None:
    repository = OperationsRepository(tmp_path / "operations.sqlite3")
    repository.append_source_attempt(event(status="error", sequence=1))
    repository.append_source_attempt(
        event(status="ready", sequence=2, metadata={"latest_trade_date": "2026-07-16", "field_count": 8})
    )
    repository.append_source_attempt(event(status="empty", sequence=3))

    health = repository.source_health(limit=2)

    assert len(health) == 1
    item = health[0]
    assert item["source"] == "mootdx"
    assert item["operation"] == "bars"
    assert item["status"] == "degraded"
    assert item["attempts"] == 2
    assert item["successes"] == 1
    assert item["success_rate"] == 50.0
    assert item["average_latency_ms"] == 25
    assert item["latest_trade_date"] == "2026-07-16"
    assert item["field_count"] == 8

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "UPDATE source_attempt_events SET status='ready' WHERE sequence=1"
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute("DELETE FROM source_attempt_events WHERE sequence=1")


def test_source_health_marks_all_recent_failures_unavailable(tmp_path: Path) -> None:
    repository = OperationsRepository(tmp_path / "operations.sqlite3")
    repository.append_source_attempt(event(status="error", sequence=1, source="baidu"))
    repository.append_source_attempt(event(status="empty", sequence=2, source="baidu"))

    item = repository.source_health()[0]

    assert item["status"] == "unavailable"
    assert item["success_rate"] == 0.0
    assert item["last_error_code"] == "timeout"
