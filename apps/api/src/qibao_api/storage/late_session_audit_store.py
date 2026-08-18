from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict


class LateSessionAuditSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    trading_date: date
    captured_at: AwareDatetime
    input_hash: str
    output_hash: str
    formula_version: str
    regime: str | None = None
    payload: dict[str, Any]


class LateSessionAuditStore:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS late_session_audit (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          trading_date TEXT NOT NULL,
          captured_at TEXT NOT NULL,
          input_hash TEXT NOT NULL,
          output_hash TEXT NOT NULL,
          formula_version TEXT NOT NULL,
          regime TEXT,
          payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_late_session_audit_date
          ON late_session_audit(trading_date, captured_at DESC, sequence DESC);
        CREATE TRIGGER IF NOT EXISTS late_session_audit_no_update
        BEFORE UPDATE ON late_session_audit
        BEGIN SELECT RAISE(ABORT, 'late-session audit is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS late_session_audit_no_delete
        BEFORE DELETE ON late_session_audit
        BEGIN SELECT RAISE(ABORT, 'late-session audit is append-only'); END;
        """)

    def record(
        self,
        *,
        trading_date: date,
        captured_at: datetime,
        input_hash: str,
        output_hash: str,
        formula_version: str,
        regime: str | None,
        payload: dict[str, Any],
    ) -> LateSessionAuditSnapshot:
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        content = "|".join((trading_date.isoformat(), input_hash, output_hash, formula_version, payload_json))
        snapshot_id = f"late-session-{hashlib.sha256(content.encode('utf-8')).hexdigest()[:24]}"
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO late_session_audit(
                snapshot_id,trading_date,captured_at,input_hash,output_hash,
                formula_version,regime,payload_json) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    snapshot_id,
                    trading_date.isoformat(),
                    captured_at.isoformat(),
                    input_hash,
                    output_hash,
                    formula_version,
                    regime,
                    payload_json,
                ),
            )
        return self.get(snapshot_id)

    def get(self, snapshot_id: str) -> LateSessionAuditSnapshot:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM late_session_audit WHERE snapshot_id=?",
                (snapshot_id,),
            ).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return self._model(row)

    def list(self, *, trading_date: date | None = None, limit: int = 100) -> tuple[LateSessionAuditSnapshot, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("audit limit must be between 1 and 1000")
        query = "SELECT * FROM late_session_audit"
        params: list[Any] = []
        if trading_date is not None:
            query += " WHERE trading_date=?"
            params.append(trading_date.isoformat())
        query += " ORDER BY captured_at DESC, sequence DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
        return tuple(self._model(row) for row in rows)

    @staticmethod
    def _model(row: sqlite3.Row) -> LateSessionAuditSnapshot:
        return LateSessionAuditSnapshot(
            snapshot_id=row["snapshot_id"],
            trading_date=row["trading_date"],
            captured_at=row["captured_at"],
            input_hash=row["input_hash"],
            output_hash=row["output_hash"],
            formula_version=row["formula_version"],
            regime=row["regime"],
            payload=json.loads(row["payload_json"]),
        )

    def close(self) -> None:
        with self._lock:
            self.connection.close()

