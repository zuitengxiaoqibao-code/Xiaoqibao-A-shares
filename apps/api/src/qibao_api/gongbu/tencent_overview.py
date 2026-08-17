import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.market_overview import (
    OverviewIndexQuote,
    OverviewMinutePoint,
    OverviewStockQuote,
)
from qibao_api.gongbu.tencent_quotes import market_prefix


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

    def fetch_stocks(self, symbols: tuple[str, ...]):
        if not symbols:
            return (), ()
        instruments = tuple(f"{market_prefix(symbol)}{symbol}" for symbol in symbols)
        response = self.client.get(f"{self.index_endpoint}{','.join(instruments)}")
        response.raise_for_status()
        return parse_stock_quotes(response.content, symbols)
