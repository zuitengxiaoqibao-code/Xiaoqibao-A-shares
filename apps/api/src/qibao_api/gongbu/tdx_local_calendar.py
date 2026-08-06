from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

class TdxCalendarDataUnavailable(RuntimeError):
    """Raised when TDX calendar data is empty, invalid, or incomplete."""


@dataclass(frozen=True)
class TdxIpoEvent:
    code: str
    name: str
    kind: str
    subscription_date: date
    listing_date: date | None
    allotment_date: date | None
    fetched_at: datetime
    source: str = "tdx-local-rpc"


def _rows(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, Mapping) or str(payload.get("ErrorId")) != "0":
        return ()
    value = payload.get("Value")
    if isinstance(value, Mapping):
        value = value.get("Data", value.get("Rows", value.get("Value")))
    if not isinstance(value, list):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _lookup(row: Mapping[str, Any], *names: str) -> Any:
    normalized = {
        str(key).casefold().replace("_", "").replace(" ", ""): value
        for key, value in row.items()
    }
    for name in names:
        value = normalized.get(name.casefold().replace("_", "").replace(" ", ""))
        if value not in (None, "", "--", "-"):
            return value
    return None


def _parse_date(value: Any) -> date | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).strip().split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _code(value: Any) -> str | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).strip().split(".", 1)[0]
    if len(text) != 6 or not text.isdigit():
        return None
    # IPO and new-bond subscription codes are not always valid *listed*
    # A-share codes (for example 732xxx/787xxx and 11xxxx/12xxxx).  The
    # calendar contract therefore validates the explicit six-digit shape and
    # leaves instrument classification to the returned kind field.
    return text


def parse_tdx_ipo_info(payload: Any, *, fetched_at: datetime) -> tuple[TdxIpoEvent, ...]:
    rows = _rows(payload)
    if not rows:
        raise TdxCalendarDataUnavailable("TDX IPO calendar response is empty")
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    events: list[TdxIpoEvent] = []
    for row in rows:
        code = _code(_lookup(row, "Code", "StockCode", "证券代码", "申购代码"))
        name = _lookup(row, "Name", "StockName", "证券简称", "申购简称")
        kind = _lookup(row, "Type", "Kind", "品种", "申购类型")
        subscription_date = _parse_date(
            _lookup(row, "ApplyDate", "SubscriptionDate", "申购日期", "网上申购日")
        )
        listing_date = _parse_date(
            _lookup(row, "ListingDate", "上市日期", "上市日")
        )
        allotment_date = _parse_date(
            _lookup(row, "AllotmentDate", "摇号日期", "中签号公布日")
        )
        if not code or not name or not kind or subscription_date is None:
            continue
        events.append(TdxIpoEvent(
            code=code,
            name=str(name).strip(),
            kind=str(kind).strip(),
            subscription_date=subscription_date,
            listing_date=listing_date,
            allotment_date=allotment_date,
            fetched_at=fetched_at,
        ))
    if not events:
        raise TdxCalendarDataUnavailable("TDX IPO calendar rows are incomplete")
    return tuple(events)


class TdxLocalIpoSource:
    """Read-only local TdxQuant source for IPO and new-bond calendar rows."""

    def __init__(self, rpc_factory, *, clock=lambda: datetime.now(timezone.utc)) -> None:
        self.rpc_factory = rpc_factory
        self.clock = clock

    def fetch(self, *, market: str = "5") -> tuple[TdxIpoEvent, ...]:
        rpc = self.rpc_factory()
        if rpc is None or not getattr(rpc, "available", lambda: False)():
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
            raise TdxCalendarDataUnavailable("TDX local bridge unavailable")
        try:
            payload = rpc.call("get_ipo_info", {"market": market})
            return parse_tdx_ipo_info(payload, fetched_at=self.clock())
        finally:
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
