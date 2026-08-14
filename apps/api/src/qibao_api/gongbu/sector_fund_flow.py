import asyncio
import hashlib
import hmac
import json
import sqlite3
import threading
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


EASTMONEY_SECTOR_FLOW_URL = "https://push2.eastmoney.com/api/qt/clist/get"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
YI = Decimal("100000000")
TWO_PLACES = Decimal("0.01")


class SectorFundFlowHttpResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int
    body: bytes


SectorFundFlowTransport = Callable[
    [str, dict[str, str], dict[str, str]],
    Awaitable[SectorFundFlowHttpResponse],
]


class SectorFundFlowItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    sector_code: str = Field(pattern=r"^BK\d{4}$")
    sector_name: str = Field(min_length=1)
    main_net_yi: Decimal
    large_net_yi: Decimal | None = None
    super_net_yi: Decimal | None = None


class SectorFundFlowSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(pattern=r"^sector-flow-[0-9a-f]{24}$")
    observed_at: AwareDatetime
    items: tuple[SectorFundFlowItem, ...] = Field(min_length=1)
    source: str = "eastmoney-sector-fund-flow"
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_snapshot: bytes = Field(min_length=1)


class SectorFundFlowIntegrityError(RuntimeError):
    pass


def _optional_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _yi(value: Any) -> Decimal | None:
    parsed = _optional_decimal(value)
    if parsed is None:
        return None
    return (parsed / YI).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class EastmoneySectorFundFlowSource:
    def __init__(
        self,
        transport: SectorFundFlowTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock=lambda: datetime.now(timezone.utc),
        monotonic=time.monotonic,
        sleep=asyncio.sleep,
        minimum_interval: float = 1.0,
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock
        self.monotonic = monotonic
        self.sleep = sleep
        self.minimum_interval = minimum_interval
        self._last_request_at: float | None = None
        self._request_lock = asyncio.Lock()

    async def fetch(self) -> SectorFundFlowSnapshot:
        params = {
            "pn": "1",
            "pz": "200",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f62",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f62,f66,f72",
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://data.eastmoney.com/bkzj/",
        }
        async with self._request_lock:
            await self._wait_for_rate_limit()
            response = await self._request(EASTMONEY_SECTOR_FLOW_URL, params, headers)
        if response.status_code != 200:
            raise OSError(f"Eastmoney sector fund-flow status {response.status_code}")
        try:
            payload = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Eastmoney sector fund-flow response is not valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("Eastmoney sector fund-flow response is not an object")
        items = self._parse_items(payload)
        if not items:
            raise ValueError("Eastmoney sector net flow is unavailable")
        semantic = [item.model_dump(mode="json") for item in items]
        semantic_bytes = json.dumps(
            semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        content_hash = hashlib.sha256(semantic_bytes).hexdigest()
        raw_snapshot = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        observed_at = self.clock()
        identity = hashlib.sha256(
            (content_hash + observed_at.astimezone(timezone.utc).isoformat()).encode("utf-8")
        ).hexdigest()
        return SectorFundFlowSnapshot(
            snapshot_id=f"sector-flow-{identity[:24]}",
            observed_at=observed_at,
            items=items,
            content_hash=content_hash,
            raw_snapshot=raw_snapshot,
        )

    @staticmethod
    def _parse_items(payload: dict[str, Any]) -> tuple[SectorFundFlowItem, ...]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        diff = data.get("diff") or []
        rows = diff.values() if isinstance(diff, dict) else diff
        if not isinstance(rows, (list, tuple)) and not hasattr(rows, "__iter__"):
            return ()
        items: list[SectorFundFlowItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("f12") or "").strip().upper()
            name = str(row.get("f14") or "").strip()
            main_net = _yi(row.get("f62"))
            if not code.startswith("BK") or len(code) != 6 or not name or main_net is None:
                continue
            items.append(SectorFundFlowItem(
                sector_code=code,
                sector_name=name,
                main_net_yi=main_net,
                super_net_yi=_yi(row.get("f66")),
                large_net_yi=_yi(row.get("f72")),
            ))
        return tuple(sorted(items, key=lambda item: abs(item.main_net_yi), reverse=True))

    async def _wait_for_rate_limit(self) -> None:
        now = self.monotonic()
        if self._last_request_at is not None:
            remaining = self.minimum_interval - (now - self._last_request_at)
            if remaining > 0:
                await self.sleep(remaining)
                now = self.monotonic()
        self._last_request_at = now

    async def _request(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> SectorFundFlowHttpResponse:
        if self.transport is not None:
            return await self.transport(url, params, headers)
        if self.client is not None:
            result = await self.client.get(url, params=params, headers=headers)
            return SectorFundFlowHttpResponse(status_code=result.status_code, body=result.content)
        async with httpx.AsyncClient(timeout=15) as client:
            result = await client.get(url, params=params, headers=headers)
            return SectorFundFlowHttpResponse(status_code=result.status_code, body=result.content)


class SectorFundFlowRepository:
    def __init__(self, database: str | Path) -> None:
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS sector_fund_flow_snapshots (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          observed_at TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          canonical_hash TEXT NOT NULL,
          payload TEXT NOT NULL,
          raw_snapshot BLOB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_sector_fund_flow_observed
        ON sector_fund_flow_snapshots(observed_at, sequence);
        CREATE TRIGGER IF NOT EXISTS reject_update_sector_fund_flow_snapshots
        BEFORE UPDATE ON sector_fund_flow_snapshots
        BEGIN SELECT RAISE(ABORT, 'append-only sector fund-flow snapshots'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_sector_fund_flow_snapshots
        BEFORE DELETE ON sector_fund_flow_snapshots
        BEGIN SELECT RAISE(ABORT, 'append-only sector fund-flow snapshots'); END;
        """)

    def append(self, snapshot: SectorFundFlowSnapshot) -> str:
        payload = json.dumps(
            snapshot.model_dump(mode="json", exclude={"raw_snapshot"}),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        canonical_hash = hashlib.sha256(
            payload.encode("utf-8") + b"\0" + snapshot.raw_snapshot
        ).hexdigest()
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT canonical_hash FROM sector_fund_flow_snapshots WHERE snapshot_id=?",
                (snapshot.snapshot_id,),
            ).fetchone()
            if existing is not None:
                if not hmac.compare_digest(existing["canonical_hash"], canonical_hash):
                    raise SectorFundFlowIntegrityError("sector fund-flow snapshot id collision")
                return snapshot.snapshot_id
            self.connection.execute(
                "INSERT INTO sector_fund_flow_snapshots "
                "(snapshot_id, observed_at, content_hash, canonical_hash, payload, raw_snapshot) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    snapshot.observed_at.astimezone(timezone.utc).isoformat(),
                    snapshot.content_hash,
                    canonical_hash,
                    payload,
                    snapshot.raw_snapshot,
                ),
            )
        return snapshot.snapshot_id

    def latest(self) -> SectorFundFlowSnapshot | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM sector_fund_flow_snapshots ORDER BY observed_at DESC, sequence DESC LIMIT 1"
            ).fetchone()
        return self._verified(row) if row is not None else None

    def history(self, *, limit: int = 60) -> tuple[SectorFundFlowSnapshot, ...]:
        if limit <= 0:
            return ()
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM sector_fund_flow_snapshots ORDER BY observed_at DESC, sequence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(self._verified(row) for row in reversed(rows))

    def _verified(self, row: sqlite3.Row) -> SectorFundFlowSnapshot:
        canonical_hash = hashlib.sha256(
            row["payload"].encode("utf-8") + b"\0" + row["raw_snapshot"]
        ).hexdigest()
        if not hmac.compare_digest(canonical_hash, row["canonical_hash"]):
            raise SectorFundFlowIntegrityError("sector fund-flow snapshot failed integrity check")
        payload = json.loads(row["payload"])
        payload["raw_snapshot"] = row["raw_snapshot"]
        snapshot = SectorFundFlowSnapshot.model_validate(payload)
        if not hmac.compare_digest(snapshot.content_hash, row["content_hash"]):
            raise SectorFundFlowIntegrityError("sector fund-flow content hash differs")
        return snapshot

    def count(self) -> int:
        with self._lock:
            return int(self.connection.execute(
                "SELECT COUNT(*) FROM sector_fund_flow_snapshots"
            ).fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self.connection.close()


class SectorFundFlowService:
    def __init__(
        self,
        source: EastmoneySectorFundFlowSource,
        repository: SectorFundFlowRepository,
    ) -> None:
        self.source = source
        self.repository = repository

    async def sync(self) -> SectorFundFlowSnapshot:
        snapshot = await self.source.fetch()
        self.repository.append(snapshot)
        return snapshot
