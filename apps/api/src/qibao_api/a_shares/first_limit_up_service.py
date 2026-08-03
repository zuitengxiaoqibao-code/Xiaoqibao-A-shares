import inspect
import re
from collections.abc import Callable, Sequence
from datetime import date, datetime, timezone

import httpx

from qibao_api.a_shares.first_limit_up import (
    MINIMUM_DAILY_HISTORY,
    evaluate_first_limit_up,
    is_limit_up,
    refresh_candidate_state,
    limit_rate_for_symbol,
)
from qibao_api.a_shares.first_limit_up_repository import FirstLimitUpRepository
from qibao_api.contracts.first_limit_up import (
    FIRST_LIMIT_UP_RULE_VERSION,
    FirstLimitUpBoard,
    FirstLimitUpCandidate,
)
from qibao_api.gongbu.tencent_quotes import market_prefix, parse_tencent_snapshot


class FirstLimitUpService:
    def __init__(
        self,
        *,
        bar_repository,
        quote_source,
        repository: FirstLimitUpRepository,
        universe_provider=None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        pool_limit: int = 120,
    ) -> None:
        self.bar_repository = bar_repository
        self.quote_source = quote_source
        self.repository = repository
        self.universe_provider = universe_provider
        self.clock = clock
        self.pool_limit = pool_limit
        self._missing_data: tuple[str, ...] = ()

    async def refresh(self, as_of: date) -> FirstLimitUpBoard:
        missing: list[str] = []
        eligible_symbols = tuple(
            self.bar_repository.symbols_with_history(MINIMUM_DAILY_HISTORY, as_of)
        )
        active_symbols = self._active_symbols(eligible_symbols)
        eligible_set = set(eligible_symbols)
        symbols = tuple(symbol for symbol in active_symbols if symbol in eligible_set)
        histories = self.bar_repository.latest_many(symbols, 300, as_of)
        covered_symbols = tuple(
            symbol
            for symbol in symbols
            if len(histories.get(symbol, ())) >= MINIMUM_DAILY_HISTORY
        )
        universe_count = len(active_symbols)
        history_eligible_count = len(symbols)
        scan_coverage_count = len(covered_symbols)
        coverage_complete = universe_count > 0 and scan_coverage_count == universe_count
        latest_dates = [
            bars[-1].trade_date for bars in histories.values() if bars
        ]
        scan_date = max(latest_dates, default=as_of)
        eligible_events: list[tuple[str, list, list[date]]] = []
        for symbol in symbols:
            bars = sorted(histories.get(symbol, []), key=lambda item: item.trade_date)
            if len(bars) < 2:
                continue
            limit_rate = limit_rate_for_symbol(symbol)
            event_dates = [
                current.trade_date
                for previous, current in zip(bars, bars[1:])
                if current.trade_date <= scan_date
                and is_limit_up(previous.close, current.close, limit_rate)
            ]
            if not event_dates:
                continue
            eligible_events.append((symbol, bars, event_dates))

        batch_snapshots = None
        fetch_many = getattr(self.quote_source, "fetch_many", None)
        if callable(fetch_many) and eligible_events:
            try:
                batch_snapshots = fetch_many(tuple(item[0] for item in eligible_events))
                if inspect.isawaitable(batch_snapshots):
                    batch_snapshots = await batch_snapshots
                batch_snapshots = dict(batch_snapshots)
            except Exception:
                batch_snapshots = {}
                missing.append("quote_source_unavailable")

        today: list[FirstLimitUpCandidate] = []
        for symbol, bars, event_dates in eligible_events:
            try:
                if batch_snapshots is None:
                    snapshot = self.quote_source.fetch_snapshot(symbol)
                    if inspect.isawaitable(snapshot):
                        snapshot = await snapshot
                else:
                    snapshot = batch_snapshots[symbol]
                pe_ttm = snapshot.pe_ttm
                name = snapshot.name
            except (KeyError, OSError, ValueError):
                pe_ttm = None
                name = symbol
                missing.append("quote_source_unavailable")
            event_candidates = [
                candidate
                for event_date in event_dates
                if (candidate := evaluate_first_limit_up(
                    symbol=symbol,
                    name=name,
                    bars=bars,
                    pe_ttm=pe_ttm,
                    as_of=event_date,
                )) is not None
            ]
            if not event_candidates:
                continue
            latest_event = max(event_candidates, key=lambda item: item.limit_up_date)
            if latest_event.limit_up_date == scan_date:
                today.append(latest_event)
            qualified = [
                candidate
                for candidate in event_candidates
                if candidate.selection_status == "qualified"
            ]
            if qualified:
                self.repository.upsert_many([
                    max(qualified, key=lambda item: item.limit_up_date)
                ])
        self._missing_data = tuple(dict.fromkeys(missing))
        displayed_today = today
        self.repository.save_scan(
            scan_date,
            displayed_today,
            universe_count=universe_count,
            history_eligible_count=history_eligible_count,
            scan_coverage_count=scan_coverage_count,
            coverage_complete=coverage_complete,
        )
        board = self.current(scan_date)
        has_scanned_samples = bool(displayed_today)
        return board.model_copy(update={
            "today": tuple(
                sorted(displayed_today, key=lambda item: (-item.score, item.symbol))
            ),
            "scanned_count": len(displayed_today),
            "universe_count": universe_count,
            "history_eligible_count": history_eligible_count,
            "scan_coverage_count": scan_coverage_count,
            "coverage_complete": coverage_complete,
            "qualified_count": sum(
                item.selection_status == "qualified" for item in displayed_today
            ),
            "status": (
                "partial"
                if (
                    not coverage_complete
                    or missing
                    or (has_scanned_samples and board.status == "empty")
                )
                else board.status
            ),
            "missing_data": tuple(dict.fromkeys((*board.missing_data, *missing))),
        })

    def current(self, as_of: date) -> FirstLimitUpBoard:
        stored = self.repository.list_recent(self.pool_limit, as_of=as_of)
        latest_scan = self.repository.latest_scan(as_of=as_of)
        scanned = latest_scan.candidates if latest_scan is not None else ()
        symbols = [item.symbol for item in stored]
        histories = self.bar_repository.latest_many(symbols, 300, as_of) if symbols else {}
        refreshed: list[FirstLimitUpCandidate] = []
        missing = list(self._missing_data)
        for item in stored:
            bars = histories.get(item.symbol, [])
            if not bars:
                missing.append("pool_history_unavailable")
                refreshed.append(item.model_copy(update={
                    "as_of": as_of,
                    "stage": "data_insufficient",
                    "action": "data_insufficient",
                    "risk_flags": tuple(dict.fromkeys((*item.risk_flags, "history_insufficient"))),
                }))
                continue
            refreshed.append(refresh_candidate_state(item, bars, as_of=as_of))
        refreshed.sort(key=lambda item: (-item.score, item.symbol))
        pullback = [item for item in refreshed if item.stage == "pullback_window"]
        priority_symbol = pullback[0].symbol if pullback else None
        universe_count = latest_scan.universe_count if latest_scan else 0
        history_eligible_count = (
            latest_scan.history_eligible_count if latest_scan else 0
        )
        scan_coverage_count = latest_scan.scan_coverage_count if latest_scan else 0
        if latest_scan is None:
            eligible_symbols = tuple(
                self.bar_repository.symbols_with_history(
                    MINIMUM_DAILY_HISTORY,
                    as_of,
                )
            )
            active_symbols = self._active_symbols(eligible_symbols)
            active_set = set(active_symbols)
            eligible_set = set(eligible_symbols)
            universe_count = len(active_symbols)
            history_eligible_count = len(active_set & eligible_set)
            scan_coverage_count = 0
            scanned = ()
            missing.append("full_market_scan_required")
        coverage_complete = (
            latest_scan.coverage_complete
            if latest_scan is not None
            else False
        )
        status = (
            "ready"
            if refreshed and coverage_complete
            else "partial"
            if missing or scanned or latest_scan is not None
            else "empty"
        )
        return FirstLimitUpBoard(
            status=status,
            as_of=as_of,
            universe_count=universe_count,
            history_eligible_count=history_eligible_count,
            scan_coverage_count=scan_coverage_count,
            coverage_complete=coverage_complete,
            scanned_count=len(scanned),
            qualified_count=sum(
                item.selection_status == "qualified" for item in scanned
            ),
            pullback_window_count=len(pullback),
            no_buy_count=sum(item.action == "no_buy" for item in scanned),
            today=tuple(scanned),
            pool=tuple(refreshed),
            priority_symbol=priority_symbol,
            missing_data=tuple(dict.fromkeys(missing)),
            sources=("local-daily-bars", "tencent-quote"),
            rule_version=FIRST_LIMIT_UP_RULE_VERSION,
        )

    def _active_symbols(self, eligible_symbols: tuple[str, ...]) -> tuple[str, ...]:
        if self.universe_provider is None:
            return eligible_symbols
        provider = self.universe_provider
        values = provider() if callable(provider) else provider.active_symbols()
        return tuple(dict.fromkeys(values))


class SynchronousTencentQuoteSource:
    """Thread-safe adapter for the scheduler's synchronous post-close worker."""

    BATCH_SIZE = 80

    def __init__(self, client, compliance) -> None:
        self.client = client
        self.compliance = compliance

    def fetch_snapshot(self, symbol: str):
        snapshots = self.fetch_many((symbol,))
        if symbol not in snapshots:
            raise ValueError("Tencent quote response has no valid payload")
        return snapshots[symbol]

    def fetch_many(self, symbols: Sequence[str]):
        self.compliance.require_feature_sources("realtime_quotes", "a_share")
        unique_symbols = tuple(dict.fromkeys(symbols))
        snapshots = {}
        for offset in range(0, len(unique_symbols), self.BATCH_SIZE):
            batch = unique_symbols[offset:offset + self.BATCH_SIZE]
            instruments = ",".join(f"{market_prefix(symbol)}{symbol}" for symbol in batch)
            try:
                response = self.client.get(f"https://qt.gtimg.cn/q={instruments}")
                response.raise_for_status()
                body = response.content.decode("gbk", errors="strict")
            except (httpx.HTTPError, OSError, UnicodeError, ValueError):
                continue
            for payload in re.findall(r'v_[^=]+="([^"]*)"', body):
                try:
                    snapshot = parse_tencent_snapshot(payload, "tencent")
                except (ArithmeticError, ValueError):
                    continue
                snapshots[snapshot.symbol] = snapshot
        return snapshots
