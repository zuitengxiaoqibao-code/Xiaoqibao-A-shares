from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit


_SYMBOL_SEGMENT = re.compile(r"(?<=/a-shares/)(?:sh|sz|bj)?\d{6}(?=/|$)", re.IGNORECASE)
_BOND_SEGMENT = re.compile(r"(?<=/convertible-bonds/)\d{6}(?=/|$)")
_DATE_SEGMENT = re.compile(r"(?<=/)\d{4}-\d{2}-\d{2}(?=/|$)")
_UUID_SEGMENT = re.compile(
    r"(?<=/)[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=/|$)",
    re.IGNORECASE,
)
_NAMED_DYNAMIC_SEGMENTS = (
    (re.compile(r"(?<=/tasks/)[^/]+(?=/|$)"), "{task_id}"),
    (re.compile(r"(?<=/versions/)[^/]+(?=/|$)"), "{snapshot_id}"),
    (re.compile(r"(?<=/backups/)[^/]+(?=/|$)"), "{backup_id}"),
    (re.compile(r"(?<=/alerts/)[^/]+(?=/|$)"), "{alert_id}"),
    (re.compile(r"(?<=/postclose-reports/)[^/]+(?=/|$)"), "{report_id}"),
)


def normalize_performance_name(kind: str, name: str) -> str:
    if kind != "api":
        return name
    path = urlsplit(name).path or name.split("?", 1)[0]
    path = _SYMBOL_SEGMENT.sub("{symbol}", path)
    path = _BOND_SEGMENT.sub("{bond_code}", path)
    path = _DATE_SEGMENT.sub("{trading_date}", path)
    path = _UUID_SEGMENT.sub("{task_id}", path)
    for pattern, replacement in _NAMED_DYNAMIC_SEGMENTS:
        path = pattern.sub(replacement, path)
    return path


class PerformanceStore:
    def __init__(
        self,
        database: Path,
        *,
        max_samples_per_key: int = 10,
        shared_snapshot_registry=None,
        release_id: str | None = None,
    ) -> None:
        self.database = database
        self.max_samples_per_key = max_samples_per_key
        self.shared_snapshot_registry = shared_snapshot_registry
        self.release_id = release_id or os.environ.get("QIBAO_RELEASE_ID") or "runtime-v2"
        database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS performance_sample (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    success INTEGER NOT NULL,
                    cache_hit INTEGER,
                    status_code INTEGER,
                    response_source TEXT,
                    outcome TEXT,
                    release_id TEXT NOT NULL DEFAULT 'legacy',
                    observed_at TEXT NOT NULL
                )"""
            )
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(performance_sample)")
        }
        additions = {
            "status_code": "INTEGER",
            "response_source": "TEXT",
            "outcome": "TEXT",
            "release_id": "TEXT NOT NULL DEFAULT 'legacy'",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE performance_sample ADD COLUMN {name} {definition}"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def record(
        self,
        kind: str,
        name: str,
        *,
        latency_ms: int,
        success: bool,
        cache_hit: bool | None = None,
        status_code: int | None = None,
        response_source: str | None = None,
        outcome: str | None = None,
    ) -> None:
        normalized_name = normalize_performance_name(kind, name)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO performance_sample(
                    kind,name,latency_ms,success,cache_hit,status_code,response_source,
                    outcome,release_id,observed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    kind,
                    normalized_name,
                    max(0, latency_ms),
                    int(success),
                    None if cache_hit is None else int(cache_hit),
                    status_code,
                    response_source,
                    outcome,
                    self.release_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                """DELETE FROM performance_sample WHERE kind=? AND name=? AND release_id=? AND id NOT IN (
                    SELECT id FROM performance_sample WHERE kind=? AND name=? AND release_id=? ORDER BY id DESC LIMIT ?
                )""",
                (
                    kind,
                    normalized_name,
                    self.release_id,
                    kind,
                    normalized_name,
                    self.release_id,
                    self.max_samples_per_key,
                ),
            )

    def summary(self, *, include_historical: bool = False) -> list[dict]:
        with self._connect() as connection:
            where = "" if include_historical else " WHERE release_id=?"
            parameters = () if include_historical else (self.release_id,)
            keys = connection.execute(
                f"SELECT DISTINCT kind,name,release_id FROM performance_sample{where} ORDER BY kind,name,release_id",
                parameters,
            ).fetchall()
            result = []
            for kind, name, release_id in keys:
                rows = connection.execute(
                    """SELECT latency_ms,success,cache_hit,status_code,response_source,outcome
                    FROM performance_sample WHERE kind=? AND name=? AND release_id=? ORDER BY id""",
                    (kind, name, release_id),
                ).fetchall()
                latencies = [row[0] for row in rows]
                cache_values = [row[2] for row in rows if row[2] is not None]
                status_counts = Counter(str(row[3]) for row in rows if row[3] is not None)
                source_counts = Counter(row[4] for row in rows if row[4])
                outcome_counts = Counter(row[5] for row in rows if row[5])
                result.append({
                    "kind": kind,
                    "name": name,
                    "release_id": release_id,
                    "sample_count": len(rows),
                    "p50_ms": _nearest_rank(latencies, 0.50),
                    "p95_ms": _nearest_rank(latencies, 0.95),
                    "failure_rate": round(sum(1 for row in rows if not row[1]) / len(rows) * 100, 2),
                    "cache_hit_rate": round(sum(cache_values) / len(cache_values) * 100, 2) if cache_values else None,
                    "cache_observed_count": len(cache_values),
                    "status_counts": dict(sorted(status_counts.items())),
                    "source_counts": dict(sorted(source_counts.items())),
                    "outcome_counts": dict(sorted(outcome_counts.items())),
                    "recent_ms": latencies,
                })
            return result

    def snapshot_summary(self) -> list[dict]:
        if self.shared_snapshot_registry is None:
            return []
        return self.shared_snapshot_registry.summary()


def _nearest_rank(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * percentile + 0.999999) - 1))
    return ordered[index]
