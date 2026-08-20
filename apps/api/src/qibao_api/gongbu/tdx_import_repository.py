from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from qibao_api.contracts.tdx_import import TdxImportError, TdxImportJob


class TdxImportRepository:
    def __init__(self, database_path: Path, *, clock: Callable[[], datetime] | None = None) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tdx_import_jobs (
                    job_id TEXT PRIMARY KEY, state TEXT NOT NULL, stage TEXT NOT NULL,
                    paths_json TEXT NOT NULL, total_files INTEGER NOT NULL DEFAULT 0,
                    processed_files INTEGER NOT NULL DEFAULT 0, imported_rows INTEGER NOT NULL DEFAULT 0,
                    replaced_rows INTEGER NOT NULL DEFAULT 0, skipped_rows INTEGER NOT NULL DEFAULT 0,
                    failed_files INTEGER NOT NULL DEFAULT 0, current_file TEXT,
                    latest_trade_date TEXT, errors_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finished_at TEXT
                )"""
            )

    def create_job(self, paths: tuple[str, ...]) -> TdxImportJob:
        if not paths:
            raise ValueError("at least one local TDX path is required")
        now = self._now()
        job_id = f"tdx-import-{uuid4().hex}"
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO tdx_import_jobs (job_id,state,stage,paths_json,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (job_id, "pending", "queued", json.dumps(paths, ensure_ascii=False), now, now),
            )
        return self.get(job_id)

    def current(self) -> TdxImportJob | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT job_id FROM tdx_import_jobs ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        return self.get(row["job_id"]) if row else None

    def get(self, job_id: str) -> TdxImportJob:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM tdx_import_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._model(row)

    def update(self, job_id: str, **changes) -> TdxImportJob:
        current = self.get(job_id)
        values = {
            "state": changes.get("state", current.state),
            "stage": changes.get("stage", current.stage),
            "total_files": changes.get("total_files", current.total_files),
            "processed_files": changes.get("processed_files", current.processed_files),
            "imported_rows": changes.get("imported_rows", current.imported_rows),
            "replaced_rows": changes.get("replaced_rows", current.replaced_rows),
            "skipped_rows": changes.get("skipped_rows", current.skipped_rows),
            "failed_files": changes.get("failed_files", current.failed_files),
            "current_file": changes.get("current_file", current.current_file),
            "latest_trade_date": changes.get("latest_trade_date", current.latest_trade_date),
            "errors": changes.get("errors", current.errors),
        }
        total = int(values["total_files"] or 0)
        processed = min(total, int(values["processed_files"] or 0)) if total else 0
        now = self._now()
        finished = now if values["state"] in {"completed", "failed", "paused"} else current.finished_at
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE tdx_import_jobs SET state=?,stage=?,total_files=?,processed_files=?,
                   imported_rows=?,replaced_rows=?,skipped_rows=?,failed_files=?,current_file=?,
                   latest_trade_date=?,errors_json=?,updated_at=?,finished_at=? WHERE job_id=?""",
                (values["state"], values["stage"], total, processed, values["imported_rows"],
                 values["replaced_rows"], values["skipped_rows"], values["failed_files"],
                 values["current_file"], values["latest_trade_date"],
                 json.dumps([item.model_dump(mode="json") for item in values["errors"]], ensure_ascii=False),
                 now, finished, job_id),
            )
        return self.get(job_id)

    def recover_interrupted(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE tdx_import_jobs
                   SET state='paused', stage='restart_paused', updated_at=?, finished_at=?
                   WHERE state IN ('pending', 'running')""",
                (self._now(), self._now()),
            )

    def update_existing(self, job_id: str, **changes) -> TdxImportJob:
        return self.update(job_id, **changes)

    def close(self) -> None:
        return None

    def _now(self) -> str:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("TDX import clock must return an aware datetime")
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _model(row: sqlite3.Row) -> TdxImportJob:
        total = int(row["total_files"] or 0)
        processed = min(total, int(row["processed_files"] or 0)) if total else 0
        errors = tuple(TdxImportError.model_validate(item) for item in json.loads(row["errors_json"] or "[]"))
        return TdxImportJob(
            job_id=row["job_id"], state=row["state"], stage=row["stage"],
            paths=tuple(json.loads(row["paths_json"])), total_files=total,
            processed_files=processed, imported_rows=int(row["imported_rows"] or 0),
            replaced_rows=int(row["replaced_rows"] or 0), skipped_rows=int(row["skipped_rows"] or 0),
            failed_files=int(row["failed_files"] or 0), current_file=row["current_file"],
            latest_trade_date=row["latest_trade_date"],
            percent=round(processed / total * 100, 2) if total else 0,
            errors=errors, created_at=row["created_at"], updated_at=row["updated_at"],
            finished_at=row["finished_at"],
        )
