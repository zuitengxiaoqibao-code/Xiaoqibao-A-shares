import asyncio
import hashlib
import hmac
import json
import sqlite3
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


REPORT_API = "https://reportapi.eastmoney.com/report/list"
DATACENTER_API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
STOCK_INFO_API = "https://push2.eastmoney.com/api/qt/stock/get"
STOCK_BLOCKS_API = "https://push2.eastmoney.com/api/qt/slist/get"
INDUSTRY_CONSTITUENTS_API = "https://push2.eastmoney.com/api/qt/clist/get"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class ResearchReportRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publish_date: date
    organization: str
    rating: str | None = None
    industry: str | None = None
    eps_this_year: Decimal | None = None
    eps_next_year: Decimal | None = None
    eps_next_two_year: Decimal | None = None
    pdf_url: str | None = None


class UnlockRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    free_date: date
    stock_type: str | None = None
    shares: Decimal | None = None
    ratio_percent: Decimal | None = None


class MarginRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_date: date
    financing_balance: Decimal | None = None
    financing_buy: Decimal | None = None
    securities_lending_balance: Decimal | None = None
    total_balance: Decimal | None = None


class HolderRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    period: date
    holder_count: Decimal | None = None
    change_ratio_percent: Decimal | None = None
    average_free_shares: Decimal | None = None


class PeerCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    industry: str | None = None
    price: Decimal | None = None
    change_percent: Decimal | None = None
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    market_cap_yi: Decimal | None = None


class ResearchEnrichmentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(pattern=r"^research-enrichment-[0-9a-f]{24}$")
    symbol: str = Field(pattern=r"^\d{6}$")
    observed_at: AwareDatetime
    stock_reports: tuple[ResearchReportRecord, ...] = ()
    industry_reports: tuple[ResearchReportRecord, ...] = ()
    industry_name: str | None = None
    industry_code: str | None = None
    industry_board_code: str | None = None
    peer_candidates: tuple[PeerCandidateRecord, ...] = ()
    unlocks: tuple[UnlockRecord, ...] = ()
    margin: tuple[MarginRecord, ...] = ()
    holders: tuple[HolderRecord, ...] = ()
    sources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ResearchEnrichmentIntegrityError(RuntimeError):
    pass


class EastmoneyResearchEnrichmentSource:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        clock=lambda: datetime.now(timezone.utc),
        monotonic=time.monotonic,
        sleep=asyncio.sleep,
        minimum_interval: float = 1.0,
    ) -> None:
        self.client = client
        self.clock = clock
        self.monotonic = monotonic
        self.sleep = sleep
        self.minimum_interval = minimum_interval
        self._lock = asyncio.Lock()
        self._last_request_at: float | None = None

    async def fetch(self, symbol: str) -> ResearchEnrichmentSnapshot:
        stock_rows = await self._reports(symbol=symbol, q_type="0", page_size=20)
        stock_reports = self._parse_reports(stock_rows)
        industry_code = next((
            str(row.get("indvInduCode") or row.get("industryCode") or "").strip()
            for row in stock_rows
            if row.get("indvInduCode") or row.get("industryCode")
        ), "")
        warnings: list[str] = []
        industry_reports: tuple[ResearchReportRecord, ...] = ()
        if industry_code:
            industry_rows = await self._reports(
                symbol="", q_type="1", page_size=12, industry_code=industry_code,
            )
            industry_reports = self._parse_reports(industry_rows)
        else:
            warnings.append("industry_report_code_unavailable")

        fallback_industry = next((
            str(row.get("indvInduName") or row.get("industryName") or "").strip()
            for row in stock_rows
            if row.get("indvInduName") or row.get("industryName")
        ), "") or None
        try:
            industry_name, industry_board_code, peer_candidates, peer_warning = (
                await self._industry_peers(symbol, fallback_industry)
            )
        except (httpx.HTTPError, OSError, RuntimeError, ValueError):
            industry_name = fallback_industry
            industry_board_code = None
            peer_candidates = ()
            peer_warning = "industry_peer_lookup_unavailable"
        if peer_warning:
            warnings.append(peer_warning)

        unlock_rows = await self._datacenter(
            "RPT_LIFT_STAGE", f'(SECURITY_CODE="{symbol}")', "FREE_DATE", "-1", 30,
        )
        margin_rows = await self._datacenter(
            "RPTA_WEB_RZRQ_GGMX", f'(SCODE="{symbol}")', "DATE", "-1", 30,
        )
        holder_rows = await self._datacenter(
            "RPT_HOLDERNUMLATEST", f'(SECURITY_CODE="{symbol}")', "END_DATE", "-1", 12,
        )
        observed_at = self.clock()
        semantic = {
            "symbol": symbol,
            "observed_at": observed_at.isoformat(),
            "stock_reports": [item.model_dump(mode="json") for item in stock_reports],
            "industry_reports": [item.model_dump(mode="json") for item in industry_reports],
            "industry_name": industry_name,
            "industry_code": industry_code or None,
            "industry_board_code": industry_board_code,
            "peer_candidates": [item.model_dump(mode="json") for item in peer_candidates],
            "unlocks": [item.model_dump(mode="json") for item in self._parse_unlocks(unlock_rows)],
            "margin": [item.model_dump(mode="json") for item in self._parse_margin(margin_rows)],
            "holders": [item.model_dump(mode="json") for item in self._parse_holders(holder_rows)],
            "sources": ["eastmoney-reportapi", "eastmoney-push2", "eastmoney-datacenter"],
            "warnings": warnings,
        }
        encoded = json.dumps(
            semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        content_hash = hashlib.sha256(encoded).hexdigest()
        identity = hashlib.sha256(encoded + observed_at.isoformat().encode("utf-8")).hexdigest()
        return ResearchEnrichmentSnapshot(
            snapshot_id=f"research-enrichment-{identity[:24]}",
            content_hash=content_hash,
            **semantic,
        )

    async def _reports(
        self,
        *,
        symbol: str,
        q_type: str,
        page_size: int,
        industry_code: str = "*",
    ) -> list[dict[str, Any]]:
        payload = await self._get_json(REPORT_API, {
            "industryCode": industry_code, "pageSize": str(page_size), "industry": "*",
            "rating": "*", "ratingChange": "*", "beginTime": "2023-01-01",
            "endTime": "2030-01-01", "pageNo": "1", "fields": "", "qType": q_type,
            "orgCode": "", "code": symbol, "rcode": "", "p": "1",
            "pageNum": "1", "pageNumber": "1",
        }, referer="https://data.eastmoney.com/")
        rows = payload.get("data") if isinstance(payload, dict) else None
        return [row for row in rows or [] if isinstance(row, dict)]

    async def _datacenter(
        self,
        report_name: str,
        filter_value: str,
        sort_columns: str,
        sort_types: str,
        page_size: int,
    ) -> list[dict[str, Any]]:
        payload = await self._get_json(DATACENTER_API, {
            "reportName": report_name, "columns": "ALL", "filter": filter_value,
            "pageNumber": "1", "pageSize": str(page_size),
            "sortColumns": sort_columns, "sortTypes": sort_types,
            "source": "WEB", "client": "WEB",
        }, referer="https://data.eastmoney.com/")
        result = payload.get("result") if isinstance(payload, dict) else None
        rows = result.get("data") if isinstance(result, dict) else None
        return [row for row in rows or [] if isinstance(row, dict)]

    async def _industry_peers(
        self,
        symbol: str,
        fallback_industry: str | None,
    ) -> tuple[str | None, str | None, tuple[PeerCandidateRecord, ...], str | None]:
        secid = f"{1 if symbol.startswith('6') else 0}.{symbol}"
        info_payload = await self._get_json(STOCK_INFO_API, {
            "fltt": "2", "invt": "2", "fields": "f57,f127", "secid": secid,
        }, referer="https://quote.eastmoney.com/")
        info = info_payload.get("data") if isinstance(info_payload, dict) else None
        industry_name = str((info or {}).get("f127") or fallback_industry or "").strip() or None

        blocks_payload = await self._get_json(STOCK_BLOCKS_API, {
            "fltt": "2", "invt": "2", "secid": secid, "spt": "3",
            "pi": "0", "pz": "200", "po": "1", "fields": "f12,f14",
        }, referer="https://quote.eastmoney.com/")
        diff = (blocks_payload.get("data") or {}).get("diff") if isinstance(blocks_payload, dict) else None
        block_rows = list(diff.values()) if isinstance(diff, dict) else diff or []
        industry_board_code = next((
            str(row.get("f12") or "").strip()
            for row in block_rows
            if isinstance(row, dict)
            and industry_name is not None
            and str(row.get("f14") or "").strip() == industry_name
            and str(row.get("f12") or "").startswith("BK")
        ), "") or None
        if industry_board_code is None:
            return industry_name, None, (), "industry_board_code_unavailable"

        peer_payload = await self._get_json(INDUSTRY_CONSTITUENTS_API, {
            "pn": "1", "pz": "30", "po": "1", "np": "1", "fltt": "2",
            "invt": "2", "fid": "f20", "fs": f"b:{industry_board_code}",
            "fields": "f12,f14,f2,f3,f9,f20,f23",
        }, referer="https://quote.eastmoney.com/")
        peer_diff = (peer_payload.get("data") or {}).get("diff") if isinstance(peer_payload, dict) else None
        peer_rows = list(peer_diff.values()) if isinstance(peer_diff, dict) else peer_diff or []
        parsed: list[PeerCandidateRecord] = []
        for row in peer_rows:
            if not isinstance(row, dict):
                continue
            peer_symbol = str(row.get("f12") or "").strip()
            peer_name = str(row.get("f14") or "").strip()
            if len(peer_symbol) != 6 or not peer_symbol.isdigit() or not peer_name:
                continue
            market_cap = _decimal(row.get("f20"))
            parsed.append(PeerCandidateRecord(
                symbol=peer_symbol,
                name=peer_name,
                industry=industry_name,
                price=_decimal(row.get("f2")),
                change_percent=_decimal(row.get("f3")),
                pe_ttm=_decimal(row.get("f9")),
                pb=_decimal(row.get("f23")),
                market_cap_yi=(market_cap / Decimal("100000000") if market_cap is not None else None),
            ))
        return industry_name, industry_board_code, tuple(parsed), None if parsed else "industry_peer_sample_unavailable"

    async def _get_json(self, url: str, params: dict[str, str], *, referer: str) -> Any:
        async with self._lock:
            now = self.monotonic()
            if self._last_request_at is not None:
                wait = self.minimum_interval - (now - self._last_request_at)
                if wait > 0:
                    await self.sleep(wait)
            self._last_request_at = self.monotonic()
            response = await self.client.get(
                url, params=params,
                headers={"User-Agent": USER_AGENT, "Referer": referer},
            )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_reports(rows: list[dict[str, Any]]) -> tuple[ResearchReportRecord, ...]:
        parsed: list[ResearchReportRecord] = []
        for row in rows:
            info_code = str(row.get("infoCode") or "").strip()
            title = str(row.get("title") or "").strip()
            publish_date = _date(row.get("publishDate"))
            if not info_code or not title or publish_date is None:
                continue
            parsed.append(ResearchReportRecord(
                report_id=info_code,
                title=title,
                publish_date=publish_date,
                organization=str(row.get("orgSName") or "未知机构").strip(),
                rating=str(row.get("emRatingName") or "").strip() or None,
                industry=str(row.get("indvInduName") or row.get("industryName") or "").strip() or None,
                eps_this_year=_decimal(row.get("predictThisYearEps")),
                eps_next_year=_decimal(row.get("predictNextYearEps")),
                eps_next_two_year=_decimal(row.get("predictNextTwoYearEps")),
                pdf_url=f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf",
            ))
        return tuple(parsed)

    @staticmethod
    def _parse_unlocks(rows: list[dict[str, Any]]) -> tuple[UnlockRecord, ...]:
        return tuple(UnlockRecord(
            free_date=free_date,
            stock_type=str(row.get("LIMITED_STOCK_TYPE") or "").strip() or None,
            shares=_decimal(row.get("FREE_SHARES_NUM")),
            ratio_percent=_decimal(row.get("FREE_RATIO")),
        ) for row in rows if (free_date := _date(row.get("FREE_DATE"))) is not None)

    @staticmethod
    def _parse_margin(rows: list[dict[str, Any]]) -> tuple[MarginRecord, ...]:
        return tuple(MarginRecord(
            trade_date=trade_date,
            financing_balance=_decimal(row.get("RZYE")),
            financing_buy=_decimal(row.get("RZMRE")),
            securities_lending_balance=_decimal(row.get("RQYE")),
            total_balance=_decimal(row.get("RZRQYE")),
        ) for row in rows if (trade_date := _date(row.get("DATE"))) is not None)

    @staticmethod
    def _parse_holders(rows: list[dict[str, Any]]) -> tuple[HolderRecord, ...]:
        return tuple(HolderRecord(
            period=period,
            holder_count=_decimal(row.get("HOLDER_NUM")),
            change_ratio_percent=_decimal(row.get("HOLDER_NUM_RATIO")),
            average_free_shares=_decimal(row.get("AVG_FREE_SHARES")),
        ) for row in rows if (period := _date(row.get("END_DATE"))) is not None)


class ResearchEnrichmentRepository:
    def __init__(self, database: str | Path) -> None:
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS research_enrichment_snapshots (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          symbol TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          canonical_hash TEXT NOT NULL,
          payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_research_enrichment_symbol
        ON research_enrichment_snapshots(symbol, observed_at, sequence);
        CREATE TRIGGER IF NOT EXISTS reject_update_research_enrichment
        BEFORE UPDATE ON research_enrichment_snapshots
        BEGIN SELECT RAISE(ABORT, 'append-only research enrichment'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_research_enrichment
        BEFORE DELETE ON research_enrichment_snapshots
        BEGIN SELECT RAISE(ABORT, 'append-only research enrichment'); END;
        """)

    def append(self, snapshot: ResearchEnrichmentSnapshot) -> str:
        payload = snapshot.model_dump_json()
        canonical_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT canonical_hash FROM research_enrichment_snapshots WHERE snapshot_id=?",
                (snapshot.snapshot_id,),
            ).fetchone()
            if existing is not None:
                if not hmac.compare_digest(existing["canonical_hash"], canonical_hash):
                    raise ResearchEnrichmentIntegrityError("research enrichment id collision")
                return snapshot.snapshot_id
            self.connection.execute(
                "INSERT INTO research_enrichment_snapshots "
                "(snapshot_id,symbol,observed_at,canonical_hash,payload) VALUES(?,?,?,?,?)",
                (snapshot.snapshot_id, snapshot.symbol, snapshot.observed_at.isoformat(), canonical_hash, payload),
            )
        return snapshot.snapshot_id

    def latest(self, symbol: str) -> ResearchEnrichmentSnapshot | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM research_enrichment_snapshots WHERE symbol=? "
                "ORDER BY observed_at DESC, sequence DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        computed = hashlib.sha256(row["payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(computed, row["canonical_hash"]):
            raise ResearchEnrichmentIntegrityError("research enrichment integrity failure")
        return ResearchEnrichmentSnapshot.model_validate_json(row["payload"])

    def close(self) -> None:
        with self._lock:
            self.connection.close()
