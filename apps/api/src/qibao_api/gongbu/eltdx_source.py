"""Bounded, lazy pooled TDX transport; never guess a quote's trading date."""
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from threading import RLock
from time import monotonic, perf_counter
from zoneinfo import ZoneInfo

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.market_overview import OverviewIndexQuote
from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.gongbu.tdx_history import DataSourceUnavailable
from qibao_api.gongbu.tencent_quotes import market_prefix

CHINA = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class _MinuteTick:
    observed_at: datetime
    price: Decimal


def _make_client():
    from eltdx import TdxClient
    from qibao_api.gongbu.tdx_client import TDX_SERVERS

    return TdxClient.from_hosts(
        hosts=[f"{host}:{port}" for host, port in TDX_SERVERS],
        server_count=2, connections_per_server=2, runtime_workers=2,
        timeout=3, probe_hosts=False, max_pending_requests=16,
        global_raw_bytes=8 * 1024 * 1024, global_decoded_bytes=32 * 1024 * 1024,
    )


class EltdxSource:
    source_name = source_id = "eltdx"
    upstream_source = "tdx"

    def __init__(self, *, factory=_make_client, observer=None, clock=lambda: datetime.now(timezone.utc)):
        self.factory, self.observer, self.clock = factory, observer, clock
        self._client = None
        self._lock = RLock()
        self._retry_after = {}
        self._transport_retry_after = 0.0
        self._closed = False

    def _get_client(self):
        with self._lock:
            if self._closed:
                raise DataSourceUnavailable("eltdx source closed")
            if self._client is None:
                try:
                    self._client = self.factory()
                except Exception:
                    self._transport_retry_after = monotonic() + 30
                    raise
            return self._client

    def _call(self, operation, target, query):
        started = perf_counter()
        error = None
        key = (operation, target)
        try:
            with self._lock:
                if monotonic() < max(self._retry_after.get(key, 0), self._transport_retry_after):
                    raise DataSourceUnavailable("eltdx 暂时冷却，使用其他来源")
            result = query(self._get_client())
            with self._lock:
                self._retry_after.pop(key, None)
            return result
        except Exception as reason:
            error = reason
            try:
                from eltdx.exceptions import TransportError
                transport_failed = isinstance(reason, TransportError)
            except ImportError:
                transport_failed = False
            with self._lock:
                if transport_failed:
                    self._transport_retry_after = monotonic() + 30
                # Unsupported intraday responses must not disable daily repair.
                self._retry_after.setdefault(key, 0)
                if monotonic() >= self._retry_after[key]:
                    self._retry_after[key] = monotonic() + 30
                if len(self._retry_after) > 1024:
                    self._retry_after = {k: v for k, v in self._retry_after.items() if v > monotonic()}
            raise
        finally:
            if self.observer is not None:
                try:
                    self.observer(SourceAttemptEvent(
                        source="eltdx", operation=operation, target=target,
                        status="error" if error else "ready", error_code=type(error).__name__ if error else None,
                        latency_ms=round((perf_counter() - started) * 1000), observed_at=self.clock(),
                        metadata={"upstream": "tdx", "client": "eltdx"},
                    ))
                except Exception:
                    pass  # Health reporting must not break a successful data request.

    def fetch_daily(self, symbol: str, limit: int = 250) -> list[DailyBar]:
        validate_a_share_code(symbol)
        if not 1 <= limit <= 4000:
            raise ValueError("eltdx daily limit must be between 1 and 4000")
        code = f"{market_prefix(symbol)}{symbol}"

        def query(client):
            values = []
            for offset in range(0, limit, 800):
                series = client.bars.get(code, period="day", start=offset,
                                         count=min(800, limit - offset), adjust="none")
                if series.full_code != code or series.adjust_mode != "none":
                    raise ValueError("eltdx 返回的证券或复权口径不匹配")
                for bar in series.bars:
                    volume = Decimal(str(bar.volume_wire_value))
                    if not volume.is_finite() or volume < 0 or volume != volume.to_integral_value():
                        raise ValueError("eltdx 成交股数无效")
                    day = bar.time.astimezone(CHINA).date() if bar.time.tzinfo else bar.time.date()
                    if day > self.clock().astimezone(CHINA).date():
                        raise ValueError("eltdx 日线日期位于未来")
                    values.append(DailyBar(
                        symbol=symbol, trade_date=day, open=Decimal(str(bar.open)),
                        high=Decimal(str(bar.high)), low=Decimal(str(bar.low)), close=Decimal(str(bar.close)),
                        volume=int(volume), amount=Decimal(str(bar.amount)), source="eltdx",
                    ))
                if len(series.bars) < min(800, limit - offset):
                    break
            if not values or len({bar.trade_date for bar in values}) != len(values):
                raise DataSourceUnavailable("eltdx 未返回有效且日期唯一的日线")
            return sorted(values, key=lambda bar: bar.trade_date)

        return self._call("daily", code, query)

    def _minutes(self, instrument):
        def query(client):
            # today() lacks a full date and recent() may return no points.
            # Derive a verifiable date from the latest dated bar, not the PC clock.
            latest = client.bars.get(instrument, period="day", count=1, adjust="none")
            if latest.full_code != instrument or latest.adjust_mode != "none" or not latest.bars:
                raise ValueError("eltdx 无可核验的最新交易日期")
            day = latest.bars[-1].time.date()
            series = client.minutes.history(instrument, day)
            if series.full_code != instrument or series.trading_date != day:
                raise ValueError("eltdx 分时证券或交易日期不可核验")
            points = []
            for point in series.points:
                if point.time is None:
                    raise ValueError("eltdx 分时缺少完整时间")
                observed = point.time.replace(tzinfo=CHINA) if point.time.tzinfo is None else point.time.astimezone(CHINA)
                if observed.date() != series.trading_date or observed > self.clock().astimezone(CHINA):
                    raise ValueError("eltdx 分时日期异常")
                if not ("09:30" <= observed.strftime("%H:%M") <= "11:30" or "13:00" <= observed.strftime("%H:%M") <= "15:00"):
                    continue
                price = Decimal(str(point.price))
                if not price.is_finite() or price <= 0:
                    raise ValueError("eltdx 分时价格无效")
                points.append(_MinuteTick(observed_at=observed, price=price))
            if not points or len({p.observed_at for p in points}) != len(points):
                raise DataSourceUnavailable("eltdx 无可核验的分时记录")
            return series, tuple(sorted(points, key=lambda p: p.observed_at))
        return self._call("minutes", instrument, query)

    def fetch_minutes(self, instrument="sh000001"):
        # This upstream has no actual per-minute amount. The application requires
        # it; do not invent zero or price*volume and pretend it is actual amount.
        return (), ("eltdx_minute_actual_amount_unavailable",)

    def fetch_indices(self):
        result, warnings = [], ["eltdx_upstream_tdx"]
        for code, name in (("sh000001", "上证指数"), ("sz399001", "深证成指"), ("sz399006", "创业板指")):
            try:
                series, points = self._minutes(code)
                previous = Decimal(str(series.prev_close))
                if not previous.is_finite() or previous <= 0:
                    raise ValueError("previous close unavailable")
                point = points[-1]
                change = point.price - previous
                result.append(OverviewIndexQuote(instrument=code, name=name, value=point.price,
                    change=change, change_percent=change / previous * 100, observed_at=point.observed_at,
                    source="eltdx", quality="stale" if (self.clock() - point.observed_at).total_seconds() > 180 else "ready"))
            except Exception as error:
                warnings.append(f"eltdx_index_unavailable:{code}:{type(error).__name__}")
        return tuple(result), tuple(warnings)

    def fetch_stocks(self, symbols):
        # Native snapshots do not carry a full date. Do not stamp them with today's date.
        return (), ("eltdx_snapshot_date_unverified",)

    def close(self):
        with self._lock:
            self._closed = True
            client, self._client = self._client, None
        if client is not None:
            client.close()
