from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4


class ObservabilityStore:
    """Small append-only local event stream with deterministic alert rules."""

    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS observability_events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id TEXT NOT NULL UNIQUE,
          event_type TEXT NOT NULL,
          status TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          latency_ms INTEGER,
          coverage_percent REAL,
          error_code TEXT,
          trace_id TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS ix_observability_events_time
          ON observability_events(observed_at DESC, sequence DESC);
        CREATE TRIGGER IF NOT EXISTS observability_no_update
        BEFORE UPDATE ON observability_events
        BEGIN SELECT RAISE(ABORT, 'observability events are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS observability_no_delete
        BEFORE DELETE ON observability_events
        BEGIN SELECT RAISE(ABORT, 'observability events are append-only'); END;
        """)

    def record(
        self,
        event_type: str,
        *,
        status: str,
        observed_at: datetime | None = None,
        latency_ms: int | None = None,
        coverage_percent: float | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        event = {
            "event_id": f"obs-{uuid4().hex}",
            "event_type": event_type,
            "status": status,
            "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
            "latency_ms": max(0, latency_ms) if latency_ms is not None else None,
            "coverage_percent": coverage_percent,
            "error_code": error_code,
            "trace_id": trace_id,
            "metadata": metadata or {},
        }
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT INTO observability_events(
                event_id,event_type,status,observed_at,latency_ms,coverage_percent,
                error_code,trace_id,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    event["event_id"], event["event_type"], event["status"], event["observed_at"],
                    event["latency_ms"], event["coverage_percent"], event["error_code"],
                    event["trace_id"], json.dumps(event["metadata"], ensure_ascii=False, sort_keys=True),
                ),
            )
        return event

    def recent(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM observability_events ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "event_id": row["event_id"], "event_type": row["event_type"],
                "status": row["status"], "observed_at": row["observed_at"],
                "latency_ms": row["latency_ms"], "coverage_percent": row["coverage_percent"],
                "error_code": row["error_code"], "trace_id": row["trace_id"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def snapshot(self, limit: int = 100) -> dict:
        events = self.recent(limit)
        failures = Counter(
            item["event_type"] for item in events if item["status"] in {"error", "unavailable"}
        )
        alerts = []
        for event_type, count in failures.items():
            if count >= 3:
                alerts.append({"severity": "high", "code": "repeated_failure", "event_type": event_type, "detail": f"{event_type} 最近窗口连续失败 {count} 次"})
        for item in events:
            if item["coverage_percent"] is not None and item["coverage_percent"] < 70:
                alerts.append({"severity": "medium", "code": "coverage_low", "event_type": item["event_type"], "detail": f"{item['event_type']} 覆盖率仅 {item['coverage_percent']}%"})
            if item["latency_ms"] is not None and item["latency_ms"] > 5000:
                alerts.append({"severity": "medium", "code": "latency_high", "event_type": item["event_type"], "detail": f"{item['event_type']} 延迟超过 5 秒"})
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "window_size": limit, "events": events, "alerts": alerts[:50]}

    def close(self) -> None:
        with self._lock:
            self.connection.close()

