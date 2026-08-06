import itertools
import logging
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from statistics import median
from typing import Callable, Iterable
from urllib.parse import urlparse

import httpx

from qibao_api.contracts.market_overview import (
    OverviewBreadth,
    OverviewFeatureStock,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewMarketSnapshot,
    OverviewRegimeMetrics,
    OverviewSector,
    OverviewSectorStock,
)
from qibao_api.gongbu.tdx_local_professional import parse_tdx_professional_rows


logger = logging.getLogger(__name__)
HUNDRED = Decimal("100")
PRICE_TICK = Decimal("0.01")
TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class TdxRealtimeQuote:
    symbol: str
    exchange_code: str
    name: str
    previous_close: Decimal
    price: Decimal
    high: Decimal
    low: Decimal
    open: Decimal
    volume: Decimal
    amount_wan: Decimal
    observed_at: datetime | None = None
    market_cap_yi: Decimal | None = None

    @property
    def change_percent(self) -> Decimal:
        if self.previous_close <= 0:
            return Decimal()
        return (
            (self.price - self.previous_close) / self.previous_close * HUNDRED
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class TdxJsonRpcClient:
    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:17709/",
        timeout_seconds: float = 3.0,
    ) -> None:
        self.endpoint = endpoint
        self.client = httpx.Client(timeout=timeout_seconds)
        self._ids = itertools.count(1)
        self._id_lock = threading.Lock()

    def call(self, method: str, params: dict) -> object:
        with self._id_lock:
            request_id = next(self._ids)
        response = self.client.post(
            self.endpoint,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise OSError(f"TDX JSON-RPC error: {payload['error'].get('code')}")
        return payload.get("result")

    def available(self) -> bool:
        parsed = urlparse(self.endpoint)
        if not parsed.hostname or not parsed.port:
            return False
        try:
            with socket.create_connection(
                (parsed.hostname, parsed.port), timeout=0.1
            ):
                return True
        except OSError:
            return False

    def close(self) -> None:
        self.client.close()


_TDX_READ_ONLY_PROBES: tuple[tuple[str, str, str, dict], ...] = (
    ("catalog", "证券目录", "get_stock_list", {"market": "5", "list_type": 1}),
    ("snapshot", "实时行情", "get_market_snapshot", {"stock_code": "{stock_code}", "field_list": []}),
    ("sectors", "板块目录", "get_sector_list", {"list_type": 1}),
    ("more_info", "扩展行情与估值", "get_more_info", {"stock_code": "{stock_code}"}),
    ("stock_info", "基础财务与行业", "get_stock_info", {"stock_code": "{stock_code}"}),
    ("ipo", "新股与新债日历", "get_ipo_info", {"market": "5"}),
    ("kzz", "可转债条款", "get_kzz_info", {"stock_code": "{stock_code}"}),
    ("formula", "通达信公式计算", "formula_process_mul_zb", {"stock_list": ["{stock_code}"]}),
    ("professional_finance", "专业财务表", "get_financial_data", {
        "stock_list": ["{stock_code}"], "table_list": ["Fn193"],
        "start_time": "", "end_time": "", "report_type": "report_time",
    }),
    ("professional_stock_trade", "个股交易表", "get_gpjy_value", {
        "stock_list": ["{stock_code}"], "table_list": ["GP1"],
        "start_time": "", "end_time": "",
    }),
    ("professional_sector_trade", "板块交易表", "get_bkjy_value", {
        "stock_list": ["880660.SH"], "table_list": ["BK5"],
        "start_time": "", "end_time": "",
    }),
    ("professional_market_trade", "市场交易表", "get_scjy_value", {
        "table_list": ["SC1"], "start_time": "", "end_time": "",
    }),
    ("professional_stock_single", "个股单项表", "get_gp_one_data", {
        "stock_list": ["{stock_code}"], "table_list": ["GO1"],
    }),
)


def tdx_read_only_capability_catalog() -> tuple[dict[str, str], ...]:
    return tuple(
        {"key": key, "label": label, "method": method}
        for key, label, method, _params in _TDX_READ_ONLY_PROBES
    )


def _probe_result_is_usable(key: str, result: object, *, method: str | None = None) -> bool:
    if result is None:
        return False
    if key.startswith("professional_") and method is not None:
        # The local JSON-RPC bridge must expose its explicit ErrorId contract.
        # Official Python TdxQuant responses are parsed by the dedicated lazy
        # adapter, but an unwrapped list from the bridge is not verified data.
        if not isinstance(result, dict) or "ErrorId" not in result:
            return False
        if str(result.get("ErrorId")) != "0":
            return False
        try:
            parse_tdx_professional_rows(
                result,
                method=method,
                fetched_at=datetime.now(timezone.utc),
            )
        except (ValueError, RuntimeError):
            return False
        return True
    if isinstance(result, dict):
        if "ErrorId" in result and str(result.get("ErrorId")) != "0":
            return False
        if key in {"catalog", "sectors", "ipo"}:
            return isinstance(result.get("Value"), list) and bool(result.get("Value"))
        if key == "snapshot":
            return any(result.get(field) not in (None, "", "--") for field in ("Now", "LastClose", "Price"))
        return len(result) > 1
    if isinstance(result, (list, tuple, set)):
        return bool(result)
    return True


def probe_tdx_capabilities(rpc, *, stock_code: str = "600000.SH") -> dict[str, object]:
    """Probe only read-only TDX methods and return honest capability state.

    The probe intentionally treats unsupported methods and missing professional
    data packages as unavailable; it never substitutes a different field or
    calls any trading/account endpoint.
    """
    capabilities: list[dict[str, str]] = []
    reachable = bool(getattr(rpc, "available", lambda: False)())
    if not reachable:
        for key, label, method, _params in _TDX_READ_ONLY_PROBES:
            capabilities.append({
                "key": key,
                "label": label,
                "method": method,
                "status": "unavailable",
                "detail": "本地桥接端口不可达",
            })
        return {
            "status": "unavailable",
            "reachable": False,
            "capabilities": tuple(capabilities),
        }

    for key, label, method, template in _TDX_READ_ONLY_PROBES:
        params = {
            name: (
                [
                    item.replace("{stock_code}", stock_code)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
                if isinstance(value, list)
                else value.replace("{stock_code}", stock_code)
                if isinstance(value, str)
                else value
            )
            for name, value in template.items()
        }
        try:
            result = rpc.call(method, params)
            if not _probe_result_is_usable(key, result, method=method):
                raise ValueError("empty or invalid response")
        except Exception as error:  # probe must continue and report each method independently
            capabilities.append({
                "key": key,
                "label": label,
                "method": method,
                "status": "unavailable",
                "detail": f"接口不可用（{type(error).__name__}）",
            })
        else:
            capabilities.append({
                "key": key,
                "label": label,
                "method": method,
                "status": "ready",
                "detail": "只读接口返回响应",
            })

    ready_count = sum(item["status"] == "ready" for item in capabilities)
    return {
        "status": "ready" if ready_count == len(capabilities) else "partial" if ready_count else "unavailable",
        "reachable": True,
        "capabilities": tuple(capabilities),
    }


def _decimal(value: object) -> Decimal | None:
    if value in (None, "", "--"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_tdx_snapshot(
    exchange_code: str,
    name: str,
    payload: object,
) -> TdxRealtimeQuote | None:
    if not isinstance(payload, dict) or str(payload.get("ErrorId")) != "0":
        return None
    previous_close = _decimal(payload.get("LastClose"))
    price = _decimal(payload.get("Now"))
    high = _decimal(payload.get("Max"))
    low = _decimal(payload.get("Min"))
    opening = _decimal(payload.get("Open"))
    volume = _decimal(payload.get("Volume"))
    amount_wan = _decimal(payload.get("Amount"))
    # Only accept an explicitly hundred-million-yuan field. TDX builds differ in
    # the units of generic MarketValue/MarketCap fields, so those are ignored
    # instead of being silently converted into a false market-cap value.
    market_cap_yi = _decimal(payload.get("MarketCapYi") or payload.get("market_cap_yi"))
    if market_cap_yi is not None and market_cap_yi < 0:
        market_cap_yi = None
    if (
        previous_close is None
        or price is None
        or previous_close <= 0
        or price <= 0
    ):
        return None
    symbol = exchange_code.split(".", 1)[0]
    if len(symbol) != 6 or not symbol.isdigit():
        return None
    return TdxRealtimeQuote(
        symbol=symbol,
        exchange_code=exchange_code,
        name=name.strip() or symbol,
        previous_close=previous_close,
        price=price,
        high=high if high is not None and high > 0 else price,
        low=low if low is not None and low > 0 else price,
        open=opening if opening is not None and opening > 0 else previous_close,
        volume=volume if volume is not None and volume >= 0 else Decimal(),
        amount_wan=amount_wan if amount_wan is not None and amount_wan >= 0 else Decimal(),
        market_cap_yi=market_cap_yi,
    )


def _price_limit_rate(quote: TdxRealtimeQuote) -> Decimal:
    if quote.symbol.startswith(("300", "301", "688", "689")):
        return Decimal("0.20")
    if quote.symbol.startswith(("4", "8")):
        return Decimal("0.30")
    if "ST" in quote.name.upper():
        return Decimal("0.05")
    return Decimal("0.10")


def _limit_price(quote: TdxRealtimeQuote, direction: int) -> Decimal:
    rate = _price_limit_rate(quote) * Decimal(direction)
    return (quote.previous_close * (Decimal(1) + rate)).quantize(
        PRICE_TICK,
        rounding=ROUND_HALF_UP,
    )


def build_market_statistics(
    quotes: Iterable[TdxRealtimeQuote],
    *,
    observed_at: datetime,
    universe_count: int | None = None,
    sectors: tuple[OverviewSector, ...] = (),
    sector_stocks: dict[str, tuple[OverviewSectorStock, ...]] | None = None,
    source: str = "tdx-local-rpc",
) -> OverviewMarketSnapshot:
    values = tuple(quotes)
    rising = sum(item.price > item.previous_close for item in values)
    falling = sum(item.price < item.previous_close for item in values)
    flat = len(values) - rising - falling
    limit_up = 0
    limit_down = 0
    broken = 0
    for item in values:
        upper = _limit_price(item, 1)
        lower = _limit_price(item, -1)
        if item.price >= upper:
            limit_up += 1
        elif item.high >= upper:
            broken += 1
        if item.price <= lower:
            limit_down += 1
    seal_rate = (
        Decimal(limit_up) / Decimal(limit_up + broken) * HUNDRED
        if limit_up + broken else None
    )
    total_amount_yi = (
        sum((item.amount_wan for item in values), Decimal()) / Decimal("10000")
    ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_universe = universe_count if universe_count is not None else len(values)
    coverage = Decimal(len(values)) / Decimal(total_universe) if total_universe else Decimal()
    quality = "ready" if coverage >= Decimal("0.80") else "partial"
    return OverviewMarketSnapshot(
        observed_at=observed_at,
        source=source,
        quality=quality,
        quote_count=len(values),
        universe_count=total_universe,
        median_change_percent=(
            Decimal(median(tuple(item.change_percent for item in values)))
            if values else None
        ),
        breadth=OverviewBreadth(
            rising_count=rising,
            falling_count=falling,
            flat_count=flat,
            valid_count=len(values),
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=limit_up,
            limit_down_count=limit_down,
            broken_limit_up_count=broken,
            seal_rate_percent=(
                seal_rate.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if seal_rate is not None else None
            ),
        ),
        liquidity=OverviewLiquidity(total_amount_yi=total_amount_yi),
        regime_metrics=_build_regime_metrics(values),
        sectors=sectors,
        sector_stocks=sector_stocks or {},
        market_stocks=_representative_stocks(
            values, observed_at=observed_at, source=source
        ),
    )


def _ratio(count: int, total: int) -> Decimal | None:
    if total <= 0:
        return None
    return (Decimal(count) / Decimal(total) * HUNDRED).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


def _close_position(quote: TdxRealtimeQuote) -> Decimal:
    price_range = max(quote.high - quote.low, Decimal("0.01"))
    return (quote.price - quote.low) / price_range * HUNDRED


def _build_regime_metrics(
    quotes: tuple[TdxRealtimeQuote, ...],
) -> OverviewRegimeMetrics:
    total = len(quotes)
    if total == 0:
        return OverviewRegimeMetrics()
    positions = {item.symbol: _close_position(item) for item in quotes}
    touched = [item for item in quotes if item.high >= _limit_price(item, 1)]
    failed_weak = sum(
        item.price < _limit_price(item, 1) * Decimal("0.97")
        for item in touched
    )
    panic = sum(
        (item.low / item.previous_close - Decimal(1)) * HUNDRED <= Decimal("-8")
        for item in quotes
    )
    high_amplitude = sum(
        (item.high - item.low) / item.previous_close * HUNDRED >= Decimal("10")
        for item in quotes
    )
    large_count = max(1, (total + 9) // 10)
    large_amount = sorted(
        quotes, key=lambda item: item.amount_wan, reverse=True
    )[:large_count]
    limit_up = sum(item.price >= _limit_price(item, 1) for item in quotes)
    limit_down = sum(item.price <= _limit_price(item, -1) for item in quotes)
    return OverviewRegimeMetrics(
        up_ratio=_ratio(sum(item.price > item.previous_close for item in quotes), total),
        zt_ratio=_ratio(limit_up, total),
        dt_ratio=_ratio(limit_down, total),
        median_ret=Decimal(median(tuple(item.change_percent for item in quotes))).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        ),
        amt_heat=None,
        strong_close_ratio=_ratio(
            sum(position >= Decimal("75") for position in positions.values()), total
        ),
        weak_close_ratio=_ratio(
            sum(position <= Decimal("25") for position in positions.values()), total
        ),
        limit_fail_ratio=_ratio(failed_weak, len(touched)),
        panic_ratio=_ratio(panic, total),
        amp_ratio=_ratio(high_amplitude, total),
        net_positive_ratio=None,
        large_amount_strong_close_ratio=_ratio(
            sum(positions[item.symbol] >= Decimal("75") for item in large_amount),
            len(large_amount),
        ),
        factor_coverage_percent=Decimal("81.82"),
    )


def _representative_stocks(
    quotes: tuple[TdxRealtimeQuote, ...],
    *,
    observed_at: datetime,
    source: str,
) -> tuple[OverviewFeatureStock, ...]:
    states = {item.symbol: _quote_state(item) for item in quotes}
    special = [item for item in quotes if states[item.symbol] != "active"]
    strongest = sorted(quotes, key=lambda item: item.change_percent, reverse=True)[:80]
    weakest = sorted(quotes, key=lambda item: item.change_percent)[:60]
    most_active = sorted(quotes, key=lambda item: item.amount_wan, reverse=True)[:80]
    selected: list[TdxRealtimeQuote] = []
    seen: set[str] = set()
    for item in (*special, *strongest, *weakest, *most_active):
        if item.symbol in seen:
            continue
        seen.add(item.symbol)
        selected.append(item)
    return tuple(
        OverviewFeatureStock(
            symbol=item.symbol,
            name=item.name,
            price=item.price,
            previous_close=item.previous_close,
            open=item.open,
            high=item.high,
            low=item.low,
            volume=item.volume,
            amount_yi=(item.amount_wan / Decimal("10000")).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            ),
            change_percent=item.change_percent,
            state=states[item.symbol],
            observed_at=observed_at,
            source=source,
            quality="ready",
        )
        for item in selected
    )


def _quote_state(
    quote: TdxRealtimeQuote,
) -> str:
    upper = _limit_price(quote, 1)
    lower = _limit_price(quote, -1)
    if quote.price >= upper:
        return "limit_up"
    if quote.high >= upper:
        return "broken_limit_up"
    if quote.price <= lower:
        return "limit_down"
    return "active"


def _is_a_share(exchange_code: str) -> bool:
    symbol, _, exchange = exchange_code.partition(".")
    if exchange == "SH":
        return symbol.startswith(("600", "601", "603", "605", "688", "689"))
    if exchange == "SZ":
        return symbol.startswith(("000", "001", "002", "003", "300", "301"))
    return False


def _catalog_rows(payload: object, *, a_shares_only: bool) -> tuple[tuple[str, str], ...]:
    if not isinstance(payload, dict) or str(payload.get("ErrorId")) != "0":
        return ()
    rows = payload.get("Value")
    if not isinstance(rows, list):
        return ()
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("Code") or "").strip()
        name = str(row.get("Name") or "").strip()
        if not code or not name or (a_shares_only and not _is_a_share(code)):
            continue
        result.append((code, name))
    return tuple(result)


class LocalTdxOverviewSource:
    def __init__(
        self,
        *,
        cache_path: Path,
        rpc: TdxJsonRpcClient | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        refresh_seconds: int = 15,
        max_workers: int = 16,
        initial_delay_seconds: float = 0,
        fallback=None,
    ) -> None:
        if initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must not be negative")
        self.cache_path = cache_path
        self.rpc = rpc
        self.clock = clock
        self.refresh_seconds = refresh_seconds
        self.max_workers = max_workers
        self.initial_delay_seconds = initial_delay_seconds
        self.fallback = fallback
        self._lock = threading.RLock()
        self._snapshot = self._load_cache()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._refresh_failure_count = 0
        self._last_refresh_error_type: str | None = None

    def current(self) -> OverviewMarketSnapshot | None:
        with self._lock:
            return self._snapshot

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._refresh_loop,
                name="tdx-overview-refresh",
                daemon=True,
            )
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        if self.rpc is not None:
            self.rpc.close()

    def refresh(self) -> OverviewMarketSnapshot:
        if self.rpc is None:
            if self.fallback is None:
                raise OSError("local TDX realtime bridge is disabled")
            return self._accept_fallback()
        available = getattr(self.rpc, "available", None)
        if self.fallback is not None and callable(available) and not available():
            return self._accept_fallback()
        try:
            return self._refresh_rpc()
        except (OSError, ValueError, httpx.HTTPError):
            if self.fallback is None:
                raise
            return self._accept_fallback()

    def _refresh_rpc(self) -> OverviewMarketSnapshot:
        rpc = self._require_rpc()
        stock_catalog = _catalog_rows(
            rpc.call("get_stock_list", {"market": "5", "list_type": 1}),
            a_shares_only=True,
        )
        if not stock_catalog:
            raise OSError("local TDX stock catalog is unavailable")
        quotes = self._fetch_quotes(stock_catalog)
        if not quotes:
            raise OSError("local TDX realtime quotes are unavailable")
        by_symbol = {item.symbol: item for item in quotes}
        sectors, sector_stocks = self._build_sectors(by_symbol)
        snapshot = build_market_statistics(
            quotes,
            observed_at=self.clock(),
            universe_count=len(stock_catalog),
            sectors=sectors,
            sector_stocks=sector_stocks,
        )
        with self._lock:
            self._snapshot = snapshot
        self._save_cache(snapshot)
        return snapshot

    def _accept_fallback(self) -> OverviewMarketSnapshot:
        snapshot = self.fallback.fetch()
        with self._lock:
            self._snapshot = snapshot
        self._save_cache(snapshot)
        return snapshot

    def _refresh_loop(self) -> None:
        if self._stop.wait(self.initial_delay_seconds):
            return
        while not self._stop.is_set():
            try:
                self.refresh()
                self._record_refresh_success()
            except Exception as error:
                self._record_refresh_failure(error)
            if self._stop.wait(self.refresh_seconds):
                break

    def _record_refresh_failure(self, error: Exception) -> None:
        error_type = type(error).__name__
        self._refresh_failure_count += 1
        should_log = (
            self._refresh_failure_count == 1
            or error_type != self._last_refresh_error_type
            or self._refresh_failure_count % 20 == 0
        )
        if should_log:
            logger.warning(
                "local TDX overview refresh failed; error_type=%s failures=%s",
                error_type,
                self._refresh_failure_count,
                exc_info=True,
            )
        self._last_refresh_error_type = error_type

    def _record_refresh_success(self) -> None:
        if self._refresh_failure_count > 0:
            logger.info(
                "local TDX overview refresh recovered after %s failures",
                self._refresh_failure_count,
            )
        self._refresh_failure_count = 0
        self._last_refresh_error_type = None

    def _fetch_quotes(
        self,
        catalog: tuple[tuple[str, str], ...],
    ) -> tuple[TdxRealtimeQuote, ...]:
        rpc = self._require_rpc()

        def fetch(row: tuple[str, str]) -> TdxRealtimeQuote | None:
            code, name = row
            try:
                payload = rpc.call(
                    "get_market_snapshot",
                    {"stock_code": code, "field_list": []},
                )
                return parse_tdx_snapshot(code, name, payload)
            except (OSError, ValueError, httpx.HTTPError):
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            return tuple(item for item in executor.map(fetch, catalog) if item is not None)

    def _build_sectors(
        self,
        quotes_by_symbol: dict[str, TdxRealtimeQuote],
    ) -> tuple[tuple[OverviewSector, ...], dict[str, tuple[OverviewSectorStock, ...]]]:
        rpc = self._require_rpc()
        sector_catalog = _catalog_rows(
            rpc.call("get_sector_list", {"list_type": 1}),
            a_shares_only=False,
        )
        sector_quotes = self._fetch_quotes(sector_catalog)
        ranked = sorted(sector_quotes, key=lambda item: item.change_percent, reverse=True)
        sectors: list[OverviewSector] = []
        stocks_by_sector: dict[str, tuple[OverviewSectorStock, ...]] = {}
        for sector_quote in ranked[:40]:
            try:
                members_payload = rpc.call(
                    "get_stock_list_in_sector",
                    {
                        "block_code": sector_quote.exchange_code,
                        "block_type": 0,
                        "list_type": 1,
                    },
                )
            except (OSError, ValueError, httpx.HTTPError):
                continue
            members = _catalog_rows(members_payload, a_shares_only=True)
            member_quotes = [
                quotes_by_symbol[code.split(".", 1)[0]]
                for code, _name in members
                if code.split(".", 1)[0] in quotes_by_symbol
            ]
            if len(member_quotes) < 3:
                continue
            member_quotes.sort(key=lambda item: item.change_percent, reverse=True)
            sector_id = f"tdx-{sector_quote.exchange_code.replace('.', '-').lower()}"
            stocks = tuple(
                OverviewSectorStock(
                    symbol=item.symbol,
                    name=item.name,
                    change_percent=item.change_percent,
                    amount_yi=(item.amount_wan / Decimal("10000")).quantize(
                        TWO_PLACES, rounding=ROUND_HALF_UP
                    ),
                    market_cap_yi=item.market_cap_yi,
                    first_limit_time=None,
                    position=(
                        "涨停" if item.price >= _limit_price(item, 1)
                        else "领涨" if index < 3 else "成分股"
                    ),
                    quality="ready",
                )
                for index, item in enumerate(member_quotes[:30])
            )
            sectors.append(OverviewSector(
                sector_id=sector_id,
                name=sector_quote.name,
                change_percent=sector_quote.change_percent,
                amount_yi=(sector_quote.amount_wan / Decimal("10000")).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                ),
                limit_up_count=sum(item.price >= _limit_price(item, 1) for item in member_quotes),
                rising_count=sum(item.price > item.previous_close for item in member_quotes),
                falling_count=sum(item.price < item.previous_close for item in member_quotes),
                stock_count=len(member_quotes),
            ))
            stocks_by_sector[sector_id] = stocks
            if len(sectors) >= 12:
                break
        return tuple(sectors), stocks_by_sector

    def _require_rpc(self) -> TdxJsonRpcClient:
        if self.rpc is None:
            raise OSError("local TDX realtime bridge is disabled")
        return self.rpc

    def _load_cache(self) -> OverviewMarketSnapshot | None:
        if not self.cache_path.exists():
            return None
        try:
            return OverviewMarketSnapshot.model_validate_json(
                self.cache_path.read_text(encoding="utf-8")
            ).model_copy(update={"quality": "stale"})
        except (OSError, ValueError):
            logger.warning("local TDX overview cache is invalid", exc_info=True)
            return None

    def _save_cache(self, snapshot: OverviewMarketSnapshot) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        try:
            temporary.write_text(snapshot.model_dump_json(), encoding="utf-8")
            temporary.replace(self.cache_path)
        except OSError:
            logger.warning("local TDX overview cache write failed", exc_info=True)
