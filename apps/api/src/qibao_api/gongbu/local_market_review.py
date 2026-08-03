import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from qibao_api.a_shares.market_review import build_market_review
from qibao_api.contracts.market_review import MarketReviewSnapshot
from qibao_api.gongbu.tdx_local_daily import load_tdx_daily_histories


class LocalMarketReviewSource:
    def __init__(
        self,
        *,
        vipdoc_root: Path | None,
        cache_path: Path,
        name_resolver: Callable[[str], str],
        dragon_tiger_source=None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        refresh_seconds: int = 600,
    ) -> None:
        self.vipdoc_root = vipdoc_root
        self.cache_path = cache_path
        self.name_resolver = name_resolver
        self.dragon_tiger_source = dragon_tiger_source
        self.clock = clock
        self.refresh_seconds = refresh_seconds
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._current = self._load_cache()

    def current(self) -> MarketReviewSnapshot | None:
        with self._lock:
            return self._current

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
        if self.vipdoc_root is None:
            snapshot = MarketReviewSnapshot(
                as_of=target_date,
                observed_at=observed_at,
                warnings=("tdx_vipdoc_unavailable",),
            )
        else:
            histories = load_tdx_daily_histories(
                self.vipdoc_root,
                as_of=target_date,
                limit=252,
                stop_requested=self._stop.is_set,
            )
            if self._stop.is_set():
                raise RuntimeError("local market review refresh cancelled")
            snapshot = build_market_review(
                histories,
                as_of=target_date,
                observed_at=observed_at,
                name_resolver=self.name_resolver,
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

    def _refresh_loop(self) -> None:
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
            return MarketReviewSnapshot.model_validate_json(
                self.cache_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None

    def _save_cache(self, snapshot: MarketReviewSnapshot) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        temporary.write_text(snapshot.model_dump_json(), encoding="utf-8")
        temporary.replace(self.cache_path)
