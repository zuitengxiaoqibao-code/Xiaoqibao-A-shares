from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.market_overview import OverviewIndexQuote, OverviewMinutePoint, OverviewStockQuote


CHINA_TZ = ZoneInfo("Asia/Shanghai")
INDEX_SYMBOLS = {
    "sh000001": "000001.SH",
    "sz399001": "399001.SZ",
    "sh000688": "000688.SH",
    "sz399006": "399006.SZ",
    "sh000905": "000905.SH",
}


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "" or value == "--":
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


def _symbol_parts(symbol: str) -> tuple[str, str]:
    code = str(symbol).strip().upper()
    if "." in code:
        number, exchange = code.split(".", 1)
        return number.zfill(6), exchange
    exchange = "SH" if code.startswith(("5", "6", "688", "689")) else "SZ"
    return code.zfill(6), exchange


def _external_symbol(symbol: str) -> str:
    """Convert local Tencent instrument notation to provider notation."""
    code = str(symbol).strip().lower()
    if code.startswith(("sh", "sz", "bj")) and len(code) == 8:
        suffix = {"sh": "SH", "sz": "SZ", "bj": "BJ"}[code[:2]]
        return f"{code[2:]}.{suffix}"
    number, exchange = _symbol_parts(symbol)
    return f"{number}.{exchange}"


def _observed_at(timestamp: Any) -> datetime:
    value = _decimal(timestamp)
    if value is not None:
        # TickFlow timestamps are milliseconds since epoch.
        return datetime.fromtimestamp(float(value) / 1000, tz=CHINA_TZ)
    return datetime.now(CHINA_TZ)


class TickFlowQuoteSource:
    """Adapter for TickFlow's documented ``/v1/quotes`` endpoint."""

    source_id = "tickflow"

    def __init__(self, client: httpx.Client, api_key: str, *, base_url: str = "https://api.tickflow.org") -> None:
        self.client = client
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.last_source_id = self.source_id

    def _request(self, symbols: tuple[str, ...]):
        response = self.client.get(
            f"{self.base_url}/v1/quotes",
            params={"symbols": ",".join(symbols)},
            headers={"x-api-key": self.api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else None
        return rows if isinstance(rows, list) else []

    def fetch_stocks(self, symbols: tuple[str, ...]):
        if not symbols:
            return (), ()
        requested = tuple(dict.fromkeys(symbols))
        by_symbol = {symbol: symbol for symbol in requested}
        try:
            rows = self._request(tuple(_external_symbol(item) for item in requested))
        except (httpx.HTTPError, OSError, ValueError) as error:
            return (), (f"tickflow_unavailable:{type(error).__name__}",)
        output = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            code, _exchange = _symbol_parts(str(row.get("symbol") or ""))
            symbol = by_symbol.get(code)
            if symbol is None:
                continue
            ext = row.get("ext") if isinstance(row.get("ext"), dict) else {}
            change_percent = _decimal(ext.get("change_pct"))
            # TickFlow documents 0.01 as 1%; normalize to percentage points.
            if change_percent is not None and abs(change_percent) <= Decimal("1"):
                change_percent *= Decimal("100")
            amount_yi = _decimal(row.get("amount"))
            if amount_yi is not None:
                amount_yi /= Decimal("100000000")
            output.append(OverviewStockQuote(
                symbol=code,
                name=str(ext.get("name") or row.get("symbol") or code),
                change_percent=change_percent or Decimal("0"),
                amount_yi=amount_yi,
                market_cap_yi=None,
                turnover_rate=(
                    (_decimal(ext.get("turnover_rate")) or Decimal("0")) * Decimal("100")
                    if ext.get("turnover_rate") is not None else None
                ),
                observed_at=_observed_at(row.get("timestamp")),
            ))
        return tuple(output), (() if output else ("tickflow_quotes_empty",))

    def fetch_indices(self):
        requested = tuple(INDEX_SYMBOLS.values())
        try:
            rows = self._request(requested)
        except (httpx.HTTPError, OSError, ValueError) as error:
            return (), (f"tickflow_unavailable:{type(error).__name__}",)
        output = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "").upper()
            instrument = next((key for key, value in INDEX_SYMBOLS.items() if value == symbol), None)
            if instrument is None:
                continue
            value = _decimal(row.get("last_price"))
            previous = _decimal(row.get("prev_close"))
            if value is None or value <= 0 or previous is None or previous <= 0:
                continue
            ext = row.get("ext") if isinstance(row.get("ext"), dict) else {}
            change = _decimal(ext.get("change_amount")) or (value - previous)
            change_percent = _decimal(ext.get("change_pct"))
            if change_percent is None:
                change_percent = change / previous * Decimal("100")
            elif abs(change_percent) <= Decimal("1"):
                change_percent *= Decimal("100")
            output.append(OverviewIndexQuote(
                instrument=instrument,
                name=str(ext.get("name") or instrument),
                value=value,
                change=change,
                change_percent=change_percent,
                observed_at=_observed_at(row.get("timestamp")),
                source=self.source_id,
                quality="ready",
            ))
        ordered = tuple(next((item for item in output if item.instrument == key), None) for key in INDEX_SYMBOLS)
        result = tuple(item for item in ordered if item is not None)
        return result, (() if result else ("tickflow_indices_empty",))

    def fetch_minutes(self, instrument: str = "sh000001"):
        external_symbol = _external_symbol(instrument)
        try:
            response = self.client.get(
                f"{self.base_url}/v1/klines/intraday",
                params={"symbol": external_symbol, "period": "1m"},
                headers={"x-api-key": self.api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                return (), ("tickflow_minutes_empty",)
            rows = []
            keys = ("timestamp", "open", "high", "low", "close", "volume", "amount")
            arrays = [data.get(key) for key in keys]
            if not all(isinstance(item, list) for item in arrays):
                return (), ("tickflow_minutes_invalid",)
            for values in zip(*arrays, strict=False):
                observed, _open, _high, _low, close, volume, amount = values
                price = _decimal(close)
                if price is None or price <= 0:
                    continue
                rows.append(OverviewMinutePoint(
                    observed_at=_observed_at(observed),
                    price=price,
                    volume=_decimal(volume) or Decimal("0"),
                    amount=_decimal(amount) or Decimal("0"),
                ))
            return tuple(rows), (() if rows else ("tickflow_minutes_empty",))
        except (httpx.HTTPError, OSError, ValueError) as error:
            return (), (f"tickflow_minutes_unavailable:{type(error).__name__}",)


class TushareQuoteSource:
    """Adapter for Tushare Pro's documented JSON POST protocol."""

    source_id = "tushare"

    def __init__(self, client: httpx.Client, token: str, *, base_url: str = "https://api.tushare.pro") -> None:
        self.client = client
        self.token = token
        self.base_url = base_url
        self.last_source_id = self.source_id

    def _query(self, api_name: str, params: dict[str, Any], fields: str):
        response = self.client.post(
            self.base_url,
            json={"api_name": api_name, "token": self.token, "params": params, "fields": fields},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") not in (None, 0):
            raise ValueError(str(payload.get("msg") if isinstance(payload, dict) else "tushare response invalid"))
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return []
        fields_list = data.get("fields") or []
        return [dict(zip(fields_list, row, strict=False)) for row in (data.get("items") or [])]

    def fetch_stocks(self, symbols: tuple[str, ...]):
        if not symbols:
            return (), ()
        codes = tuple(f"{code}.{exchange}" for code, exchange in (_symbol_parts(item) for item in symbols))
        try:
            rows = self._query("daily", {"ts_code": ",".join(codes)}, "ts_code,trade_date,close,pre_close,change,pct_chg,amount")
        except (httpx.HTTPError, OSError, ValueError) as error:
            return (), (f"tushare_unavailable:{type(error).__name__}",)
        output = []
        for row in rows:
            code, _exchange = _symbol_parts(str(row.get("ts_code") or ""))
            close = _decimal(row.get("close"))
            previous = _decimal(row.get("pre_close"))
            trade_date = str(row.get("trade_date") or "")
            if close is None or close <= 0 or previous is None or previous <= 0 or len(trade_date) != 8:
                continue
            observed = datetime.strptime(trade_date, "%Y%m%d").replace(hour=15, minute=0, tzinfo=CHINA_TZ)
            output.append(OverviewStockQuote(
                symbol=code,
                name=code,
                change_percent=_decimal(row.get("pct_chg")) or ((close - previous) / previous * Decimal("100")),
                amount_yi=(_decimal(row.get("amount")) or Decimal("0")) / Decimal("10000"),
                observed_at=observed,
            ))
        return tuple(output), (() if output else ("tushare_quotes_empty",))

    def fetch_indices(self):
        codes = tuple(INDEX_SYMBOLS.values())
        try:
            rows = self._query("index_daily", {"ts_code": ",".join(codes)}, "ts_code,trade_date,close,pre_close,change,pct_chg")
        except (httpx.HTTPError, OSError, ValueError) as error:
            return (), (f"tushare_unavailable:{type(error).__name__}",)
        output = []
        for row in rows:
            symbol = str(row.get("ts_code") or "").upper()
            instrument = next((key for key, value in INDEX_SYMBOLS.items() if value == symbol), None)
            value = _decimal(row.get("close"))
            previous = _decimal(row.get("pre_close"))
            trade_date = str(row.get("trade_date") or "")
            if instrument is None or value is None or value <= 0 or previous is None or previous <= 0 or len(trade_date) != 8:
                continue
            observed = datetime.strptime(trade_date, "%Y%m%d").replace(hour=15, minute=0, tzinfo=CHINA_TZ)
            change = _decimal(row.get("change")) or value - previous
            output.append(OverviewIndexQuote(
                instrument=instrument,
                name=instrument,
                value=value,
                change=change,
                change_percent=_decimal(row.get("pct_chg")) or change / previous * Decimal("100"),
                observed_at=observed,
                source=self.source_id,
                quality="stale",
            ))
        return tuple(output), (() if output else ("tushare_indices_empty",))

    def fetch_minutes(self, instrument: str = "sh000001"):
        return (), ("tushare_minute_not_enabled",)


class ExternalQuoteFallbackSource:
    """Primary-first source composition used by market overview."""

    def __init__(self, primary, fallbacks=()):
        self.primary = primary
        self.fallbacks = tuple(fallbacks)
        self.last_source_id = getattr(primary, "source_id", "primary")

    def _run(self, method: str, *args):
        warnings: list[str] = []
        try:
            values, primary_warnings = getattr(self.primary, method)(*args)
        except Exception as error:  # noqa: BLE001
            values, primary_warnings = (), (f"primary_{method}_failed:{type(error).__name__}",)
        warnings.extend(primary_warnings)
        if values:
            self.last_source_id = getattr(self.primary, "source_id", "primary")
            return values, tuple(warnings)
        for fallback in self.fallbacks:
            try:
                values, fallback_warnings = getattr(fallback, method)(*args)
            except Exception as error:  # noqa: BLE001
                values, fallback_warnings = (), (f"{getattr(fallback, 'source_id', 'external')}_{method}_failed:{type(error).__name__}",)
            warnings.extend(fallback_warnings)
            if values:
                self.last_source_id = getattr(fallback, "source_id", "external")
                return values, tuple(warnings)
        return (), tuple(warnings)

    def fetch_indices(self):
        return self._run("fetch_indices")

    def fetch_stocks(self, symbols):
        return self._run("fetch_stocks", symbols)

    def fetch_minutes(self, instrument="sh000001"):
        return self._run("fetch_minutes", instrument)

    def fetch_minutes_by_index(
        self,
        instruments=("sh000001", "sz399001", "sz399006"),
    ):
        """Fetch each index independently through the configured fallback chain."""
        series = {}
        warnings = []
        for instrument in instruments:
            points, item_warnings = self.fetch_minutes(instrument)
            series[instrument] = points
            warnings.extend(item_warnings)
        return series, tuple(warnings)


def build_external_quote_source(primary, repository, client: httpx.Client):
    """Compose supported, explicitly enabled external sources around primary."""
    fallbacks = []
    tickflow_key = repository.enabled_key("tickflow")
    if tickflow_key:
        fallbacks.append(TickFlowQuoteSource(client, tickflow_key))
    tushare_key = repository.enabled_key("tushare")
    if tushare_key:
        fallbacks.append(TushareQuoteSource(client, tushare_key))
    # Fuyao is intentionally excluded until its public quote contract is
    # verified; a connection test alone is not enough to claim data support.
    return ExternalQuoteFallbackSource(primary, fallbacks)
