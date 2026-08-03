import json
import math
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from qibao_api.a_shares.instrument_directory import (
    NON_EQUITY_IDENTIFIERS,
    AShareInstrument,
)
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.gongbu.tencent_quotes import market_prefix


EASTMONEY_A_SHARE_UNIVERSE_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_A_SHARE_UNIVERSE_SOURCE = "eastmoney-a-share-universe"
EASTMONEY_A_SHARE_UNIVERSE_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
CNINFO_A_SHARE_UNIVERSE_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_A_SHARE_UNIVERSE_SOURCE = "cninfo-a-share-universe"
MINIMUM_COMPLETE_A_SHARE_UNIVERSE_COUNT = 4_000
REQUIRED_A_SHARE_EXCHANGES = frozenset({"sh", "sz"})
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class RawUniverseResponse:
    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self.body = body


UniverseTransport = Callable[
    [str, dict[str, str], dict[str, str]], Awaitable[RawUniverseResponse]
]


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Eastmoney A-share universe response is incomplete")
    diff = data.get("diff")
    if isinstance(diff, dict):
        values = diff.values()
    elif isinstance(diff, list):
        values = diff
    else:
        values = ()
    return [row for row in values if isinstance(row, dict)]


def parse_eastmoney_a_share_universe(
    raw_payload: bytes, *, observed_at: datetime
) -> tuple[AShareInstrument, ...]:
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
        rows = _rows(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("Eastmoney"):
            raise
        raise ValueError("Eastmoney A-share universe response is incomplete") from exc

    instruments: dict[str, AShareInstrument] = {}
    for row in rows:
        code = str(row.get("f12") or "")
        try:
            validate_a_share_code(code)
        except ValueError:
            continue
        if code in NON_EQUITY_IDENTIFIERS:
            continue
        name = str(row.get("f14") or "").strip()
        if not name:
            continue
        instrument = AShareInstrument(
            symbol=code,
            name=name,
            exchange=market_prefix(code),
            observed_at=observed_at,
            quote_quality="unavailable",
        )
        instruments[code] = instrument
    return tuple(instruments[code] for code in sorted(instruments))


def parse_cninfo_a_share_universe(
    raw_payload: bytes, *, observed_at: datetime
) -> tuple[AShareInstrument, ...]:
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
        rows = payload.get("stockList")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise ValueError("Cninfo A-share universe response is incomplete") from exc
    if not isinstance(rows, list):
        raise ValueError("Cninfo A-share universe response is incomplete")

    instruments: dict[str, AShareInstrument] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("category") != "A股":
            continue
        code = str(row.get("code") or "")
        try:
            validate_a_share_code(code)
        except ValueError:
            continue
        if code in NON_EQUITY_IDENTIFIERS:
            continue
        name = str(row.get("zwjc") or "").strip()
        if not name or name.endswith("退") or "退市" in name:
            continue
        instruments[code] = AShareInstrument(
            symbol=code,
            name=name,
            exchange=market_prefix(code),
            observed_at=observed_at,
            quote_quality="unavailable",
        )
    return tuple(instruments[code] for code in sorted(instruments))


class EastmoneyAShareUniverseSource:
    source_name = EASTMONEY_A_SHARE_UNIVERSE_SOURCE

    def __init__(
        self,
        transport: UniverseTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        page_size: int = 200,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        self.transport = transport
        self.client = client
        self.clock = clock
        self.page_size = page_size

    async def fetch(self) -> tuple[AShareInstrument, ...]:
        observed_at = self.clock()
        first = await self._request_page(1)
        if first.status_code != 200:
            raise ValueError(f"Eastmoney A-share universe status {first.status_code}")
        try:
            payload = json.loads(first.body.decode("utf-8"))
            total = int((payload.get("data") or {}).get("total") or 0)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Eastmoney A-share universe response is incomplete") from exc
        bodies = [first.body]
        pages = max(1, math.ceil(total / self.page_size))
        for page in range(2, pages + 1):
            response = await self._request_page(page)
            if response.status_code != 200:
                raise ValueError(f"Eastmoney A-share universe status {response.status_code}")
            bodies.append(response.body)
        merged_rows: list[dict[str, Any]] = []
        for body in bodies:
            try:
                merged_rows.extend(_rows(json.loads(body.decode("utf-8"))))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError("Eastmoney A-share universe response is incomplete") from exc
        merged = json.dumps({"data": {"diff": merged_rows}}, ensure_ascii=False).encode("utf-8")
        return parse_eastmoney_a_share_universe(merged, observed_at=observed_at)

    async def _request_page(self, page: int) -> RawUniverseResponse:
        params = {
            "pn": str(page),
            "pz": str(self.page_size),
            "fs": EASTMONEY_A_SHARE_UNIVERSE_FS,
            "fields": "f12,f13,f14",
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://quote.eastmoney.com/",
        }
        if self.transport is not None:
            return await self.transport(EASTMONEY_A_SHARE_UNIVERSE_URL, params, headers)
        if self.client is not None:
            response = await self.client.get(
                EASTMONEY_A_SHARE_UNIVERSE_URL, params=params, headers=headers
            )
        else:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    EASTMONEY_A_SHARE_UNIVERSE_URL, params=params, headers=headers
                )
        return RawUniverseResponse(response.status_code, response.content)


class CninfoAShareUniverseSource:
    source_name = CNINFO_A_SHARE_UNIVERSE_SOURCE

    def __init__(
        self,
        transport: UniverseTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock

    async def fetch(self) -> tuple[AShareInstrument, ...]:
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch",
        }
        if self.transport is not None:
            response = await self.transport(CNINFO_A_SHARE_UNIVERSE_URL, {}, headers)
        elif self.client is not None:
            raw_response = await self.client.get(
                CNINFO_A_SHARE_UNIVERSE_URL, headers=headers
            )
            response = RawUniverseResponse(raw_response.status_code, raw_response.content)
        else:
            async with httpx.AsyncClient(timeout=15) as client:
                raw_response = await client.get(
                    CNINFO_A_SHARE_UNIVERSE_URL, headers=headers
                )
            response = RawUniverseResponse(raw_response.status_code, raw_response.content)
        if response.status_code != 200:
            raise ValueError(f"Cninfo A-share universe status {response.status_code}")
        instruments = parse_cninfo_a_share_universe(
            response.body, observed_at=self.clock()
        )
        if not instruments:
            raise ValueError("Cninfo A-share universe response contains no active equities")
        return instruments


class FallbackAShareUniverseSource:
    def __init__(
        self,
        primary: object,
        fallback: object,
        *,
        minimum_instrument_count: int = MINIMUM_COMPLETE_A_SHARE_UNIVERSE_COUNT,
    ) -> None:
        if minimum_instrument_count < 1:
            raise ValueError("minimum_instrument_count must be positive")
        self.sources = (primary, fallback)
        self.minimum_instrument_count = minimum_instrument_count
        self.last_source = str(getattr(primary, "source_name", "unknown"))

    async def fetch(self) -> tuple[AShareInstrument, ...]:
        errors: list[str] = []
        for source in self.sources:
            source_name = str(getattr(source, "source_name", "unknown"))
            try:
                instruments = await source.fetch()
            except (httpx.HTTPError, OSError, ValueError) as exc:
                errors.append(f"{source_name}: {exc}")
                continue
            exchanges = {instrument.exchange for instrument in instruments}
            missing_exchanges = REQUIRED_A_SHARE_EXCHANGES - exchanges
            if (
                len(instruments) >= self.minimum_instrument_count
                and not missing_exchanges
            ):
                self.last_source = source_name
                return instruments
            errors.append(
                f"{source_name}: incomplete response "
                f"(count={len(instruments)}, "
                f"missing_exchanges={','.join(sorted(missing_exchanges)) or 'none'})"
            )
        raise ValueError(
            "all A-share universe sources unavailable: " + "; ".join(errors)
        )
