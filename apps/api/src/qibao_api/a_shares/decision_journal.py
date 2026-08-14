"""Append-only manual decision journal; it never sends orders."""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable
from uuid import uuid4

from qibao_api.contracts.decision_journal import (
    DecisionJournalCreate,
    DecisionJournalEntry,
)


class DecisionJournalStore:
    def __init__(
        self,
        database_path: Path,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS decision_journal_entries (
                    entry_id TEXT PRIMARY KEY,
                    decision_id TEXT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    actual_price TEXT,
                    quantity TEXT,
                    note TEXT NOT NULL,
                    market_regime TEXT,
                    screener_session_id TEXT,
                    snapshot_hash TEXT,
                    observation_reason TEXT,
                    risks TEXT NOT NULL DEFAULT '[]',
                    invalidation_conditions TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_decision_journal_recorded
                ON decision_journal_entries(recorded_at DESC, created_at DESC);
                """
            )
            existing = {row[1] for row in connection.execute("PRAGMA table_info(decision_journal_entries)").fetchall()}
            for name, definition in {
                "market_regime": "TEXT", "screener_session_id": "TEXT", "snapshot_hash": "TEXT",
                "observation_reason": "TEXT", "risks": "TEXT NOT NULL DEFAULT '[]'",
                "invalidation_conditions": "TEXT NOT NULL DEFAULT '[]'",
            }.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE decision_journal_entries ADD COLUMN {name} {definition}")

    def append(self, request: DecisionJournalCreate) -> DecisionJournalEntry:
        created_at = self.clock()
        entry = DecisionJournalEntry(
            entry_id=f"journal-{uuid4().hex}",
            created_at=created_at,
            **request.model_dump(),
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO decision_journal_entries
                (entry_id, decision_id, symbol, action, recorded_at, actual_price,
                 quantity, note, market_regime, screener_session_id, snapshot_hash,
                 observation_reason, risks, invalidation_conditions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.entry_id,
                    entry.decision_id,
                    entry.symbol,
                    entry.action,
                    entry.recorded_at.isoformat(),
                    str(entry.actual_price) if entry.actual_price is not None else None,
                    str(entry.quantity) if entry.quantity is not None else None,
                    entry.note,
                    entry.market_regime,
                    entry.screener_session_id,
                    entry.snapshot_hash,
                    entry.observation_reason,
                    json.dumps(entry.risks, ensure_ascii=False),
                    json.dumps(entry.invalidation_conditions, ensure_ascii=False),
                    entry.created_at.isoformat(),
                ),
            )
        return entry

    def recent(self, *, limit: int = 50) -> tuple[DecisionJournalEntry, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM decision_journal_entries
                   ORDER BY recorded_at DESC, rowid DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return tuple(_entry(row) for row in rows)

    def on_date(self, value) -> tuple[DecisionJournalEntry, ...]:
        prefix = value.isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM decision_journal_entries
                   WHERE substr(recorded_at, 1, 10) = ?
                   ORDER BY recorded_at ASC, rowid ASC""",
                (prefix,),
            ).fetchall()
        return tuple(_entry(row) for row in rows)


def _entry(row: sqlite3.Row) -> DecisionJournalEntry:
    return DecisionJournalEntry(
        entry_id=row["entry_id"],
        decision_id=row["decision_id"],
        symbol=row["symbol"],
        action=row["action"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        actual_price=Decimal(row["actual_price"]) if row["actual_price"] else None,
        quantity=Decimal(row["quantity"]) if row["quantity"] else None,
        note=row["note"],
        market_regime=row["market_regime"],
        screener_session_id=row["screener_session_id"],
        snapshot_hash=row["snapshot_hash"],
        observation_reason=row["observation_reason"],
        risks=tuple(json.loads(row["risks"] or "[]")),
        invalidation_conditions=tuple(json.loads(row["invalidation_conditions"] or "[]")),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
