import time
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.gongbu.tdx_history import DataSourceUnavailable

BAIDU_KLINE_URL = "https://finance.pae.baidu.com/selfselect/getstockquotation"
REQUIRED_KLINE_KEYS = frozenset(
    {"time", "open", "high", "low", "close", "volume", "amount"}
)


class BaiduHistorySource:
    source_name = "baidu"

    def __init__(
        self,
        client: httpx.Client,
        observer: Callable[[SourceAttemptEvent], None] | None = None,
    ) -> None:
        self.client = client
        self.observer = observer

    def _record(
        self,
        *,
        status: str,
        started: float,
        error_code: str | None = None,
        metadata: dict[str, str | int] | None = None,
    ) -> None:
        if self.observer is None:
            return
        event = SourceAttemptEvent(
            source="baidu",
            operation="history",
            target=BAIDU_KLINE_URL,
            status=status,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            observed_at=datetime.now(timezone.utc),
            error_code=error_code,
            metadata=metadata or {},
        )
        try:
            self.observer(event)
        except Exception:
            return

    def fetch_daily(self, symbol: str, limit: int = 250) -> list[DailyBar]:
        started = time.perf_counter()
        try:
            response = self.client.get(
                BAIDU_KLINE_URL,
                params={
                    "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
                    "isFutures": "false", "isStock": "true", "newFormat": "1",
                    "group": "quotation_kline_ab", "finClientType": "pc", "code": symbol,
                    "start_time": "", "ktype": "1",
                },
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/vnd.finance-web.v1+json",
                    "Origin": "https://gushitong.baidu.com",
                    "Referer": "https://gushitong.baidu.com/",
                },
                timeout=httpx.Timeout(8, connect=3),
            )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("ResultCode", -1)) != "0":
                raise DataSourceUnavailable("Baidu K-line source returned an error")
            result = payload.get("Result")
            if not isinstance(result, dict):
                raise DataSourceUnavailable(
                    "Baidu K-line source returned no daily bars"
                )
            market_data = result.get("newMarketData", {})
            keys = market_data.get("keys") or []
            rows = [row for row in (market_data.get("marketData") or "").split(";") if row]
            bars = self._parse_batch(symbol, keys, rows)
            if not bars:
                raise DataSourceUnavailable("Baidu K-line source returned no daily bars")
            sorted_bars = sorted(bars, key=lambda item: item.trade_date)[-limit:]
            self._record(
                status="ready",
                started=started,
                metadata={
                    "field_count": len(keys),
                    "latest_trade_date": max(item.trade_date for item in sorted_bars).isoformat(),
                    "row_count": len(sorted_bars),
                    "validation": "schema_ohlc_unique_dates",
                },
            )
            return sorted_bars
        except Exception as error:
            self._record(
                status="error",
                started=started,
                error_code=type(error).__name__,
            )
            raise

    def _parse_batch(
        self,
        symbol: str,
        keys: list[str],
        rows: list[str],
    ) -> list[DailyBar]:
        if REQUIRED_KLINE_KEYS.difference(keys):
            raise DataSourceUnavailable(
                "Baidu K-line source missing required keys"
            )

        bars = []
        seen_dates = set()
        for row in rows:
            if len(row.split(",")) != len(keys):
                raise DataSourceUnavailable("Baidu K-line row width is invalid")
            try:
                bar = self._parse_row(symbol, keys, row)
            except (InvalidOperation, KeyError, ValueError) as error:
                raise DataSourceUnavailable(
                    "Baidu K-line row is invalid"
                ) from error
            if bar.trade_date in seen_dates:
                raise DataSourceUnavailable(
                    "Baidu K-line duplicate trade date"
                )
            seen_dates.add(bar.trade_date)
            bars.append(bar)
        return bars

    @staticmethod
    def _parse_row(symbol: str, keys: list[str], row: str) -> DailyBar:
        values = row.split(",")
        data = dict(zip(keys, values, strict=False))
        open_price = Decimal(data["open"])
        high_price = Decimal(data["high"])
        low_price = Decimal(data["low"])
        close_price = Decimal(data["close"])
        if (
            min(open_price, high_price, low_price, close_price) <= 0
            or high_price < max(open_price, close_price)
            or low_price > min(open_price, close_price)
            or high_price < low_price
        ):
            raise DataSourceUnavailable("Baidu K-line invalid OHLC bounds")
        return DailyBar(
            symbol=symbol,
            trade_date=data["time"],
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=int(Decimal(data["volume"])),
            amount=Decimal(data["amount"]),
            source="baidu",
        )
