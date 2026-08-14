import sqlite3
import threading
from datetime import date, datetime
import json
from pathlib import Path

from qibao_api.contracts.source_health import SourceAttemptEvent


class OperationsRepository:
    def __init__(self, database: str | Path) -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS scheduler_state_events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          paused INTEGER NOT NULL,
          occurred_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scheduled_job_events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          job_key TEXT NOT NULL,
          phase TEXT NOT NULL,
          trading_date TEXT NOT NULL,
          slot TEXT NOT NULL,
          trigger TEXT NOT NULL,
          attempt INTEGER NOT NULL,
          status TEXT NOT NULL,
          occurred_at TEXT NOT NULL,
          report_id TEXT,
          error_code TEXT,
          UNIQUE(job_key, attempt, status)
        );
        CREATE TABLE IF NOT EXISTS source_attempt_events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL,
          operation TEXT NOT NULL,
          target TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('ready', 'error', 'empty')),
          latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0),
          observed_at TEXT NOT NULL,
          error_code TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS source_health_snapshots (
          snapshot_id INTEGER PRIMARY KEY CHECK(snapshot_id = 1),
          generated_at TEXT NOT NULL,
          window_size INTEGER NOT NULL,
          sources_json TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS reject_update_scheduler_state
        BEFORE UPDATE ON scheduler_state_events
        BEGIN SELECT RAISE(ABORT, 'append-only scheduler state'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_scheduler_state
        BEFORE DELETE ON scheduler_state_events
        BEGIN SELECT RAISE(ABORT, 'append-only scheduler state'); END;
        CREATE TRIGGER IF NOT EXISTS reject_update_job_events
        BEFORE UPDATE ON scheduled_job_events
        BEGIN SELECT RAISE(ABORT, 'append-only job attempts'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_job_events
        BEFORE DELETE ON scheduled_job_events
        BEGIN SELECT RAISE(ABORT, 'append-only job attempts'); END;
        CREATE TRIGGER IF NOT EXISTS reject_update_source_attempts
        BEFORE UPDATE ON source_attempt_events
        BEGIN SELECT RAISE(ABORT, 'append-only source attempts'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_source_attempts
        BEFORE DELETE ON source_attempt_events
        BEGIN SELECT RAISE(ABORT, 'append-only source attempts'); END;
        """)
        legacy = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='scheduled_job_attempts'"
        ).fetchone()
        if legacy is not None:
            with self.connection:
                self.connection.execute("""
                INSERT OR IGNORE INTO scheduled_job_events(
                  job_key,phase,trading_date,slot,trigger,attempt,status,occurred_at,
                  report_id,error_code
                ) SELECT job_key,phase,trading_date,slot,trigger,attempt,status,
                  occurred_at,report_id,error_code FROM scheduled_job_attempts
                """)

    def set_paused(self, paused: bool, occurred_at: datetime) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                "INSERT INTO scheduler_state_events(paused,occurred_at) VALUES(?,?)",
                (int(paused), occurred_at.isoformat()),
            )

    def paused(self) -> bool:
        with self._lock:
            row = self.connection.execute(
                "SELECT paused FROM scheduler_state_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return bool(row["paused"]) if row is not None else False

    def append_attempt(
        self,
        *,
        job_key: str,
        phase: str,
        trading_date: date,
        slot: str,
        trigger: str,
        attempt: int,
        status: str,
        occurred_at: datetime,
        report_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT INTO scheduled_job_events(
                job_key,phase,trading_date,slot,trigger,attempt,status,occurred_at,
                report_id,error_code) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (job_key, phase, trading_date.isoformat(), slot, trigger, attempt,
                 status, occurred_at.isoformat(), report_id, error_code),
            )

    def attempts_for(self, job_key: str) -> list[dict]:
        with self._lock:
            rows = self.connection.execute(
                """SELECT * FROM scheduled_job_events WHERE job_key=?
                ORDER BY attempt, sequence""",
                (job_key,),
            ).fetchall()
        return [dict(row) for row in rows]

    def jobs(self) -> list[dict]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM scheduled_job_events ORDER BY sequence"
            ).fetchall()
        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault(row["job_key"], []).append(row)
        jobs = []
        for attempts in grouped.values():
            latest = dict(attempts[-1])
            latest["attempts"] = max(item["attempt"] for item in attempts)
            jobs.append(latest)
        return jobs

    def append_source_attempt(self, event: SourceAttemptEvent) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT INTO source_attempt_events(
                source, operation, target, status, latency_ms, observed_at,
                error_code, metadata_json) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    event.source,
                    event.operation,
                    event.target,
                    event.status,
                    event.latency_ms,
                    event.observed_at.isoformat(),
                    event.error_code,
                    json.dumps(event.metadata, ensure_ascii=False, sort_keys=True),
                ),
            )

    def source_health(self, limit: int = 20) -> list[dict]:
        if limit < 1:
            raise ValueError("source health window must be positive")
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM source_attempt_events ORDER BY sequence DESC"
            ).fetchall()
        grouped: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for row in rows:
            key = (row["source"], row["operation"], row["target"])
            bucket = grouped.setdefault(key, [])
            if len(bucket) < limit:
                bucket.append(row)

        result = []
        for (source, operation, target), recent in grouped.items():
            successes = sum(row["status"] == "ready" for row in recent)
            failures = sum(row["status"] == "error" for row in recent)
            empty_responses = sum(row["status"] == "empty" for row in recent)
            attempts = len(recent)
            if successes == 0:
                health_status = "unavailable"
            elif successes < attempts:
                health_status = "degraded"
            else:
                health_status = "ready"
            metadata = {}
            for row in recent:
                try:
                    values = json.loads(row["metadata_json"])
                except (TypeError, json.JSONDecodeError):
                    values = {}
                if isinstance(values, dict):
                    for key in ("latest_trade_date", "field_count", "row_count", "validation"):
                        if key not in metadata and values.get(key) is not None:
                            metadata[key] = values[key]
            ready_rows = [row for row in recent if row["status"] == "ready"]
            failure_rows = [row for row in recent if row["status"] != "ready"]
            result.append({
                "source": source,
                "operation": operation,
                "target": target,
                "status": health_status,
                "attempts": attempts,
                "successes": successes,
                "failures": failures,
                "empty_responses": empty_responses,
                "success_rate": round(successes / attempts * 100, 2),
                "average_latency_ms": round(sum(row["latency_ms"] for row in recent) / attempts),
                "latest_latency_ms": recent[0]["latency_ms"],
                "last_success_at": ready_rows[0]["observed_at"] if ready_rows else None,
                "last_failure_at": failure_rows[0]["observed_at"] if failure_rows else None,
                "last_error_code": next((row["error_code"] for row in failure_rows if row["error_code"]), None),
                "latest_trade_date": metadata.get("latest_trade_date"),
                "field_count": metadata.get("field_count"),
                "row_count": metadata.get("row_count"),
                "validation": metadata.get("validation"),
            })
        return sorted(result, key=lambda item: (item["source"], item["operation"], item["target"]))

    def refresh_source_health_snapshot(
        self, limit: int = 20, *, generated_at: datetime | None = None
    ) -> dict:
        """Persist a bounded health read model for fast, non-probing reads."""
        timestamp = generated_at or datetime.now().astimezone()
        payload = {
            "generated_at": timestamp.isoformat(),
            "window_size": limit,
            "sources": self.source_health(limit),
        }
        with self._lock, self.connection:
            self.connection.execute(
                """INSERT INTO source_health_snapshots(
                   snapshot_id, generated_at, window_size, sources_json
                ) VALUES(1, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO UPDATE SET
                   generated_at=excluded.generated_at,
                   window_size=excluded.window_size,
                   sources_json=excluded.sources_json""",
                (
                    payload["generated_at"],
                    limit,
                    json.dumps(payload["sources"], ensure_ascii=False, sort_keys=True),
                ),
            )
        return payload

    def source_health_snapshot(self) -> dict | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT generated_at, window_size, sources_json FROM source_health_snapshots WHERE snapshot_id=1"
            ).fetchone()
        if row is None:
            return None
        try:
            sources = json.loads(row["sources_json"])
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(sources, list):
            return None
        return {
            "generated_at": row["generated_at"],
            "window_size": row["window_size"],
            "sources": sources,
        }

    def close(self) -> None:
        with self._lock:
            self.connection.close()
