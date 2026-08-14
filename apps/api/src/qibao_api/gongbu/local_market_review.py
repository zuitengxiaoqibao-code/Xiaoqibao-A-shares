import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from qibao_api.a_shares.market_review import build_interval_review, build_market_review
from qibao_api.contracts.market_review import (
    MarketIntervalReviewSnapshot,
    MarketReviewSnapshot,
)
from qibao_api.gongbu.tdx_local_daily import load_tdx_daily_histories
from qibao_api.gongbu.tdx_local_daily import TdxLocalDailyBar


class LocalMarketReviewSource:
    def __init__(
        self,
        *,
        vipdoc_root: Path | None,
        cache_path: Path,
        name_resolver: Callable[[str], str],
        dragon_tiger_source=None,
        bar_repository=None,
        symbol_provider: Callable[[], tuple[str, ...] | list[str]] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        refresh_seconds: int = 600,
        scan_workers: int = 2,
        initial_delay_seconds: float = 15,
        defer_cache_validation: bool = False,
    ) -> None:
        if scan_workers < 1:
            raise ValueError("scan_workers must be positive")
        if initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must not be negative")
        self.vipdoc_root = vipdoc_root
        self.cache_path = cache_path
        self.name_resolver = name_resolver
        self.dragon_tiger_source = dragon_tiger_source
        self.bar_repository = bar_repository
        self.symbol_provider = symbol_provider
        self.clock = clock
        self.refresh_seconds = refresh_seconds
        self.scan_workers = scan_workers
        self.initial_delay_seconds = initial_delay_seconds
        self.defer_cache_validation = defer_cache_validation
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._current = None if defer_cache_validation else self._load_cache()

    def current(self) -> MarketReviewSnapshot | None:
        with self._lock:
            return self._current

    def cache_is_stale(self) -> bool:
        """Return whether the persisted review is behind the local bar store."""
        if self.defer_cache_validation:
            with self._lock:
                return self._current is None
        if self.cache_path is None or not self.cache_path.exists():
            return False
        try:
            cached = MarketReviewSnapshot.model_validate_json(
                self.cache_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return False
        latest = self._repository_latest_trade_date()
        return bool(
            latest is not None
            and cached.latest_trade_date is not None
            and cached.latest_trade_date < latest
        )

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._refresh_loop,
                name="local-market-review-refresh",
                daemon=True,
            )
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join()
            self._thread = None
        if self.dragon_tiger_source is not None:
            self.dragon_tiger_source.close()

    def refresh(
        self,
        *,
        as_of: date | None = None,
        include_dragon_tiger: bool = True,
    ) -> MarketReviewSnapshot:
        observed_at = self.clock()
        target_date = as_of or observed_at.astimezone().date()
        if self.vipdoc_root is None and not (
            self.bar_repository is not None and self.symbol_provider is not None
        ):
            snapshot = MarketReviewSnapshot(
                as_of=target_date,
                observed_at=observed_at,
                warnings=("tdx_vipdoc_unavailable",),
            )
        else:
            histories, history_source = self._load_histories(target_date)
            if self._stop.is_set():
                raise RuntimeError("local market review refresh cancelled")
            snapshot = build_market_review(
                histories,
                as_of=target_date,
                observed_at=observed_at,
                name_resolver=self.name_resolver,
                history_source=history_source,
            )
        if self._stop.is_set():
            raise RuntimeError("local market review refresh cancelled")
        if self.dragon_tiger_source is not None and include_dragon_tiger:
            dragon_tiger = self.dragon_tiger_source.fetch(
                as_of=target_date,
                observed_at=observed_at,
            )
            warnings = tuple(snapshot.warnings)
            if not dragon_tiger:
                warnings = tuple(dict.fromkeys((*warnings, "dragon_tiger_unavailable")))
            snapshot = snapshot.model_copy(update={
                "dragon_tiger": dragon_tiger,
                "warnings": warnings,
            })
        with self._lock:
            self._current = snapshot
        self._save_cache(snapshot)
        return snapshot

    def interval(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> MarketIntervalReviewSnapshot:
        observed_at = self.clock()
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        if self.vipdoc_root is None and self.bar_repository is None:
            return MarketIntervalReviewSnapshot(
                requested_start_date=start_date,
                requested_end_date=end_date,
                observed_at=observed_at,
                warnings=("tdx_vipdoc_unavailable",),
            )
        if self.bar_repository is not None and self.symbol_provider is not None:
            histories = self._repository_histories(
                end_date, start_date=start_date, limit=None,
            )
        else:
            histories = load_tdx_daily_histories(
                self.vipdoc_root,
                as_of=end_date,
                start_date=start_date,
                limit=None,
                max_workers=self.scan_workers,
                stop_requested=self._stop.is_set,
            )
        if not histories and self.vipdoc_root is not None:
            histories = load_tdx_daily_histories(
                self.vipdoc_root,
                as_of=end_date,
                start_date=start_date,
                limit=None,
                max_workers=self.scan_workers,
                stop_requested=self._stop.is_set,
            )
        if self._stop.is_set():
            raise RuntimeError("local interval review cancelled")
        return build_interval_review(
            histories,
            start_date=start_date,
            end_date=end_date,
            as_of=end_date,
            observed_at=observed_at,
            name_resolver=self.name_resolver,
        )

    def _load_histories(self, target_date: date) -> tuple[dict[str, tuple[TdxLocalDailyBar, ...]], str]:
        if self.bar_repository is not None and self.symbol_provider is not None:
            histories = self._repository_histories(target_date, limit=252)
            if histories and max(
                (bars[-1].trade_date for bars in histories.values() if bars),
                default=None,
            ) is not None:
                return histories, "market-db"
        if self.vipdoc_root is None:
            return {}, "unavailable"
        return load_tdx_daily_histories(
            self.vipdoc_root,
            as_of=target_date,
            limit=252,
            max_workers=self.scan_workers,
            stop_requested=self._stop.is_set,
        ), "tdx-local-day"

    def _repository_histories(
        self,
        target_date: date,
        *,
        start_date: date | None = None,
        limit: int | None = 252,
    ) -> dict[str, tuple[TdxLocalDailyBar, ...]]:
        if self.bar_repository is None or self.symbol_provider is None:
            return {}
        symbols = list(dict.fromkeys(self.symbol_provider()))
        if not symbols:
            return {}
        if limit is None:
            # Interval queries need the complete requested window. The repository
            # API is intentionally bounded, so use a generous bound and filter
            # below; the bar store still returns only rows at or before target_date.
            limit = 1000
        try:
            rows = self.bar_repository.latest_many(symbols, limit, target_date)
        except (OSError, RuntimeError, ValueError):
            return {}
        histories: dict[str, tuple[TdxLocalDailyBar, ...]] = {}
        for symbol, bars in rows.items():
            converted = tuple(
                TdxLocalDailyBar(
                    symbol=bar.symbol,
                    trade_date=bar.trade_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    amount=bar.amount,
                    source="market-db",
                )
                for bar in bars
                if start_date is None or bar.trade_date >= start_date
            )
            if converted:
                histories[symbol] = converted
        return histories

    def _refresh_loop(self) -> None:
        if self._stop.wait(self.initial_delay_seconds):
            return
        while not self._stop.is_set():
            try:
                self.refresh()
            except (OSError, RuntimeError, ValueError):
                pass
            self._stop.wait(self.refresh_seconds)

    def _load_cache(self) -> MarketReviewSnapshot | None:
        if not self.cache_path.exists():
            return None
        try:
            cached = MarketReviewSnapshot.model_validate_json(
                self.cache_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None
        if self.cache_is_stale():
            return None
        return cached

    def _repository_latest_trade_date(self) -> date | None:
        if self.bar_repository is None or not hasattr(self.bar_repository, "trade_dates"):
            return None
        try:
            values = self.bar_repository.trade_dates(limit=1)
        except (OSError, RuntimeError, ValueError):
            return None
        if not values:
            return None
        value = values[0]
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    def _save_cache(self, snapshot: MarketReviewSnapshot) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        temporary.write_text(snapshot.model_dump_json(), encoding="utf-8")
        temporary.replace(self.cache_path)
