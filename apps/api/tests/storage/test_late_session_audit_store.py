from datetime import UTC, date, datetime
import sqlite3

import pytest

from qibao_api.storage.late_session_audit_store import LateSessionAuditStore


NOW = datetime(2026, 8, 18, 6, 31, tzinfo=UTC)


def test_audit_store_is_idempotent_append_only_and_traceable(tmp_path) -> None:
    store = LateSessionAuditStore(tmp_path / "late-session-audit.sqlite3")
    payload = {"monitor_stage": "monitor", "candidates": [{"symbol": "600000"}]}

    first = store.record(
        trading_date=date(2026, 8, 18),
        captured_at=NOW,
        input_hash="input-1",
        output_hash="output-1",
        formula_version="late-session-v2",
        regime="轮动震荡",
        payload=payload,
    )
    second = store.record(
        trading_date=date(2026, 8, 18),
        captured_at=NOW,
        input_hash="input-1",
        output_hash="output-1",
        formula_version="late-session-v2",
        regime="轮动震荡",
        payload=payload,
    )

    assert first.snapshot_id == second.snapshot_id
    assert store.list(trading_date=date(2026, 8, 18))[0].payload == payload
    with pytest.raises(sqlite3.DatabaseError):
        store.connection.execute("UPDATE late_session_audit SET regime='changed'")
    with pytest.raises(sqlite3.DatabaseError):
        store.connection.execute("DELETE FROM late_session_audit")

