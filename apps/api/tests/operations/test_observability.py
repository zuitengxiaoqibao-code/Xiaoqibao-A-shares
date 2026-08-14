import sqlite3
from datetime import UTC, datetime

import pytest

from qibao_api.operations.observability import ObservabilityStore


def test_observability_aggregates_repeated_failures_and_quality_alerts(tmp_path) -> None:
    store = ObservabilityStore(tmp_path / "observability.sqlite3")
    now = datetime(2026, 8, 14, 8, tzinfo=UTC)
    for _ in range(3):
        store.record("market-overview", status="unavailable", observed_at=now, coverage_percent=65, latency_ms=6001)

    snapshot = store.snapshot()

    codes = {item["code"] for item in snapshot["alerts"]}
    assert {"repeated_failure", "coverage_low", "latency_high"} <= codes
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.connection.execute("DELETE FROM observability_events")

