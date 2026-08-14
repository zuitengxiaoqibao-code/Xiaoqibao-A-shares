import re
import sqlite3
import threading
import json
from collections.abc import Callable, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from qibao_api.contracts.history_sync import (
    HistoryRepairAudit,
    HistorySyncItem,
    HistorySyncItemState,
    HistorySyncJob,
    HistorySyncMode,
)
from qibao_api.contracts.instruments import validate_a_share_code


_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
_TERMINAL_ITEM_STATES = ("ready", "failed", "skipped")


class HistorySyncRepository:
    def __init__(
        self,
        database_path: Path,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self._lock = threading.RLock()
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS history_sync_jobs (
                    job_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    state TEXT NOT NULL,
                    pause_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(mode, target_date)
                );
                CREATE TABLE IF NOT EXISTS history_sync_items (
                    job_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    source TEXT,
                    written_rows INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(job_id, symbol),
                    FOREIGN KEY(job_id) REFERENCES history_sync_jobs(job_id)
                );
                CREATE TABLE IF NOT EXISTS history_repair_audits (
                    audit_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    gap_count_before INTEGER NOT NULL,
                    coverage_before_percent REAL,
                    written_rows INTEGER NOT NULL,
                    ready_count INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    coverage_after_percent REAL,
                    final_state TEXT NOT NULL,
                    failure_reasons_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS ix_history_sync_items_pending
                ON history_sync_items(job_id, state, symbol);
                """
            )

    def create_job(
        self,
        mode: HistorySyncMode,
        target_date: date,
        symbols: Sequence[str],
    ) -> HistorySyncJob:
        if mode not in ("backfill", "incremental"):
            raise ValueError("unsupported history sync mode")
        validated = tuple(dict.fromkeys(validate_a_share_code(item) for item in symbols))
        if not validated:
            raise ValueError("history sync job requires at least one symbol")
        now = self._now()
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                """SELECT job_id FROM history_sync_jobs
                   WHERE mode = ? AND target_date = ?""",
                (mode, target_date.isoformat()),
            ).fetchone()
            if existing is not None:
                job_id = existing["job_id"]
            else:
                job_id = f"history-sync-{uuid4().hex}"
                connection.execute(
                    """INSERT INTO history_sync_jobs
                       (job_id, mode, target_date, state, pause_requested,
                        created_at, updated_at)
                       VALUES (?, ?, ?, 'pending', 0, ?, ?)""",
                    (job_id, mode, target_date.isoformat(), now, now),
                )
                connection.executemany(
                    """INSERT INTO history_sync_items
                       (job_id, symbol, state, attempts, source, written_rows,
                        error_code, updated_at)
                       VALUES (?, ?, 'pending', 0, NULL, 0, NULL, ?)""",
                    [(job_id, symbol, now) for symbol in validated],
                )
        return self.get(job_id)

    def get(self, job_id: str) -> HistorySyncJob:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT j.*,
                          count(i.symbol) AS total_count,
                          sum(CASE WHEN i.state = 'ready' THEN 1 ELSE 0 END) AS ready_count,
                          sum(CASE WHEN i.state = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                          sum(CASE WHEN i.state = 'skipped' THEN 1 ELSE 0 END) AS skipped_count,
                          sum(CASE WHEN i.state IN ('pending', 'running') THEN 1 ELSE 0 END) AS pending_count,
                          sum(CASE WHEN i.state = 'ready' AND i.source = 'mootdx' THEN 1 ELSE 0 END) AS tdx_ready_count,
                          sum(CASE WHEN i.state = 'ready' AND i.source = 'baidu' THEN 1 ELSE 0 END) AS baidu_ready_count
                   FROM history_sync_jobs j
                   LEFT JOIN history_sync_items i ON i.job_id = j.job_id
                   WHERE j.job_id = ?
                   GROUP BY j.job_id""",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job(row)

    def current(self) -> HistorySyncJob | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT job_id FROM history_sync_jobs
                   ORDER BY updated_at DESC, created_at DESC LIMIT 1"""
            ).fetchone()
        return self.get(row["job_id"]) if row is not None else None

    def items(self, job_id: str) -> tuple[HistorySyncItem, ...]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM history_sync_items
                   WHERE job_id = ? ORDER BY symbol""",
                (job_id,),
            ).fetchall()
        return tuple(self._item(row) for row in rows)

    def next_pending(self, job_id: str) -> HistorySyncItem | None:
        job = self.get(job_id)
        if job.pause_requested or job.state in ("paused", "completed", "failed"):
            return None
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM history_sync_items
                   WHERE job_id = ? AND state = 'pending'
                   ORDER BY symbol LIMIT 1""",
                (job_id,),
            ).fetchone()
        return self._item(row) if row is not None else None

    def mark_running(self, job_id: str, symbol: str) -> HistorySyncItem:
        symbol = validate_a_share_code(symbol)
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE history_sync_items
                   SET state = 'running', attempts = attempts + 1, updated_at = ?
                   WHERE job_id = ? AND symbol = ? AND state = 'pending'""",
                (now, job_id, symbol),
            )
            connection.execute(
                """UPDATE history_sync_jobs SET state = 'running', updated_at = ?
                   WHERE job_id = ? AND pause_requested = 0""",
                (now, job_id),
            )
            row = connection.execute(
                "SELECT * FROM history_sync_items WHERE job_id = ? AND symbol = ?",
                (job_id, symbol),
            ).fetchone()
        if row is None or row["state"] != "running":
            raise ValueError("history sync item is not pending")
        return self._item(row)

    def complete_item(
        self,
        job_id: str,
        symbol: str,
        *,
        state: HistorySyncItemState,
        source: str | None,
        written_rows: int,
        error_code: str | None = None,
    ) -> HistorySyncItem:
        if state not in _TERMINAL_ITEM_STATES:
            raise ValueError("item completion requires a terminal state")
        if source not in (None, "mootdx", "baidu"):
            raise ValueError("unsupported history source")
        if written_rows < 0:
            raise ValueError("written_rows must not be negative")
        if error_code is not None and not _SAFE_ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a safe identifier")
        symbol = validate_a_share_code(symbol)
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE history_sync_items
                   SET state = ?, source = ?, written_rows = ?, error_code = ?,
                       updated_at = ?
                   WHERE job_id = ? AND symbol = ?
                     AND state IN ('pending', 'running')""",
                (state, source, written_rows, error_code, now, job_id, symbol),
            )
            connection.execute(
                "UPDATE history_sync_jobs SET updated_at = ? WHERE job_id = ?",
                (now, job_id),
            )
            row = connection.execute(
                "SELECT * FROM history_sync_items WHERE job_id = ? AND symbol = ?",
                (job_id, symbol),
            ).fetchone()
        if row is None or row["state"] != state:
            raise ValueError("history sync item cannot be completed")
        return self._item(row)

    def request_pause(self, job_id: str) -> HistorySyncJob:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE history_sync_jobs
                   SET pause_requested = 1, state = 'paused', updated_at = ?
                   WHERE job_id = ? AND state IN ('pending', 'running', 'paused')""",
                (now, job_id),
            )
        return self.get(job_id)

    def resume(self, job_id: str) -> HistorySyncJob:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE history_sync_jobs
                   SET pause_requested = 0, state = 'pending', updated_at = ?
                   WHERE job_id = ? AND state = 'paused'""",
                (now, job_id),
            )
        return self.get(job_id)

    def is_pause_requested(self, job_id: str) -> bool:
        return self.get(job_id).pause_requested

    def mark_paused(self, job_id: str) -> HistorySyncJob:
        return self.request_pause(job_id)

    def mark_failed(self, job_id: str) -> HistorySyncJob:
        self._set_job_state(job_id, "failed")
        return self.get(job_id)

    def finish(self, job_id: str) -> HistorySyncJob:
        job = self.get(job_id)
        if job.pending_count:
            raise ValueError("history sync job still has pending work")
        self._set_job_state(job_id, "completed")
        return self.get(job_id)

    def recover_interrupted(self) -> None:
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE history_sync_items SET state = 'pending', updated_at = ?
                   WHERE state = 'running'""",
                (now,),
            )
            connection.execute(
                """UPDATE history_sync_jobs
                   SET state = CASE WHEN pause_requested = 1 THEN 'paused' ELSE 'pending' END,
                       updated_at = ?
                   WHERE state = 'running'""",
                (now,),
            )

    def close(self) -> None:
        return None

    def append_repair_audit(self, audit: HistoryRepairAudit) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO history_repair_audits(
                   audit_id, job_id, mode, target_date, started_at, completed_at,
                   source, gap_count_before, coverage_before_percent, written_rows,
                   ready_count, failed_count, skipped_count, coverage_after_percent,
                   final_state, failure_reasons_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    audit.audit_id, audit.job_id, audit.mode, audit.target_date.isoformat(),
                    audit.started_at.isoformat(), audit.completed_at.isoformat(), audit.source,
                    audit.gap_count_before, audit.coverage_before_percent, audit.written_rows,
                    audit.ready_count, audit.failed_count, audit.skipped_count,
                    audit.coverage_after_percent, audit.final_state,
                    json.dumps(audit.failure_reasons, ensure_ascii=False),
                ),
            )

    def repair_audits(self, *, limit: int = 50) -> tuple[HistoryRepairAudit, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM history_repair_audits ORDER BY completed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(
            HistoryRepairAudit(
                audit_id=row["audit_id"], job_id=row["job_id"], mode=row["mode"],
                target_date=row["target_date"], started_at=row["started_at"],
                completed_at=row["completed_at"], source=row["source"],
                gap_count_before=int(row["gap_count_before"]),
                coverage_before_percent=row["coverage_before_percent"],
                written_rows=int(row["written_rows"]), ready_count=int(row["ready_count"]),
                failed_count=int(row["failed_count"]), skipped_count=int(row["skipped_count"]),
                coverage_after_percent=row["coverage_after_percent"],
                final_state=row["final_state"],
                failure_reasons=tuple(json.loads(row["failure_reasons_json"] or "[]")),
            ) for row in rows
        )

    def _set_job_state(self, job_id: str, state: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE history_sync_jobs SET state = ?, updated_at = ? WHERE job_id = ?",
                (state, self._now(), job_id),
            )

    def _now(self) -> str:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("history sync clock must return an aware datetime")
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _job(row: sqlite3.Row) -> HistorySyncJob:
        return HistorySyncJob(
            job_id=row["job_id"],
            mode=row["mode"],
            target_date=row["target_date"],
            state=row["state"],
            pause_requested=bool(row["pause_requested"]),
            total_count=int(row["total_count"] or 0),
            ready_count=int(row["ready_count"] or 0),
            failed_count=int(row["failed_count"] or 0),
            skipped_count=int(row["skipped_count"] or 0),
            pending_count=int(row["pending_count"] or 0),
            tdx_ready_count=int(row["tdx_ready_count"] or 0),
            baidu_ready_count=int(row["baidu_ready_count"] or 0),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _item(row: sqlite3.Row) -> HistorySyncItem:
        return HistorySyncItem(
            job_id=row["job_id"],
            symbol=row["symbol"],
            state=row["state"],
            attempts=int(row["attempts"]),
            source=row["source"],
            written_rows=int(row["written_rows"]),
            error_code=row["error_code"],
            updated_at=row["updated_at"],
        )
