from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from threading import RLock
from uuid import uuid4

from qibao_api.contracts.data_lineage import DataLineageRecord


class DataLineageRepository:
    """Append-only local provenance ledger with deterministic filtering."""

    def __init__(self, database: str | Path) -> None:
        self._lock = RLock()
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS data_lineage (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              lineage_id TEXT NOT NULL UNIQUE,
              domain TEXT NOT NULL,
              field TEXT NOT NULL,
              symbol TEXT,
              trade_date TEXT,
              observed_at TEXT,
              source TEXT NOT NULL,
              source_version TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              status TEXT NOT NULL,
              coverage_percent REAL,
              limitations_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS ix_data_lineage_lookup
              ON data_lineage(domain, field, symbol, trade_date, sequence DESC);
            CREATE TRIGGER IF NOT EXISTS data_lineage_no_update
            BEFORE UPDATE ON data_lineage
            BEGIN SELECT RAISE(ABORT, 'data lineage is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS data_lineage_no_delete
            BEFORE DELETE ON data_lineage
            BEGIN SELECT RAISE(ABORT, 'data lineage is append-only'); END;
            """
        )

    def append(self, record: DataLineageRecord) -> dict:
        lineage_id = f"lineage-{uuid4().hex}"
        payload = {
            "lineage_id": lineage_id,
            "domain": record.domain,
            "field": record.field,
            "symbol": record.symbol,
            "trade_date": record.trade_date.isoformat() if record.trade_date else None,
            "observed_at": record.observed_at.isoformat() if record.observed_at else None,
            "source": record.source,
            "source_version": record.source_version,
            "content_hash": record.content_hash,
            "status": record.status,
            "coverage_percent": record.coverage_percent,
            "limitations": list(record.limitations),
        }
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT INTO data_lineage(
                lineage_id,domain,field,symbol,trade_date,observed_at,source,
                source_version,content_hash,status,coverage_percent,limitations_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    payload["lineage_id"], payload["domain"], payload["field"],
                    payload["symbol"], payload["trade_date"], payload["observed_at"],
                    payload["source"], payload["source_version"], payload["content_hash"],
                    payload["status"], payload["coverage_percent"],
                    json.dumps(payload["limitations"], ensure_ascii=False),
                ),
            )
        return payload

    def list(
        self,
        *,
        domain: str | None = None,
        field: str | None = None,
        symbol: str | None = None,
        trade_date: date | None = None,
        limit: int = 200,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        for column, value in (
            ("domain", domain),
            ("field", field),
            ("symbol", symbol),
            ("trade_date", trade_date.isoformat() if trade_date else None),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        query = "SELECT * FROM data_lineage"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY sequence DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "lineage_id": row["lineage_id"],
            "domain": row["domain"],
            "field": row["field"],
            "symbol": row["symbol"],
            "trade_date": row["trade_date"],
            "observed_at": row["observed_at"],
            "source": row["source"],
            "source_version": row["source_version"],
            "content_hash": row["content_hash"],
            "status": row["status"],
            "coverage_percent": row["coverage_percent"],
            "limitations": json.loads(row["limitations_json"] or "[]"),
        }

    def close(self) -> None:
        with self._lock:
            self.connection.close()
