import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from qibao_api.contracts.first_limit_up import FirstLimitUpCandidate


@dataclass(frozen=True)
class FirstLimitUpScan:
    scan_date: date
    updated_at: datetime
    candidates: tuple[FirstLimitUpCandidate, ...]
    universe_count: int
    history_eligible_count: int
    scan_coverage_count: int
    coverage_complete: bool


class FirstLimitUpRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS first_limit_up_candidates (
                    symbol TEXT NOT NULL,
                    limit_up_date TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, limit_up_date)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS first_limit_up_scans (
                    scan_date TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def upsert_many(self, candidates: list[FirstLimitUpCandidate]) -> None:
        if not candidates:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                item.symbol,
                item.limit_up_date.isoformat(),
                item.model_dump_json(),
                now,
            )
            for item in candidates
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO first_limit_up_candidates
                    (symbol, limit_up_date, payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol, limit_up_date) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                rows,
            )

    def list_recent(
        self, limit: int = 100, *, as_of: date | None = None
    ) -> list[FirstLimitUpCandidate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload
                FROM first_limit_up_candidates
                WHERE (? IS NULL OR limit_up_date <= ?)
                ORDER BY limit_up_date DESC, symbol ASC
                LIMIT ?
                """,
                [
                    as_of.isoformat() if as_of else None,
                    as_of.isoformat() if as_of else None,
                    limit,
                ],
            ).fetchall()
        return [FirstLimitUpCandidate.model_validate_json(row["payload"]) for row in rows]

    def save_scan(
        self,
        scan_date: date,
        candidates: list[FirstLimitUpCandidate],
        *,
        universe_count: int,
        history_eligible_count: int,
        scan_coverage_count: int,
        coverage_complete: bool,
    ) -> None:
        payload = json.dumps(
            {
                "candidates": [item.model_dump(mode="json") for item in candidates],
                "universe_count": universe_count,
                "history_eligible_count": history_eligible_count,
                "scan_coverage_count": scan_coverage_count,
                "coverage_complete": coverage_complete,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO first_limit_up_scans (scan_date, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(scan_date) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (scan_date.isoformat(), payload, datetime.now(timezone.utc).isoformat()),
            )

    def latest_scan(
        self, *, as_of: date
    ) -> FirstLimitUpScan | None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT scan_date, payload, updated_at
                FROM first_limit_up_scans
                WHERE scan_date <= ?
                ORDER BY scan_date DESC
                """,
                (as_of.isoformat(),),
            ).fetchall()
        required_metadata = {
            "candidates",
            "universe_count",
            "history_eligible_count",
            "scan_coverage_count",
            "coverage_complete",
        }
        for row in rows:
            try:
                payload = json.loads(row["payload"])
                if not isinstance(payload, dict) or not required_metadata.issubset(payload):
                    continue
                candidates = tuple(
                    FirstLimitUpCandidate.model_validate(item)
                    for item in payload["candidates"]
                )
                return FirstLimitUpScan(
                    scan_date=date.fromisoformat(row["scan_date"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    candidates=candidates,
                    universe_count=int(payload["universe_count"]),
                    history_eligible_count=int(payload["history_eligible_count"]),
                    scan_coverage_count=int(payload["scan_coverage_count"]),
                    coverage_complete=bool(payload["coverage_complete"]),
                )
            except (TypeError, ValueError):
                continue
        return None
