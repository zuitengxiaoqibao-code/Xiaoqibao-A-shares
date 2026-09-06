from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from collections.abc import Callable
from typing import Final
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.overseas_market import (
    OverseasInstrumentQuote,
    OverseasMarketSnapshot,
)


NEW_YORK_TZ = ZoneInfo("America/New_York")
HONG_KONG_TZ = ZoneInfo("Asia/Hong_Kong")
SOURCE = "tencent_overseas"
TENCENT_URL = "https://qt.gtimg.cn/q="

INDEX_SYMBOLS: Final[tuple[tuple[str, str, str], ...]] = (
    ("usDJI", "道琼斯", "DJI"),
    ("usINX", "标普500", "INX"),
    ("usIXIC", "纳斯达克", "IXIC"),
)
MAG7_SYMBOLS: Final[tuple[tuple[str, str, str], ...]] = (
    ("usAAPL", "苹果", "AAPL"),
    ("usMSFT", "微软", "MSFT"),
    ("usNVDA", "英伟达", "NVDA"),
    ("usGOOGL", "谷歌", "GOOGL"),
    ("usAMZN", "亚马逊", "AMZN"),
    ("usMETA", "Meta", "META"),
    ("usTSLA", "特斯拉", "TSLA"),
    ("usAVGO", "博通", "AVGO"),
)
OVERSEAS_INSTRUMENTS: Final[tuple[str, ...]] = tuple(
    symbol for symbol, _, _ in (*INDEX_SYMBOLS, *MAG7_SYMBOLS)
)
_SYMBOL_META = {
    symbol: (name, ticker, "index" if symbol in {item[0] for item in INDEX_SYMBOLS} else "mag7", "hk" if symbol.startswith("hk") else "us")
    for symbol, name, ticker in (*INDEX_SYMBOLS, *MAG7_SYMBOLS)
}
_LINE_RE = re.compile(r"v_(?P<symbol>us[A-Za-z0-9]+)=\"(?P<payload>[^\"]*)\"")
_EXCHANGE_CALENDARS: dict[str, object] = {}


def _exchange_calendar(market: str):
    """Load an exchange calendar lazily so importing the API stays fast."""
    calendar_name = "XHKG" if market == "hk" else "XNYS"
    calendar = _EXCHANGE_CALENDARS.get(calendar_name)
    if calendar is not None:
        return calendar
    try:
        import exchange_calendars

        calendar = exchange_calendars.get_calendar(calendar_name)
    except (ImportError, OSError, ValueError):
        return None
    _EXCHANGE_CALENDARS[calendar_name] = calendar
    return calendar


def _exchange_session(calendar, value: date):
    """Return the exchange session row, or ``None`` when unavailable/closed."""
    try:
        if not calendar.is_session(value):
            return None
        return calendar.schedule.loc[value.isoformat()]
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _decimal(value: str, field: str) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"腾讯海外行情字段 {field} 无效") from error
    if not result.is_finite():
        raise ValueError(f"腾讯海外行情字段 {field} 无效")
    return result


def _source_datetime(value: str, *, tz: ZoneInfo = NEW_YORK_TZ) -> datetime:
    text = value.strip().replace("/", "-")
    for pattern in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=tz)
        except ValueError:
            continue
    raise ValueError("腾讯海外行情时间字段无效")


def parse_tencent_overseas_payload(payload: str, *, symbol: str) -> OverseasInstrumentQuote:
    fields = payload.split("~")
    if len(fields) < 33:
        raise ValueError("腾讯海外行情字段不完整")
    metadata = _SYMBOL_META.get(symbol)
    if metadata is None:
        raise ValueError("腾讯海外行情标的不在白名单")
    name, ticker, region, market = metadata
    # Keep the configured Chinese display name stable across Tencent's
    # occasional English/abbreviated name variants (notably AVGO).
    source_name = name
    price = _decimal(fields[3], "价格")
    if price <= 0:
        raise ValueError("腾讯海外行情价格无效")
    return OverseasInstrumentQuote(
        symbol=symbol,
        name=source_name,
        ticker=ticker,
        region=region,
        price=price,
        change=_decimal(fields[31], "涨跌额"),
        change_percent=_decimal(fields[32], "涨跌幅"),
        observed_at=_source_datetime(fields[30], tz=HONG_KONG_TZ if market == "hk" else NEW_YORK_TZ),
        trading_state="最近收盘",
        quality="ready",
    )


def _market_state(
    observed: datetime,
    now: datetime,
    *,
    market: str = "us",
    trading_day_checker: Callable[[date], bool | None] | None = None,
) -> str:
    """Return the live status for one quote in its own exchange timezone.

    The exchange calendar is authoritative for holidays and early closes. A
    checker can be injected by tests or a host application; ``None`` means the
    calendar could not be resolved, so we retain the conservative time-based
    fallback rather than claiming a false live state.
    """
    tz = HONG_KONG_TZ if market == "hk" else NEW_YORK_TZ
    local_observed = observed.astimezone(tz)
    local_now = now.astimezone(tz)
    if local_now.weekday() >= 5:
        return "休市中"
    is_trading_day = trading_day_checker(local_now.date()) if trading_day_checker is not None else None
    session = None
    if trading_day_checker is None:
        calendar = _exchange_calendar(market)
        if calendar is not None:
            session = _exchange_session(calendar, local_now.date())
            is_trading_day = session is not None
    if is_trading_day is False:
        return "休市中"
    if local_observed.date() != local_now.date():
        return "最近收盘"
    if session is not None:
        try:
            market_open = session["open"].to_pydatetime().astimezone(tz)
            market_close = session["close"].to_pydatetime().astimezone(tz)
            in_session = market_open <= local_now <= market_close
            if market == "hk":
                break_start = session["break_start"]
                break_end = session["break_end"]
                if break_start is not None and break_end is not None and str(break_start) != "NaT" and str(break_end) != "NaT":
                    break_start = break_start.to_pydatetime().astimezone(tz)
                    break_end = break_end.to_pydatetime().astimezone(tz)
                    in_session = in_session and not (break_start <= local_now < break_end)
        except (AttributeError, KeyError, TypeError, ValueError):
            in_session = False
    else:
        current = local_now.time()
        if market == "hk":
            in_session = time(9, 30) <= current <= time(12, 0) or time(13, 0) <= current <= time(16, 0)
        else:
            in_session = time(9, 30) <= current <= time(16, 0)
    return "盘中" if in_session else "最近收盘"


def _market_label(observed: datetime, now: datetime, *, market: str = "us") -> tuple[str, date, str]:
    tz = HONG_KONG_TZ if market == "hk" else NEW_YORK_TZ
    local_observed = observed.astimezone(tz)
    state = _market_state(observed, now, market=market)
    market_name = "港股" if market == "hk" else "美股"
    return f"{market_name} {local_observed.date().isoformat()} {state}", local_observed.date(), state


class TencentOverseasMarketService:
    def __init__(self, client: httpx.AsyncClient, *, cache_ttl_seconds: float = 5.0) -> None:
        self.client = client
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._last_snapshot: OverseasMarketSnapshot | None = None
        self._last_success_at: datetime | None = None

    async def _fetch(self) -> tuple[OverseasInstrumentQuote, ...]:
        url = f"{TENCENT_URL}{','.join(OVERSEAS_INSTRUMENTS)}"
        response = await self.client.get(url, timeout=20.0)
        response.raise_for_status()
        text = response.content.decode("gbk", errors="strict")
        quotes: dict[str, OverseasInstrumentQuote] = {}
        for fragment in text.split(";"):
            match = _LINE_RE.search(fragment)
            if match is None:
                continue
            symbol = match.group("symbol")
            if symbol not in _SYMBOL_META:
                continue
            try:
                quote = parse_tencent_overseas_payload(match.group("payload"), symbol=symbol)
            except (ValueError, ArithmeticError):
                continue
            quotes[symbol] = quote
        missing = tuple(symbol for symbol in OVERSEAS_INSTRUMENTS if symbol not in quotes)
        if missing:
            raise ValueError(f"腾讯海外行情缺少标的：{','.join(missing)}")
        return tuple(quotes[symbol] for symbol in OVERSEAS_INSTRUMENTS if symbol in quotes)

    async def current(self, now: datetime | None = None) -> OverseasMarketSnapshot:
        current_time = now or datetime.now(timezone.utc)
        if (
            self._last_snapshot is not None
            and self._last_success_at is not None
            and (current_time - self._last_success_at).total_seconds() < self.cache_ttl_seconds
        ):
            return self._last_snapshot
        try:
            quotes = await self._fetch()
            observed = max(item.observed_at for item in quotes)
            # Every quote gets its own exchange session status. This prevents a
            # US snapshot from incorrectly labeling a future HK quote.
            normalized = tuple(
                item.model_copy(update={"trading_state": _market_state(item.observed_at, current_time, market=_SYMBOL_META[item.symbol][3])})
                for item in quotes
            )
            market = _SYMBOL_META[quotes[0].symbol][3]
            label, source_date, _ = _market_label(observed, current_time, market=market)
            snapshot = OverseasMarketSnapshot(
                indices=tuple(item for item in normalized if item.region == "index"),
                mag7=tuple(item for item in normalized if item.region == "mag7"),
                observed_at=observed.astimezone(timezone.utc),
                source=SOURCE,
                source_trading_date=source_date,
                trading_label=label,
                quality="ready",
            )
            self._last_snapshot = snapshot
            self._last_success_at = current_time
            return snapshot
        except Exception as error:
            if self._last_snapshot is not None:
                stale = self._last_snapshot.model_copy(
                    update={
                        "quality": "stale",
                        "reason": "腾讯海外行情刷新失败，显示最近一次有效快照",
                        "indices": tuple(item.model_copy(update={"quality": "stale"}) for item in self._last_snapshot.indices),
                        "mag7": tuple(item.model_copy(update={"quality": "stale"}) for item in self._last_snapshot.mag7),
                    }
                )
                self._last_snapshot = stale
                return stale
            observed = current_time.astimezone(timezone.utc)
            return OverseasMarketSnapshot(
                observed_at=observed,
                source=SOURCE,
                trading_label="美股行情暂不可用",
                quality="unavailable",
                reason=f"腾讯海外行情暂不可用：{error}",
            )
