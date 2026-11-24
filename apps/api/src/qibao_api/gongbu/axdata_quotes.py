"""Use AxData's stateless Tencent provider, not its storage, registry or scheduler."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from threading import Lock
from time import monotonic, perf_counter
from zoneinfo import ZoneInfo

from qibao_api.contracts.market_overview import OverviewIndexQuote, OverviewStockQuote
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.gongbu.tencent_quotes import market_prefix


def _make_adapter():
    from axdata_core.adapters.tencent.request import TencentRequestAdapter
    return TencentRequestAdapter(timeout=3)


class AxDataTencentQuoteSource:
    source_id = "axdata-tencent"
    upstream_source = "tencent"

    def __init__(self, *, factory=_make_adapter, observer=None, clock=lambda: datetime.now(timezone.utc)):
        self.factory, self.clock, self.observer = factory, clock, observer
        self._retry_after = 0.0
        self._lock = Lock()

    def _call(self, operation, query):
        started, error = perf_counter(), None
        try:
            with self._lock:
                if monotonic() < self._retry_after:
                    raise RuntimeError("AxData 腾讯接口冷却中")
            return query()
        except Exception as reason:
            error = reason
            with self._lock:
                if monotonic() >= self._retry_after:
                    self._retry_after = monotonic() + 30
            raise
        finally:
            if self.observer:
                try:
                    self.observer(SourceAttemptEvent(source=self.source_id, operation=operation,
                        target="overview", status="error" if error else "ready",
                        error_code=type(error).__name__ if error else None,
                        latency_ms=round((perf_counter() - started) * 1000), observed_at=self.clock(),
                        metadata={"upstream": "tencent", "client": "axdata"}))
                except Exception:
                    pass

    def _rows(self, codes):
        # Each operation owns its adapter; no mutable SDK sessions or second database.
        adapter = self.factory()
        rows = []
        for start in range(0, len(codes), 80):
            rows.extend(adapter.request("tencent_realtime_snapshot", {"code": codes[start:start + 80]}))
        if not rows:
            raise ValueError("AxData 腾讯未返回行情")
        return rows

    def _time(self, row):
        value = datetime.strptime(str(row["quote_time"]), "%Y%m%d%H%M%S").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        # Tencent servers can lead a correctly configured client by a few seconds.
        # Keep the original timestamp and flag the skew; reject larger anomalies.
        if value > self.clock() + timedelta(seconds=30):
            raise ValueError("AxData 返回未来行情时间")
        return value

    def fetch_stocks(self, symbols):
        if not symbols:
            return (), ()
        symbols = tuple(dict.fromkeys(symbols))
        for symbol in symbols:
            validate_a_share_code(symbol)
        return self._call("stocks", lambda: self._fetch_stocks(symbols))

    def _fetch_stocks(self, symbols):
        codes = [f"{symbol}.{market_prefix(symbol).upper()}" for symbol in symbols]
        wanted = dict(zip(codes, symbols))
        result = {}
        for row in self._rows(codes):
            code = row.get("instrument_id")
            if code not in wanted or row.get("symbol") != wanted[code]:
                raise ValueError("AxData 返回未请求的证券")
            if code in result:
                raise ValueError("AxData 返回重复证券")
            result[code] = OverviewStockQuote(symbol=wanted[code], name=row["name"],
                change_percent=Decimal(str(row["change_pct"])),
                amount_yi=None if row.get("amount") is None else Decimal(str(row["amount"])) / 100000000,
                market_cap_yi=None if row.get("total_market_value") is None else Decimal(str(row["total_market_value"])),
                turnover_rate=None if row.get("turnover_rate") is None else Decimal(str(row["turnover_rate"])),
                observed_at=self._time(row))
        missing = tuple(f"axdata_quote_missing:{code}" for code in codes if code not in result)
        skew = ("axdata_clock_skew_within_30s",) if any(q.observed_at > self.clock() for q in result.values()) else ()
        return tuple(result[code] for code in codes if code in result), ("axdata_upstream_tencent", *missing, *skew)

    def fetch_indices(self):
        return self._call("indices", self._fetch_indices)

    def _fetch_indices(self):
        codes = {"000001.SH": "sh000001", "399001.SZ": "sz399001", "399006.SZ": "sz399006"}
        result = []
        seen = set()
        for row in self._rows(list(codes)):
            code = row.get("instrument_id")
            if code not in codes or code in seen:
                raise ValueError("AxData 返回重复或未请求指数")
            seen.add(code)
            observed = self._time(row)
            result.append(OverviewIndexQuote(instrument=codes[code], name=row["name"],
                value=Decimal(str(row["last_price"])), change=Decimal(str(row["change"])),
                change_percent=Decimal(str(row["change_pct"])), observed_at=observed,
                source=self.source_id, quality="stale" if (self.clock() - observed).total_seconds() > 180 else "ready"))
        missing = tuple(f"axdata_quote_missing:{code}" for code in codes if code not in seen)
        skew = ("axdata_clock_skew_within_30s",) if any(q.observed_at > self.clock() for q in result) else ()
        return tuple(result), ("axdata_upstream_tencent", *missing, *skew)

    def fetch_minutes(self, instrument="sh000001"):
        return (), ("axdata_tencent_minutes_not_enabled",)
