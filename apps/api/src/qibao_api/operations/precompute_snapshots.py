from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable, Literal, Mapping
from uuid import uuid4


PRECOMPUTE_DOMAINS = ("overview", "quant", "research")
AttemptStatus = Literal["complete", "partial", "failed"]


class PrecomputeSnapshotConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrecomputedSnapshot:
    snapshot_id: str
    domain: str
    trade_date: date
    data_version: str
    status: AttemptStatus
    payload: dict | None
    content_hash: str | None
    source: str
    generated_at: datetime
    compute_ms: int
    limitations: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "domain": self.domain,
            "trade_date": self.trade_date.isoformat(),
            "data_version": self.data_version,
            "status": self.status,
            "payload": self.payload,
            "content_hash": self.content_hash,
            "source": self.source,
            "generated_at": self.generated_at.isoformat(),
            "compute_ms": self.compute_ms,
            "limitations": list(self.limitations),
        }


class PrecomputeSnapshotStore:
    def __init__(self, database: Path) -> None:
        self.database = database
        database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS precompute_attempt (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              snapshot_id TEXT NOT NULL UNIQUE,
              domain TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              data_version TEXT NOT NULL,
              status TEXT NOT NULL,
              payload_json TEXT,
              content_hash TEXT,
              source TEXT NOT NULL,
              generated_at TEXT NOT NULL,
              compute_ms INTEGER NOT NULL,
              limitations_json TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS precompute_complete_key
              ON precompute_attempt(domain, trade_date, data_version)
              WHERE status = 'complete';
            CREATE TRIGGER IF NOT EXISTS reject_update_precompute_attempt
              BEFORE UPDATE ON precompute_attempt
              BEGIN SELECT RAISE(ABORT, 'append-only precompute snapshots'); END;
            CREATE TRIGGER IF NOT EXISTS reject_delete_precompute_attempt
              BEFORE DELETE ON precompute_attempt
              BEGIN SELECT RAISE(ABORT, 'append-only precompute snapshots'); END;
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _validate(domain: str, trade_date: date, data_version: str) -> None:
        if domain not in PRECOMPUTE_DOMAINS:
            raise ValueError("unknown precompute domain")
        if not isinstance(trade_date, date):
            raise ValueError("precompute snapshot requires a trading date")
        if not data_version.strip():
            raise ValueError("precompute snapshot requires a data version")

    def append_complete(
        self,
        domain: str,
        *,
        trade_date: date,
        data_version: str,
        payload: Mapping,
        source: str,
        generated_at: datetime,
        compute_ms: int,
    ) -> PrecomputedSnapshot:
        self._validate(domain, trade_date, data_version)
        canonical = json.dumps(
            dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            existing = connection.execute(
                """SELECT * FROM precompute_attempt
                WHERE domain=? AND trade_date=? AND data_version=? AND status='complete'""",
                (domain, trade_date.isoformat(), data_version),
            ).fetchone()
            if existing is not None:
                if existing["content_hash"] != content_hash:
                    raise PrecomputeSnapshotConflictError(
                        "one data version cannot identify different snapshot content"
                    )
                return self._row(existing)
            snapshot_id = f"precompute-{domain}-{uuid4().hex}"
            connection.execute(
                """INSERT INTO precompute_attempt(
                snapshot_id,domain,trade_date,data_version,status,payload_json,
                content_hash,source,generated_at,compute_ms,limitations_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    snapshot_id, domain, trade_date.isoformat(), data_version,
                    "complete", canonical, content_hash, source,
                    generated_at.isoformat(), max(0, compute_ms), "[]",
                ),
            )
            row = connection.execute(
                "SELECT * FROM precompute_attempt WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
        return self._row(row)

    def append_attempt(
        self,
        domain: str,
        *,
        trade_date: date,
        data_version: str,
        status: Literal["partial", "failed"],
        source: str,
        generated_at: datetime,
        compute_ms: int,
        limitations: tuple[str, ...],
    ) -> PrecomputedSnapshot:
        self._validate(domain, trade_date, data_version)
        if status not in {"partial", "failed"}:
            raise ValueError("non-complete attempt must be partial or failed")
        if not limitations:
            raise ValueError("incomplete precompute attempt requires limitations")
        snapshot_id = f"precompute-{domain}-{uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO precompute_attempt(
                snapshot_id,domain,trade_date,data_version,status,payload_json,
                content_hash,source,generated_at,compute_ms,limitations_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    snapshot_id, domain, trade_date.isoformat(), data_version,
                    status, None, None, source, generated_at.isoformat(),
                    max(0, compute_ms), json.dumps(limitations, ensure_ascii=False),
                ),
            )
            row = connection.execute(
                "SELECT * FROM precompute_attempt WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
        return self._row(row)

    def latest_complete(
        self,
        domain: str,
        *,
        trade_date: date | None = None,
        data_version: str | None = None,
    ) -> PrecomputedSnapshot | None:
        if domain not in PRECOMPUTE_DOMAINS:
            raise ValueError("unknown precompute domain")
        clauses = ["domain=?", "status='complete'"]
        values: list[str] = [domain]
        if trade_date is not None:
            clauses.append("trade_date=?")
            values.append(trade_date.isoformat())
        if data_version is not None:
            clauses.append("data_version=?")
            values.append(data_version)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT * FROM precompute_attempt WHERE {' AND '.join(clauses)} "
                "ORDER BY sequence DESC LIMIT 1",
                values,
            ).fetchone()
        return self._row(row) if row is not None else None

    def summary(self) -> list[dict]:
        result = []
        with self._connect() as connection:
            for domain in PRECOMPUTE_DOMAINS:
                latest = connection.execute(
                    "SELECT * FROM precompute_attempt WHERE domain=? ORDER BY sequence DESC LIMIT 1",
                    (domain,),
                ).fetchone()
                complete = connection.execute(
                    """SELECT * FROM precompute_attempt
                    WHERE domain=? AND status='complete' ORDER BY sequence DESC LIMIT 1""",
                    (domain,),
                ).fetchone()
                attempt_count = connection.execute(
                    "SELECT COUNT(*) FROM precompute_attempt WHERE domain=?", (domain,)
                ).fetchone()[0]
                result.append({
                    "domain": domain,
                    "latest_attempt_status": latest["status"] if latest else "unavailable",
                    "latest_attempt_data_version": latest["data_version"] if latest else None,
                    "served_data_version": complete["data_version"] if complete else None,
                    "served_trade_date": complete["trade_date"] if complete else None,
                    "served_generated_at": complete["generated_at"] if complete else None,
                    "served_content_hash": complete["content_hash"] if complete else None,
                    "attempt_count": int(attempt_count),
                    "limitations": json.loads(latest["limitations_json"]) if latest else [],
                })
        return result

    @staticmethod
    def _row(row: sqlite3.Row) -> PrecomputedSnapshot:
        return PrecomputedSnapshot(
            snapshot_id=row["snapshot_id"],
            domain=row["domain"],
            trade_date=date.fromisoformat(row["trade_date"]),
            data_version=row["data_version"],
            status=row["status"],
            payload=json.loads(row["payload_json"]) if row["payload_json"] else None,
            content_hash=row["content_hash"],
            source=row["source"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            compute_ms=int(row["compute_ms"]),
            limitations=tuple(json.loads(row["limitations_json"])),
        )


class PrecomputeSnapshotService:
    def __init__(
        self,
        store: PrecomputeSnapshotStore,
        *,
        executor,
        performance_store=None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.executor = executor
        self.performance_store = performance_store
        self.clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._in_flight: set[tuple[str, date, str]] = set()

    def serve_or_schedule(
        self,
        domain: str,
        *,
        trade_date: date,
        data_version: str,
        source: str,
        compute: Callable[[], Mapping],
    ) -> dict:
        started = time.perf_counter()
        exact = self.store.latest_complete(
            domain, trade_date=trade_date, data_version=data_version
        )
        if exact is not None:
            self._record(domain, started, True, True)
            return {"snapshot": exact, "cache_state": "exact", "refresh_scheduled": False}
        previous = self.store.latest_complete(domain)
        key = (domain, trade_date, data_version)
        with self._lock:
            schedule = key not in self._in_flight
            if schedule:
                self._in_flight.add(key)
                self.executor.submit(
                    self._refresh, key, source, compute
                )
        self._record(domain, started, previous is not None, True)
        return {
            "snapshot": previous,
            "cache_state": "stale" if previous is not None else "miss",
            "refresh_scheduled": schedule,
        }

    def _refresh(
        self,
        key: tuple[str, date, str],
        source: str,
        compute: Callable[[], Mapping],
    ) -> None:
        domain, trade_date, data_version = key
        started = time.perf_counter()
        try:
            payload = compute()
            self.store.append_complete(
                domain,
                trade_date=trade_date,
                data_version=data_version,
                payload=payload,
                source=source,
                generated_at=self.clock(),
                compute_ms=round((time.perf_counter() - started) * 1000),
            )
            self._record(domain, started, False, True)
        except Exception as error:
            self.store.append_attempt(
                domain,
                trade_date=trade_date,
                data_version=data_version,
                status="failed",
                source=source,
                generated_at=self.clock(),
                compute_ms=round((time.perf_counter() - started) * 1000),
                limitations=(type(error).__name__,),
            )
            self._record(domain, started, False, False)
        finally:
            with self._lock:
                self._in_flight.discard(key)

    def _record(self, domain: str, started: float, cache_hit: bool, success: bool) -> None:
        if self.performance_store is None:
            return
        self.performance_store.record(
            "precompute",
            domain,
            latency_ms=round((time.perf_counter() - started) * 1000),
            success=success,
            cache_hit=cache_hit,
        )
