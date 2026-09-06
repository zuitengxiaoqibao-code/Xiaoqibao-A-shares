import json
import re
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.market_overview import (
    OverviewIndexQuote,
    OverviewMinutePoint,
    OverviewStockQuote,
)
from qibao_api.gongbu.market_feed import MarketFeedSnapshot
from qibao_api.gongbu.tencent_quotes import market_prefix, parse_tencent_snapshot


CHINA_TZ = ZoneInfo("Asia/Shanghai")
_QUOTE_PATTERN = re.compile(r'^v_(?P<instrument>(?:sh|sz)\d{6})="(?P<payload>.*)";$')


def parse_index_quotes(
    raw: bytes,
    requested: tuple[str, ...],
) -> tuple[tuple[OverviewIndexQuote, ...], tuple[str, ...]]:
    try:
        text = raw.decode("gbk", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Tencent index quotes are not valid GBK") from error

    parsed: dict[str, OverviewIndexQuote] = {}
    seen: set[str] = set()
    warnings: list[str] = []
    for line in text.splitlines():
        match = _QUOTE_PATTERN.match(line.strip())
        if match is None:
            continue
        instrument = match.group("instrument")
        if instrument not in requested:
            continue
        seen.add(instrument)
        fields = match.group("payload").split("~")
        try:
            if len(fields) < 33:
                raise ValueError("incomplete quote")
            observed_at = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(
                tzinfo=CHINA_TZ
            )
            parsed[instrument] = OverviewIndexQuote(
                instrument=instrument,
                name=fields[1].strip(),
                value=Decimal(fields[3]),
                change=Decimal(fields[31]),
                change_percent=Decimal(fields[32]),
                observed_at=observed_at,
                source="tencent",
                quality="ready",
            )
        except (InvalidOperation, ValueError):
            warnings.append(f"index_quote_invalid:{instrument}")

    for instrument in requested:
        if instrument not in seen:
            warnings.append(f"index_quote_missing:{instrument}")
    ordered = tuple(parsed[instrument] for instrument in requested if instrument in parsed)
    return ordered, tuple(warnings)


def parse_index_minutes(
    payload: bytes,
    instrument: str,
) -> tuple[tuple[OverviewMinutePoint, ...], tuple[str, ...]]:
    try:
        document = json.loads(payload.decode("utf-8", errors="strict"))
        node = document["data"][instrument]["data"]
        trading_date = datetime.strptime(str(node["date"]), "%Y%m%d").date()
        rows = node["data"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("Tencent index minute payload is invalid") from error
    if not isinstance(rows, list):
        raise ValueError("Tencent index minute rows are not a list")

    points: list[OverviewMinutePoint] = []
    warnings: list[str] = []
    for row in rows:
        try:
            parts = str(row).split()
            if len(parts) != 4:
                raise ValueError("minute row is incomplete")
            observed_at = datetime.combine(
                trading_date,
                datetime.strptime(parts[0], "%H%M").time(),
                tzinfo=CHINA_TZ,
            )
            points.append(OverviewMinutePoint(
                observed_at=observed_at,
                price=Decimal(parts[1]),
                volume=Decimal(parts[2]),
                amount=Decimal(parts[3]),
            ))
        except (InvalidOperation, ValueError):
            warnings.append(f"minute_point_invalid:{row}")
    return tuple(points), tuple(warnings)


def parse_stock_quotes(
    raw: bytes,
    requested: tuple[str, ...],
) -> tuple[tuple[OverviewStockQuote, ...], tuple[str, ...]]:
    try:
        text = raw.decode("gbk", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Tencent stock quotes are not valid GBK") from error
    by_symbol: dict[str, OverviewStockQuote] = {}
    warnings: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _QUOTE_PATTERN.match(line.strip())
        if match is None:
            continue
        fields = match.group("payload").split("~")
        symbol = fields[2].strip() if len(fields) > 2 else ""
        if symbol not in requested:
            continue
        seen.add(symbol)
        try:
            if len(fields) < 45:
                raise ValueError("incomplete quote")
            by_symbol[symbol] = OverviewStockQuote(
                symbol=symbol,
                name=fields[1].strip(),
                change_percent=Decimal(fields[32]),
                amount_yi=(
                    Decimal(fields[37]) / Decimal("10000")
                    if fields[37] not in {"", "--"} else None
                ),
                market_cap_yi=(
                    Decimal(fields[44]) if fields[44] not in {"", "--"} else None
                ),
                turnover_rate=(
                    Decimal(fields[38]) if fields[38] not in {"", "--"} else None
                ),
                observed_at=datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(
                    tzinfo=CHINA_TZ
                ),
            )
        except (InvalidOperation, ValueError):
            warnings.append(f"stock_quote_invalid:{symbol}")
    for symbol in requested:
        if symbol not in seen:
            warnings.append(f"stock_quote_missing:{symbol}")
    return (
        tuple(by_symbol[symbol] for symbol in requested if symbol in by_symbol),
        tuple(warnings),
    )


class TencentOverviewSource:
    source_id = "tencent"
    index_endpoint = "https://qt.gtimg.cn/q="
    minute_endpoint = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def fetch_indices(
        self,
        instruments: tuple[str, ...] = (
            "sh000001", "sz399001", "sh000688", "sz399006", "sh000905",
        ),
    ):
        response = self.client.get(f"{self.index_endpoint}{','.join(instruments)}")
        response.raise_for_status()
        return parse_index_quotes(response.content, instruments)

    def fetch_minutes(self, instrument: str = "sh000001"):
        response = self.client.get(
            self.minute_endpoint,
            params={"code": instrument},
        )
        response.raise_for_status()
        return parse_index_minutes(response.content, instrument)

    def fetch_minutes_by_index(
        self,
        instruments: tuple[str, ...] = ("sh000001", "sz399001", "sz399006"),
    ) -> tuple[dict[str, tuple[OverviewMinutePoint, ...]], tuple[str, ...]]:
        """Fetch independent real minute series for each requested index."""
        series: dict[str, tuple[OverviewMinutePoint, ...]] = {}
        warnings: list[str] = []
        for instrument in instruments:
            try:
                points, item_warnings = self.fetch_minutes(instrument)
            except (httpx.HTTPError, OSError, ValueError):
                points, item_warnings = (), (f"minute_series_unavailable:{instrument}",)
            series[instrument] = points
            warnings.extend(item_warnings)
        return series, tuple(warnings)

    def fetch_stock_minutes(self, symbol: str, *, cutoff: datetime | None = None):
        """Fetch the real current-session minute series for one A-share.

        Tencent's minute endpoint returns cumulative volume/amount and does
        not include the previous close, so the quote endpoint is read once to
        calculate the genuine change fields required by ``MarketFeedSnapshot``.
        Rows after the caller's cutoff are discarded; no synthetic points are
        inserted when either upstream response is incomplete.
        """
        instrument = f"{market_prefix(symbol)}{symbol}"
        response = self.client.get(self.minute_endpoint, params={"code": instrument})
        response.raise_for_status()
        points, _warnings = parse_index_minutes(response.content, instrument)
        if not points:
            return ()

        quote_response = self.client.get(f"{self.index_endpoint}{instrument}")
        quote_response.raise_for_status()
        text = quote_response.content.decode("gbk", errors="strict")
        marker = '="'
        if marker not in text:
            raise ValueError("Tencent stock quote response has no payload")
        payload = text.split(marker, 1)[1].rsplit('"', 1)[0]
        quote = parse_tencent_snapshot(payload, "tencent")
        previous_close = quote.previous_close
        fetched_at = datetime.now(CHINA_TZ)
        if cutoff is not None:
            fetched_at = min(fetched_at, cutoff)
        result = []
        for point in points:
            local_time = point.observed_at.astimezone(CHINA_TZ).time()
            if not (
                time(9, 30) <= local_time <= time(11, 30)
                or time(13, 0) <= local_time <= time(15, 0)
            ):
                # Tencent may append post-close reference rows (15:06-15:30)
                # to the current-session response.  They are not tradable
                # minutes and would overwrite the genuine 15:00 point.
                continue
            if cutoff is not None and point.observed_at > cutoff:
                continue
            change = point.price - previous_close
            result.append(MarketFeedSnapshot(
                symbol=symbol,
                price=point.price,
                change=change,
                change_percent=(change / previous_close * Decimal("100")),
                volume=point.volume,
                source="tencent-minute",
                observed_at=point.observed_at,
                fetched_at=max(fetched_at, point.observed_at),
                quality="ready",
                source_snapshot_id=f"tencent-minute-{symbol}-{point.observed_at.strftime('%Y%m%d%H%M')}",
            ))
        return tuple(result)

    def fetch_stocks(self, symbols: tuple[str, ...]):
        if not symbols:
            return (), ()
        instruments = tuple(f"{market_prefix(symbol)}{symbol}" for symbol in symbols)
        response = self.client.get(f"{self.index_endpoint}{','.join(instruments)}")
        response.raise_for_status()
        return parse_stock_quotes(response.content, symbols)
