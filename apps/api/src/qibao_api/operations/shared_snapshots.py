from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


SNAPSHOT_KINDS = (
    "market_cross_section",
    "limit_events",
    "sector_strength",
    "stock_fund_flow",
    "news_events",
    "financial_valuation",
    "quant_factors",
)


class SharedSnapshotRegistry:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.database = database
        with self._connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS shared_snapshot_latest (
              kind TEXT PRIMARY KEY,
              snapshot_version INTEGER NOT NULL,
              trade_date TEXT,
              observed_at TEXT NOT NULL,
              coverage_percent REAL,
              content_hash TEXT NOT NULL,
              freshness TEXT NOT NULL,
              source TEXT NOT NULL,
              compute_count INTEGER NOT NULL,
              reuse_count INTEGER NOT NULL,
              duplicate_compute_count INTEGER NOT NULL,
              slowest_compute_ms INTEGER NOT NULL,
              latest_latency_ms INTEGER NOT NULL
            );
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def record(
        self,
        kind: str,
        *,
        content_hash: str,
        trade_date: date | None,
        observed_at: datetime,
        coverage_percent: float | None,
        freshness: str,
        source: str,
        reused: bool,
        latency_ms: int,
    ) -> dict:
        if kind not in SNAPSHOT_KINDS:
            raise ValueError("unknown shared snapshot kind")
        if len(content_hash) != 64:
            raise ValueError("shared snapshot hash must be SHA-256")
        safe_latency = max(0, latency_ms)
        with self._connect() as connection:
            current = connection.execute(
                "SELECT * FROM shared_snapshot_latest WHERE kind=?", (kind,)
            ).fetchone()
            same_content = current is not None and current["content_hash"] == content_hash
            version = (
                int(current["snapshot_version"])
                if same_content
                else (int(current["snapshot_version"]) + 1 if current is not None else 1)
            )
            compute_count = (int(current["compute_count"]) if current is not None else 0) + (0 if reused else 1)
            reuse_count = (int(current["reuse_count"]) if current is not None else 0) + (1 if reused else 0)
            duplicate_count = (
                (int(current["duplicate_compute_count"]) if current is not None else 0)
                + (1 if same_content and not reused else 0)
            )
            slowest = max(
                int(current["slowest_compute_ms"]) if current is not None else 0,
                0 if reused else safe_latency,
            )
            connection.execute(
                """INSERT INTO shared_snapshot_latest(
                kind,snapshot_version,trade_date,observed_at,coverage_percent,
                content_hash,freshness,source,compute_count,reuse_count,
                duplicate_compute_count,slowest_compute_ms,latest_latency_ms
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(kind) DO UPDATE SET
                  snapshot_version=excluded.snapshot_version,
                  trade_date=excluded.trade_date,
                  observed_at=excluded.observed_at,
                  coverage_percent=excluded.coverage_percent,
                  content_hash=excluded.content_hash,
                  freshness=excluded.freshness,
                  source=excluded.source,
                  compute_count=excluded.compute_count,
                  reuse_count=excluded.reuse_count,
                  duplicate_compute_count=excluded.duplicate_compute_count,
                  slowest_compute_ms=excluded.slowest_compute_ms,
                  latest_latency_ms=excluded.latest_latency_ms""",
                (
                    kind, version, trade_date.isoformat() if trade_date else None,
                    observed_at.isoformat(), coverage_percent, content_hash,
                    freshness, source, compute_count, reuse_count, duplicate_count,
                    slowest, safe_latency,
                ),
            )
            row = connection.execute(
                "SELECT * FROM shared_snapshot_latest WHERE kind=?", (kind,)
            ).fetchone()
            return self._summary_row(row)

    def summary(self) -> list[dict]:
        with self._connect() as connection:
            rows = {
                row["kind"]: row
                for row in connection.execute(
                    "SELECT * FROM shared_snapshot_latest"
                ).fetchall()
            }
        return [
            self._summary_row(rows[kind]) if kind in rows else {
                "kind": kind,
                "snapshot_version": 0,
                "trade_date": None,
                "observed_at": None,
                "coverage_percent": None,
                "content_hash": None,
                "freshness": "unavailable",
                "source": "unavailable",
                "compute_count": 0,
                "reuse_count": 0,
                "duplicate_compute_count": 0,
                "cache_hit_rate": None,
                "slowest_compute_ms": 0,
                "latest_latency_ms": 0,
            }
            for kind in SNAPSHOT_KINDS
        ]

    @staticmethod
    def _summary_row(row: sqlite3.Row) -> dict:
        compute_count = int(row["compute_count"])
        reuse_count = int(row["reuse_count"])
        attempts = compute_count + reuse_count
        return {
            "kind": row["kind"],
            "snapshot_version": int(row["snapshot_version"]),
            "trade_date": row["trade_date"],
            "observed_at": row["observed_at"],
            "coverage_percent": row["coverage_percent"],
            "content_hash": row["content_hash"],
            "freshness": row["freshness"],
            "source": row["source"],
            "compute_count": compute_count,
            "reuse_count": reuse_count,
            "duplicate_compute_count": int(row["duplicate_compute_count"]),
            "cache_hit_rate": round(reuse_count / attempts * 100, 2) if attempts else None,
            "slowest_compute_ms": int(row["slowest_compute_ms"]),
            "latest_latency_ms": int(row["latest_latency_ms"]),
        }
