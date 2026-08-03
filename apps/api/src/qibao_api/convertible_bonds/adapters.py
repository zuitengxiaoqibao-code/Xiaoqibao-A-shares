import base64
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from qibao_api.contracts.convertible_bond import ClauseDates, ConvertibleBondContract
from qibao_api.contracts.instruments import validate_convertible_bond_code
from qibao_api.contracts.market import DataQuality
from qibao_api.convertible_bonds.models import (
    BondClauseSnapshot,
    BondQuote,
    BondUniverseItem,
    BondUniverseSnapshot,
    BondValuation,
    StrongRedemptionEvidence,
)

CHINA_TZ = timezone(timedelta(hours=8))
EASTMONEY_ENDPOINT = "https://datacenter-web.eastmoney.com/api/data/v1/get"
CB_LIST_REPORT = "RPT_BOND_CB_LIST"
BS_INFO_REPORT = "RPT_BOND_BS_INFO"
EASTMONEY_PARSER_VERSION = "eastmoney-v2"
VALUATION_REPORT = "RPTA_WEB_KZZ_LS"
UNIVERSE_REPORT = CB_LIST_REPORT


@dataclass(frozen=True)
class RawHttpResponse:
    status_code: int
    body: bytes


ClauseTransport = Callable[[str, dict[str, str]], Awaitable[RawHttpResponse]]


class ClauseDataUnavailable(LookupError):
    pass


def _provider_optional_date(value: Any) -> date | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        return date.fromisoformat(str(value).split(" ", 1)[0])
    except ValueError:
        return None


def parse_eastmoney_bond_universe(
    raw_payload: bytes, *, observed_at: datetime
) -> BondUniverseSnapshot:
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
        result = payload["result"]
        rows = result.get("data") or []
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Eastmoney bond universe response is incomplete") from exc

    items: list[BondUniverseItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("SECURITY_CODE") or "")
        try:
            validate_convertible_bond_code(code)
        except ValueError:
            continue
        delisted = _provider_optional_date(row.get("DELIST_DATE"))
        ceased = _provider_optional_date(row.get("CEASE_DATE"))
        maturity = _provider_optional_date(row.get("EXPIRE_DATE"))
        if delisted is not None and delisted <= observed_at.date():
            continue
        if ceased is not None and ceased <= observed_at.date():
            continue
        if maturity is not None and maturity < observed_at.date():
            continue
        encoded_row = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        items.append(
            BondUniverseItem(
                bond_code=code,
                name=str(row.get("SECURITY_NAME_ABBR") or code),
                linked_stock_code=(
                    str(row["CONVERT_STOCK_CODE"])
                    if row.get("CONVERT_STOCK_CODE") not in (None, "", "--", "-")
                    else None
                ),
                listing_date=_provider_optional_date(row.get("LISTING_DATE")),
                maturity=maturity,
                observed_at=observed_at,
                source="eastmoney",
                raw_identity=hashlib.sha256(encoded_row.encode("utf-8")).hexdigest(),
            )
        )
    items.sort(key=lambda item: item.bond_code)
    return BondUniverseSnapshot(
        observed_at=observed_at,
        source="eastmoney",
        raw_identity=hashlib.sha256(raw_payload).hexdigest(),
        items=tuple(items),
    )


def _bond_market_prefix(code: str) -> str:
    validate_convertible_bond_code(code)
    return "sh" if code.startswith("11") else "sz"


def _extract_tencent_payload(body: str) -> str:
    if '="' not in body:
        raise ValueError("Tencent quote response has no payload")
    return body.split('="', 1)[1].rsplit('"', 1)[0]


class TencentBondQuoteSource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, bond_code: str) -> BondQuote:
        instrument = f"{_bond_market_prefix(bond_code)}{bond_code}"
        response = await self.client.get(f"https://qt.gtimg.cn/q={instrument}")
        response.raise_for_status()
        raw = response.content
        fields = _extract_tencent_payload(raw.decode("gbk", errors="strict")).split("~")
        if len(fields) < 31:
            raise ValueError("Tencent quote payload is incomplete")
        if fields[2] != bond_code:
            raise ValueError("Tencent payload code does not match requested bond")
        observed_at = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(tzinfo=CHINA_TZ)
        price = Decimal(fields[3])
        suspended = price == 0
        return BondQuote(
            symbol=fields[2],
            name=fields[1],
            price=None if suspended else price,
            previous_close=Decimal(fields[4]),
            suspended=suspended,
            observed_at=observed_at,
            source="tencent",
            quality=DataQuality.UNAVAILABLE if suspended else DataQuality.FRESH,
            raw_identity=hashlib.sha256(raw).hexdigest(),
            turnover_amount=(Decimal(fields[37]) * Decimal("10000"))
            if len(fields) > 37 and fields[37].strip() else None,
        )


class EastmoneyBondValuationSource:
    def __init__(self, transport: ClauseTransport | None = None, *, client: httpx.AsyncClient | None = None) -> None:
        self.transport = transport
        self.client = client

    async def fetch(self, bond_code: str) -> BondValuation:
        validate_convertible_bond_code(bond_code)
        params = {"reportName": VALUATION_REPORT, "columns": "ALL",
                  "filter": f'(ZCODE="{bond_code}")', "sortColumns": "DATE",
                  "sortTypes": "-1", "pageNumber": "1", "pageSize": "1"}
        if self.transport:
            response = await self.transport(EASTMONEY_ENDPOINT, params)
        elif self.client is not None:
            result = await self.client.get(EASTMONEY_ENDPOINT, params=params)
            response = RawHttpResponse(result.status_code, result.content)
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                result = await client.get(EASTMONEY_ENDPOINT, params=params)
                response = RawHttpResponse(result.status_code, result.content)
        if response.status_code != 200:
            raise ValueError(f"Eastmoney valuation status {response.status_code}")
        row = _provider_row(response.body, VALUATION_REPORT)
        if str(row.get("ZCODE")) != bond_code:
            raise ValueError("Eastmoney valuation code does not match requested bond")
        return BondValuation(
            bond_code=bond_code, observed_at=datetime.fromisoformat(str(row["DATE"])).replace(tzinfo=CHINA_TZ),
            pure_bond_value=_required_decimal(row, "PUREBONDVALUE"),
            provider_conversion_value=_optional_decimal(row.get("SWAPVALUE")),
            provider_conversion_premium=_optional_decimal(row.get("SWAPOR")),
            provider_pure_bond_premium=_optional_decimal(row.get("PUREBONDOR")),
            close=_optional_decimal(row.get("FCLOSE")), conversion_price=_optional_decimal(row.get("SWAPPRICE")),
            raw_identity=hashlib.sha256(response.body).hexdigest(),
        )


def _optional_decimal(value) -> Decimal | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _required_decimal(row: dict[str, Any], field: str) -> Decimal:
    value = row.get(field)
    if value in (None, "", "--", "-"):
        raise ValueError(f"Eastmoney valuation field {field} is unavailable")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Eastmoney valuation field {field} is invalid") from exc
    if not parsed.is_finite():
        raise ValueError(f"Eastmoney valuation field {field} is invalid")
    return parsed


def pack_raw_reports(reports: dict[str, bytes]) -> bytes:
    payload = {
        report: base64.b64encode(body).decode("ascii") for report, body in sorted(reports.items())
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")


def unpack_raw_reports(raw_payload: bytes) -> dict[str, bytes]:
    try:
        payload = json.loads(raw_payload.decode("ascii"))
        return {report: base64.b64decode(body, validate=True) for report, body in payload.items()}
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError("Eastmoney raw report bundle is invalid") from exc


def parse_eastmoney_clause_payloads(
    reports: dict[str, bytes],
    *,
    requested_bond_code: str,
    fetched_at: datetime,
) -> BondClauseSnapshot:
    if set(reports) != {CB_LIST_REPORT, BS_INFO_REPORT}:
        raise ValueError("Eastmoney clause snapshot requires both reports")
    cb_row = _provider_row(reports[CB_LIST_REPORT], CB_LIST_REPORT)
    bs_row = _provider_row(reports[BS_INFO_REPORT], BS_INFO_REPORT)
    cb_code = _required(cb_row, "SECURITY_CODE")
    bs_code = _required(bs_row, "SECURITY_CODE")
    if cb_code != requested_bond_code or bs_code != requested_bond_code:
        raise ValueError("Eastmoney SECURITY_CODE does not match requested bond")

    contract = ConvertibleBondContract(
        bond_code=cb_code,
        linked_stock=_required(cb_row, "CONVERT_STOCK_CODE"),
        conversion_price=Decimal(_required(cb_row, "TRANSFER_VALUE")),
        maturity=_provider_date(_required(bs_row, "HONOUR_DATE")),
        remaining_size=Decimal(_required(bs_row, "BOND_BALANCE")),
        clause_dates=ClauseDates(
            conversion_start=_provider_date(_required(cb_row, "TRANSFER_START_DATE")),
            redemption_start=None,
            put_back_start=None,
        ),
        as_of=fetched_at,
    )
    raw_payload = pack_raw_reports(reports)
    evidence = _strong_redemption_evidence(cb_row, bs_row, fetched_at)
    return BondClauseSnapshot(
        contract=contract,
        raw_payload=raw_payload,
        content_hash=hashlib.sha256(raw_payload).hexdigest(),
        source="eastmoney",
        fetched_at=fetched_at,
        parser_version=EASTMONEY_PARSER_VERSION,
        strong_redemption=evidence,
    )


def parse_eastmoney_clause_bundle(
    raw_payload: bytes, *, requested_bond_code: str, fetched_at: datetime
) -> BondClauseSnapshot:
    return parse_eastmoney_clause_payloads(
        unpack_raw_reports(raw_payload),
        requested_bond_code=requested_bond_code,
        fetched_at=fetched_at,
    )


def _provider_row(raw_payload: bytes, report: str) -> dict[str, Any]:
    try:
        response = json.loads(raw_payload.decode("utf-8"))
        rows = response["result"]["data"]
        if not rows:
            raise ClauseDataUnavailable(f"Eastmoney {report} has no clause rows")
        return rows[0]
    except ClauseDataUnavailable:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Eastmoney {report} response is incomplete") from exc


def _strong_redemption_evidence(cb_row: dict[str, Any], bs_row: dict[str, Any], fetched_at: datetime) -> StrongRedemptionEvidence:
    fields = {}
    for report, row in ((CB_LIST_REPORT, cb_row), (BS_INFO_REPORT, bs_row)):
        for key, raw in row.items():
            if (key == "IS_REDEEM" or "TRIGGER" in key or "REDEEM_STATUS" in key
                    or "ANNOUNCEMENT_TYPE" in key
                    or key.startswith(("NOTICE_DATE_", "EXECUTE_START_DATE", "EXECUTE_END_DATE",
                                       "ACTUAL_EXECUTE_DATE", "EXECUTE_REASON_"))):
                if raw not in (None, "", "0"):
                    fields[f"{report}.{key}"] = str(raw)
    clause_present = bool(cb_row.get("REDEEM_CLAUSE") or bs_row.get("REDEEM_CLAUSE"))
    notice = any(".NOTICE_DATE_" in key for key in fields)
    reason = any(".EXECUTE_REASON_" in key for key in fields)
    announcement_type = any("ANNOUNCEMENT_TYPE" in key for key in fields)
    starts = [value for key, value in fields.items() if ".EXECUTE_START_DATE" in key]
    ends = [value for key, value in fields.items()
            if ".EXECUTE_END_DATE" in key or ".ACTUAL_EXECUTE_DATE" in key]
    triggered = any(("TRIGGER" in key or "REDEEM_STATUS" in key)
                    and value.lower() not in {"0", "false", "n", "unknown"}
                    for key, value in fields.items())
    today = fetched_at.date()
    if starts and ends and reason and date.fromisoformat(ends[0].split(" ")[0]) <= today:
        state = "completed"
    elif notice and (reason or announcement_type):
        state = "announced"
    elif triggered:
        state = "triggered"
    else:
        state = "unknown"
    clause_text = cb_row.get("REDEEM_CLAUSE") or bs_row.get("REDEEM_CLAUSE")
    return StrongRedemptionEvidence(state=state, clause_present=clause_present,
                                    evidence_fields=fields, clause_text=clause_text)


def _required(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if value is None or value == "":
        raise ValueError(f"Eastmoney field {field} is missing")
    return str(value)


def _provider_date(value: str) -> date:
    return date.fromisoformat(value.split(" ", 1)[0])


class EastmoneyClauseSource:
    def __init__(
        self,
        transport: ClauseTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock

    async def fetch(self, bond_code: str) -> BondClauseSnapshot:
        validate_convertible_bond_code(bond_code)
        reports: dict[str, bytes] = {}
        for report in (CB_LIST_REPORT, BS_INFO_REPORT):
            params = {
                "reportName": report,
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{bond_code}")',
                "pageNumber": "1",
                "pageSize": "1",
            }
            response = await self._request(params)
            if response.status_code != 200:
                raise ValueError(
                    f"Eastmoney {report} request returned status {response.status_code}"
                )
            reports[report] = response.body
        return parse_eastmoney_clause_payloads(
            reports,
            requested_bond_code=bond_code,
            fetched_at=self.clock(),
        )

    async def _request(self, params: dict[str, str]) -> RawHttpResponse:
        if self.transport is not None:
            return await self.transport(EASTMONEY_ENDPOINT, params)
        if self.client is not None:
            response = await self.client.get(EASTMONEY_ENDPOINT, params=params)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(EASTMONEY_ENDPOINT, params=params)
        return RawHttpResponse(status_code=response.status_code, body=response.content)


class EastmoneyBondUniverseSource:
    """Fetch the public in-market convertible-bond universe at low frequency."""

    def __init__(
        self,
        transport: ClauseTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        page_size: int = 5000,
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock
        self.page_size = page_size

    async def fetch(self) -> BondUniverseSnapshot:
        fetched_at = self.clock()
        first = await self._request_page(1)
        if first.status_code != 200:
            raise ValueError(f"Eastmoney bond universe status {first.status_code}")
        try:
            first_payload = json.loads(first.body.decode("utf-8"))
            pages = max(1, int(first_payload.get("result", {}).get("pages") or 1))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Eastmoney bond universe response is incomplete") from exc
        bodies = [first.body]
        for page in range(2, pages + 1):
            response = await self._request_page(page)
            if response.status_code != 200:
                raise ValueError(f"Eastmoney bond universe status {response.status_code}")
            bodies.append(response.body)
        if len(bodies) == 1:
            return parse_eastmoney_bond_universe(first.body, observed_at=fetched_at)
        rows: list[dict[str, Any]] = []
        for body in bodies:
            try:
                payload = json.loads(body.decode("utf-8"))
                rows.extend(payload.get("result", {}).get("data") or [])
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
                raise ValueError("Eastmoney bond universe response is incomplete") from exc
        merged = json.dumps({"result": {"data": rows}}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return parse_eastmoney_bond_universe(merged, observed_at=fetched_at).model_copy(
            update={"raw_identity": hashlib.sha256(b"".join(bodies)).hexdigest()}
        )

    async def _request_page(self, page: int) -> RawHttpResponse:
        params = {
            "reportName": UNIVERSE_REPORT,
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,CONVERT_STOCK_CODE,LISTING_DATE,EXPIRE_DATE,DELIST_DATE,CEASE_DATE",
            "sortColumns": "SECURITY_CODE",
            "sortTypes": "1",
            "pageNumber": str(page),
            "pageSize": str(self.page_size),
        }
        if self.transport is not None:
            return await self.transport(EASTMONEY_ENDPOINT, params)
        if self.client is not None:
            response = await self.client.get(EASTMONEY_ENDPOINT, params=params)
        else:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(EASTMONEY_ENDPOINT, params=params)
        return RawHttpResponse(status_code=response.status_code, body=response.content)
