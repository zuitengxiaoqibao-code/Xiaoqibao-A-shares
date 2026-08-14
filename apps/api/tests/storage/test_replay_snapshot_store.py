import sqlite3
from datetime import UTC, date, datetime

import pytest

from qibao_api.contracts.replay_snapshot import ReplayInputReference
from qibao_api.storage.replay_snapshot_store import ReplaySnapshotStore


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


def _input() -> ReplayInputReference:
    return ReplayInputReference(
        domain="market_cross_section",
        reference="shared-snapshot:market_cross_section:7",
        content_hash="a" * 64,
        source="tdx-local-daily",
        observed_at=NOW,
        status="ready",
    )


def test_replay_snapshot_is_idempotent_and_append_only(tmp_path) -> None:
    store = ReplaySnapshotStore(tmp_path / "replay.sqlite3")
    first = store.append(
        trading_date=date(2026, 8, 14), captured_at=NOW, inputs=(_input(),),
        source_health={"ready": 1}, strategy_version="strategy-v2",
    )
    second = store.append(
        trading_date=date(2026, 8, 14), captured_at=NOW, inputs=(_input(),),
        source_health={"ready": 1}, strategy_version="strategy-v2",
    )

    assert first.snapshot_id == second.snapshot_id
    assert len(store.list(trading_date=date(2026, 8, 14))) == 1
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.connection.execute("UPDATE replay_snapshots SET strategy_version='changed'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.connection.execute("DELETE FROM replay_snapshots")

