from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class PerformanceStore:
    def __init__(
        self,
        database: Path,
        *,
        max_samples_per_key: int = 10,
        shared_snapshot_registry=None,
    ) -> None:
        self.database = database
        self.max_samples_per_key = max_samples_per_key
        self.shared_snapshot_registry = shared_snapshot_registry
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
                    observed_at TEXT NOT NULL
                )"""
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
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO performance_sample(kind,name,latency_ms,success,cache_hit,observed_at) VALUES(?,?,?,?,?,?)",
                (kind, name, max(0, latency_ms), int(success), None if cache_hit is None else int(cache_hit), datetime.now(timezone.utc).isoformat()),
            )
            connection.execute(
                """DELETE FROM performance_sample WHERE kind=? AND name=? AND id NOT IN (
                    SELECT id FROM performance_sample WHERE kind=? AND name=? ORDER BY id DESC LIMIT ?
                )""",
                (kind, name, kind, name, self.max_samples_per_key),
            )

    def summary(self) -> list[dict]:
        with self._connect() as connection:
            keys = connection.execute(
                "SELECT DISTINCT kind,name FROM performance_sample ORDER BY kind,name"
            ).fetchall()
            result = []
            for kind, name in keys:
                rows = connection.execute(
                    "SELECT latency_ms,success,cache_hit FROM performance_sample WHERE kind=? AND name=? ORDER BY id",
                    (kind, name),
                ).fetchall()
                latencies = [row[0] for row in rows]
                cache_values = [row[2] for row in rows if row[2] is not None]
                result.append({
                    "kind": kind,
                    "name": name,
                    "sample_count": len(rows),
                    "p50_ms": _nearest_rank(latencies, 0.50),
                    "p95_ms": _nearest_rank(latencies, 0.95),
                    "failure_rate": round(sum(1 for row in rows if not row[1]) / len(rows) * 100, 2),
                    "cache_hit_rate": round(sum(cache_values) / len(cache_values) * 100, 2) if cache_values else None,
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
