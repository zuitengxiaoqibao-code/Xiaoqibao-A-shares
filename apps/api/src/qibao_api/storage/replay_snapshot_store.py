from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import threading

from qibao_api.contracts.replay_snapshot import ReplayInputReference, ReplaySnapshot


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ReplaySnapshotStore:
    """Append-only references needed to reproduce one trading-day analysis."""

    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS replay_snapshots (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          trading_date TEXT NOT NULL,
          captured_at TEXT NOT NULL,
          strategy_version TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          source_health_hash TEXT NOT NULL,
          inputs_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_replay_snapshots_trade_date
          ON replay_snapshots(trading_date, captured_at DESC, sequence DESC);
        CREATE TRIGGER IF NOT EXISTS replay_snapshots_no_update
        BEFORE UPDATE ON replay_snapshots
        BEGIN SELECT RAISE(ABORT, 'replay snapshots are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS replay_snapshots_no_delete
        BEFORE DELETE ON replay_snapshots
        BEGIN SELECT RAISE(ABORT, 'replay snapshots are append-only'); END;
        """)

    def append(
        self,
        *,
        trading_date: date,
        captured_at: datetime,
        inputs: tuple[ReplayInputReference, ...],
        source_health: dict,
        strategy_version: str,
    ) -> ReplaySnapshot:
        input_payload = [item.model_dump(mode="json") for item in inputs]
        source_health_hash = sha256(_canonical(source_health).encode("utf-8")).hexdigest()
        semantic_payload = {
            "trading_date": trading_date.isoformat(),
            "strategy_version": strategy_version,
            "inputs": input_payload,
            "source_health_hash": source_health_hash,
        }
        content_hash = sha256(_canonical(semantic_payload).encode("utf-8")).hexdigest()
        snapshot_id = f"replay-{content_hash[:24]}"
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO replay_snapshots(
                snapshot_id,trading_date,captured_at,strategy_version,content_hash,
                source_health_hash,inputs_json) VALUES(?,?,?,?,?,?,?)""",
                (
                    snapshot_id,
                    trading_date.isoformat(),
                    captured_at.isoformat(),
                    strategy_version,
                    content_hash,
                    source_health_hash,
                    _canonical(input_payload),
                ),
            )
        return self.get(snapshot_id)

    def get(self, snapshot_id: str) -> ReplaySnapshot:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM replay_snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return self._model(row)

    def list(self, *, trading_date: date | None = None, limit: int = 50) -> tuple[ReplaySnapshot, ...]:
        if limit < 1 or limit > 200:
            raise ValueError("replay snapshot limit must be between 1 and 200")
        query = "SELECT * FROM replay_snapshots"
        parameters: tuple[object, ...]
        if trading_date is not None:
            query += " WHERE trading_date=?"
            parameters = (trading_date.isoformat(), limit)
        else:
            parameters = (limit,)
        query += " ORDER BY captured_at DESC, sequence DESC LIMIT ?"
        with self._lock:
            rows = self.connection.execute(query, parameters).fetchall()
        return tuple(self._model(row) for row in rows)

    @staticmethod
    def _model(row: sqlite3.Row) -> ReplaySnapshot:
        return ReplaySnapshot(
            snapshot_id=row["snapshot_id"],
            trading_date=row["trading_date"],
            captured_at=row["captured_at"],
            strategy_version=row["strategy_version"],
            content_hash=row["content_hash"],
            source_health_hash=row["source_health_hash"],
            inputs=tuple(json.loads(row["inputs_json"])),
        )

    def close(self) -> None:
        with self._lock:
            self.connection.close()

