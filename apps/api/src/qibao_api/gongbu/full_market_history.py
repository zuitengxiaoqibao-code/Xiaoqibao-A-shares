from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as monotonic_time
from datetime import date, datetime, time, timedelta
from threading import Event, RLock
from zoneinfo import ZoneInfo

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.history_sync import (
    HistoryCoverageGap,
    HistoryCoverageSummary,
    HistoryRepairCenter,
    HistorySyncJob,
    HistoryRepairAudit,
)
from uuid import uuid4
from qibao_api.contracts.history_quality import HistoryQualityReport
from qibao_api.a_shares.history_quality import inspect_history_quality
from qibao_api.gongbu.history_sync_repository import HistorySyncRepository
from qibao_api.gongbu.tdx_history import DataSourceUnavailable


class FullMarketHistoryService:
    BACKFILL_BARS = 300
    ELIGIBLE_BARS = 250
    INCREMENTAL_WINDOW = 30

    def __init__(
        self,
        *,
        directory,
        bar_repository,
        tdx_source,
        baidu_source,
        job_repository: HistorySyncRepository,
        clock: Callable[[], datetime],
        failure_pause_threshold: int = 20,
        trading_calendar=None,
        fallback_sources=(),
        max_workers: int = 1,
        listing_date_source=None,
        close_source=None,
    ) -> None:
        if failure_pause_threshold < 1:
            raise ValueError("failure_pause_threshold must be positive")
        self.directory = directory
        self.bar_repository = bar_repository
        self.tdx_source = tdx_source
        self.baidu_source = baidu_source
        self.jobs = job_repository
        self.clock = clock
        self.failure_pause_threshold = failure_pause_threshold
        self.trading_calendar = trading_calendar
        self.fallback_sources = tuple(fallback_sources)
        self.max_workers = max(1, min(8, max_workers))
        self._source_lock = RLock()
        self._source_failures = {}
        self.listing_date_source = listing_date_source
        self.close_source = close_source
        self._repair_sessions = None
        self._shutdown_requested = Event()

    def create_backfill(self) -> HistorySyncJob:
        return self.jobs.create_job(
            "backfill", self.default_target_date(), self.directory.active_symbols()
        )

    def create_incremental(self, target_date: date) -> HistorySyncJob:
        return self.jobs.create_job(
            "incremental", target_date, self.directory.active_symbols()
        )

    def run(
        self,
        job_id: str,
        progress: Callable[[HistorySyncJob], None] | None = None,
        comprehensive: bool = False,
    ) -> HistorySyncJob:
        job = self.jobs.get(job_id)
        if job.state in ("paused", "completed", "failed"):
            return job
        self._repair_sessions = None
        with self._source_lock:
            self._source_failures.clear()
        consecutive_failures = 0
        started_at = self.clock()
        before = self.repair_center(job.target_date, limit=1)
        # Only the coordinator updates progress. Network workers use independent
        # clients; repository writes remain protected by their existing locks.
        if comprehensive:
            committed = {item.symbol: item.written_rows for item in self.jobs.items(job_id) if item.state == "pending"}
            with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="repair-fetch") as executor:
                pending = [item for item in self.jobs.items(job_id) if item.state == "pending"]
                if self.close_source is not None:
                    try:
                        self.close_source.prefetch(tuple(item.symbol for item in pending), job.target_date)
                        coverage = self.bar_repository.coverage([item.symbol for item in pending], job.target_date)
                        closing = [bar for bar in self.close_source.bars()
                                   if coverage[bar.symbol].bar_count > 0
                                   and coverage[bar.symbol].latest_trade_date is not None
                                   and coverage[bar.symbol].latest_trade_date < job.target_date]
                        for offset in range(0, len(closing), 256):
                            if self._shutdown_requested.is_set() or self.jobs.is_pause_requested(job_id):
                                return self.jobs.get(job_id)
                            batch = closing[offset:offset + 256]
                            inserted = self.bar_repository.append_missing_batch(batch)
                            # Only record a one-row write when the complete batch
                            # was committed. A concurrent writer falls back to
                            # the normal per-symbol verification below.
                            if inserted == len(batch):
                                for bar in batch:
                                    committed[bar.symbol] = committed.get(bar.symbol, 0) + 1
                                ready = tuple(bar.symbol for bar in batch if coverage[bar.symbol].bar_count >= self.ELIGIBLE_BARS)
                                self.jobs.complete_closing_batch(job_id, ready)
                                if progress is not None:
                                    progress(self.jobs.get(job_id))
                        pending = [item for item in self.jobs.items(job_id) if item.state == "pending"]
                    except Exception:
                        pass  # Independent historical sources remain available.
                symbols = [item.symbol for item in pending]
                coverage_values = self.bar_repository.coverage(symbols, job.target_date)
                short = [symbol for symbol in symbols if coverage_values[symbol].bar_count < self.ELIGIBLE_BARS
                         or (self.close_source is not None and self.close_source.unavailable_reason(symbol, job.target_date))]
                stored_values = self.bar_repository.latest_many(short, self.BACKFILL_BARS, job.target_date) if short and hasattr(self.bar_repository, "latest_many") else {}
                self._repair_sessions = tuple(self.bar_repository.trade_dates(limit=400)) if hasattr(self.bar_repository, "trade_dates") else None
                for offset in range(0, len(pending), self.max_workers):
                    if self._shutdown_requested.is_set() or self.jobs.is_pause_requested(job_id):
                        return self.jobs.get(job_id)
                    batch = pending[offset:offset + self.max_workers]
                    futures = []
                    for item in batch:
                        self.jobs.mark_running(job_id, item.symbol)
                        futures.append(executor.submit(self._sync_item, job_id, item.symbol,
                            coverage_values.get(item.symbol), stored_values.get(item.symbol), committed.get(item.symbol, 0)))
                    for future in as_completed(futures):
                        future.result()
                        if progress is not None:
                            progress(self.jobs.get(job_id))
            # Reuse the normal completion/audit path, not the outage pause rule.
        while True:
            if self._shutdown_requested.is_set():
                return self.jobs.get(job_id)
            item = self.jobs.next_pending(job_id)
            if item is None:
                current = self.jobs.get(job_id)
                if current.state == "paused" or current.pause_requested:
                    return current
                completed = self.jobs.finish(job_id)
                after = self.coverage(job.target_date)
                sources = {item.source for item in self.jobs.items(job_id) if item.source}
                failures = tuple(dict.fromkeys(item.error_code for item in self.jobs.items(job_id) if item.error_code))
                self.jobs.append_repair_audit(HistoryRepairAudit(
                    audit_id=f"repair-audit-{uuid4().hex}", job_id=job_id, mode=job.mode,
                    target_date=job.target_date, started_at=started_at, completed_at=self.clock(),
                    source="+".join(sorted(sources)) if sources else "unavailable",
                    gap_count_before=before.total_gap_count,
                    coverage_before_percent=before.coverage.coverage_percent,
                    written_rows=sum(item.written_rows for item in self.jobs.items(job_id)),
                    ready_count=completed.ready_count, failed_count=completed.failed_count,
                    skipped_count=completed.skipped_count,
                    coverage_after_percent=after.coverage_percent,
                    final_state=completed.state, failure_reasons=failures,
                ))
                return completed
            if self.jobs.is_pause_requested(job_id):
                return self.jobs.mark_paused(job_id)
            self.jobs.mark_running(job_id, item.symbol)
            state = self._sync_item(job_id, item.symbol, precommitted=item.written_rows)
            if progress is not None:
                progress(self.jobs.get(job_id))
            if state == "failed":
                consecutive_failures += 1
                if consecutive_failures >= self.failure_pause_threshold:
                    return self.jobs.request_pause(job_id)
            else:
                consecutive_failures = 0

    def request_shutdown(self) -> None:
        self._shutdown_requested.set()

    def pause(self, job_id: str) -> HistorySyncJob:
        return self.jobs.request_pause(job_id)

    def resume(self, job_id: str) -> HistorySyncJob:
        return self.jobs.resume(job_id)

    def retry_failed(self, job_id: str) -> HistorySyncJob:
        return self.jobs.retry_failed(job_id)

    def restart_current(self, target_date: date) -> HistorySyncJob:
        current = self.current_job()
        if current is not None and current.state in ("pending", "running"):
            raise ValueError("history sync job is still active")
        if current is not None and current.state == "paused":
            if current.target_date == target_date:
                return self.jobs.retry_failed(current.job_id)
            self.jobs.mark_failed(current.job_id)
        job = self.create_incremental(target_date)
        if job.state in ("completed", "failed") and job.failed_count:
            return self.jobs.retry_failed(job.job_id)
        return job

    def job(self, job_id: str) -> HistorySyncJob:
        return self.jobs.get(job_id)

    def current_job(self) -> HistorySyncJob | None:
        return self.jobs.current()

    def recover_interrupted(self) -> None:
        self.jobs.recover_interrupted()

    def coverage(self, target_date: date) -> HistoryCoverageSummary:
        symbols = self.directory.active_symbols()
        aggregate = self.bar_repository.coverage_aggregate(
            symbols,
            target_date,
            minimum_bars=self.ELIGIBLE_BARS,
            backfill_bars=self.BACKFILL_BARS,
        )
        evidence = self.jobs.listing_history_evidence(target_date)
        recent = self.bar_repository.coverage(tuple(set(evidence) & set(symbols)), target_date) if evidence else {}
        suspended = self.jobs.suspension_evidence(target_date)
        suspended_values = self.bar_repository.coverage(tuple(set(suspended) & set(symbols)), target_date) if suspended else {}
        confirmed_suspended = sum((item.bar_count, item.latest_trade_date) == suspended[symbol]
                                  for symbol, item in suspended_values.items())
        new_complete = sum(item.bar_count < self.ELIGIBLE_BARS
                           and item.bar_count >= evidence[symbol] and item.latest_trade_date == target_date
                           for symbol, item in recent.items())
        coverage = (
            round((aggregate.history_ready_count + new_complete) / aggregate.universe_count * 100, 2)
            if aggregate.universe_count else None
        )
        dominant_coverage = (
            round(aggregate.dominant_date_count / aggregate.universe_count * 100, 2)
            if aggregate.universe_count else None
        )
        target_date_count = (
            aggregate.latest_available_trade_date_count
            if aggregate.latest_available_trade_date == target_date else 0
        )
        target_date_coverage = (
            round(target_date_count / aggregate.universe_count * 100, 2)
            if aggregate.universe_count else None
        )
        blockers: list[str] = []
        lag_trading_days = self._trading_day_lag(
            aggregate.dominant_trade_date, target_date,
        )
        if not aggregate.universe_count:
            blockers.append("a_share_universe_unavailable")
        if aggregate.dominant_trade_date is None:
            blockers.append("daily_history_unavailable")
        if dominant_coverage is not None and dominant_coverage < 98:
            blockers.append("dominant_date_coverage_below_98_percent")
        if coverage is not None and coverage < 98:
            blockers.append("history_coverage_below_98_percent")
        if lag_trading_days:
            blockers.append("dominant_trade_date_behind_target")
        quality = (
            "ready"
            if aggregate.universe_count and not blockers
            else "stale" if aggregate.universe_count and lag_trading_days
            else "partial" if aggregate.universe_count else "unavailable"
        )
        return HistoryCoverageSummary(
            target_date=target_date,
            universe_count=aggregate.universe_count,
            backfill_complete_count=aggregate.backfill_complete_count,
            eligible_count=aggregate.history_ready_count,
            new_listing_complete_count=new_complete,
            confirmed_suspended_count=confirmed_suspended,
            target_date_count=target_date_count,
            target_date_coverage_percent=target_date_coverage,
            dominant_trade_date=aggregate.dominant_trade_date,
            dominant_date_count=aggregate.dominant_date_count,
            dominant_date_coverage_percent=dominant_coverage,
            coverage_percent=coverage,
            fragmented_latest_count=aggregate.fragmented_latest_count,
            missing_history_count=max(0, aggregate.missing_history_count - new_complete),
            quality=quality,
            blockers=tuple(blockers),
            lag_trading_days=lag_trading_days,
            is_fresh=bool(
                aggregate.universe_count
                and aggregate.dominant_trade_date == target_date
            ),
        )

    def create_target_repair(self, target_date: date) -> HistorySyncJob | None:
        """Create an online multi-source job only for symbols with a real gap."""
        symbols = self.directory.active_symbols()
        values = self.bar_repository.coverage(symbols, target_date)
        evidence = self.jobs.listing_history_evidence(target_date)
        suspended = self.jobs.suspension_evidence(target_date)
        gaps = tuple(
            symbol for symbol in symbols
            if ((values[symbol].bar_count < self.ELIGIBLE_BARS
                and values[symbol].bar_count < evidence.get(symbol, self.ELIGIBLE_BARS))
            or values[symbol].latest_trade_date is None
            or values[symbol].latest_trade_date < target_date)
            and (values[symbol].bar_count, values[symbol].latest_trade_date) != suspended.get(symbol)
        )
        if not gaps:
            return None
        job = self.jobs.create_job("backfill", target_date, gaps)
        if job.state in {"paused", "completed", "failed"}:
            job = self.jobs.requeue_gaps(job.job_id, gaps)
        return self.jobs.restrict_to_gaps(job.job_id, gaps)

    def repair_center(
        self,
        target_date: date,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> HistoryRepairCenter:
        if offset < 0:
            raise ValueError("offset must not be negative")
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        symbols = self.directory.active_symbols()
        coverage = self.coverage(target_date)
        values = self.bar_repository.coverage(symbols, target_date)
        evidence = self.jobs.listing_history_evidence(target_date)
        suspended = self.jobs.suspension_evidence(target_date)
        gaps: list[HistoryCoverageGap] = []
        for symbol in symbols:
            item = values[symbol]
            if (item.bar_count, item.latest_trade_date) == suspended.get(symbol):
                continue
            if item.bar_count == 0:
                kind = "missing_history"
            elif item.bar_count < self.ELIGIBLE_BARS and item.bar_count < evidence.get(symbol, self.ELIGIBLE_BARS):
                kind = "insufficient_history"
            elif (
                item.latest_trade_date is not None
                and item.latest_trade_date < target_date
            ):
                kind = "behind_dominant_date"
            else:
                continue
            gaps.append(HistoryCoverageGap(
                symbol=symbol,
                bar_count=item.bar_count,
                latest_trade_date=item.latest_trade_date,
                gap_kind=kind,
            ))
        priority = {
            "missing_history": 0,
            "insufficient_history": 1,
            "behind_dominant_date": 2,
        }
        gaps.sort(key=lambda item: (priority[item.gap_kind], item.symbol))
        return HistoryRepairCenter(
            coverage=coverage,
            current_job=self.current_job(),
            gaps=tuple(gaps[offset:offset + limit]),
            total_gap_count=len(gaps),
            offset=offset,
            limit=limit,
        )

    def quality_report(self, *, limit: int = 1000) -> HistoryQualityReport:
        """Inspect the locally stored date grid without creating or repairing bars."""
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        symbols = tuple(self.directory.active_symbols())
        sessions = tuple(reversed(self.bar_repository.trade_dates(limit=limit)))
        if not symbols or not sessions:
            return inspect_history_quality(sessions, symbols, {}, observed_at=self.clock())
        histories = self.bar_repository.latest_many(
            list(symbols), min(limit, self.BACKFILL_BARS), sessions[-1]
        )
        by_symbol = {
            symbol: tuple(item.trade_date for item in bars)
            for symbol, bars in histories.items()
        }
        return inspect_history_quality(
            sessions,
            symbols,
            by_symbol,
            observed_at=self.clock(),
            source="market.duckdb/daily_bars",
        )

    def _sync_item(self, job_id: str, symbol: str, coverage_override=None, stored_override=None, precommitted=0) -> str:
        job = self.jobs.get(job_id)
        coverage = coverage_override or self.bar_repository.coverage([symbol], job.target_date)[symbol]
        if (self.close_source is not None and self.listing_date_source is not None
                and coverage.bar_count >= self.ELIGIBLE_BARS
                and self.close_source.unavailable_reason(symbol, job.target_date)):
            try:
                stored = stored_override if stored_override is not None else self.bar_repository.latest_many([symbol], self.BACKFILL_BARS, job.target_date)[symbol]
                if self.listing_date_source.verify_history(symbol, stored, job.target_date):
                    self.jobs.confirm_suspension(symbol, job.target_date, coverage.bar_count, coverage.latest_trade_date)
                    self.jobs.complete_item(job_id, symbol, state="skipped", source=None, written_rows=precommitted)
                    return "skipped"
            except Exception:
                pass
        if (self.close_source is not None and coverage.bar_count > 0
                and coverage.latest_trade_date is not None and coverage.latest_trade_date < job.target_date):
            try:
                bar = self.close_source.bar(symbol, job.target_date)
                if bar is not None:
                    written = self.bar_repository.append_missing([bar])
                    precommitted += written
                    stored = self.bar_repository.latest_many([symbol], self.BACKFILL_BARS, job.target_date)[symbol]
                    if len(stored) >= self.ELIGIBLE_BARS or self._confirm_new_listing(symbol, stored, job.target_date):
                        self.jobs.complete_item(job_id, symbol, state="ready", source="tencent", written_rows=precommitted)
                        return "ready"
            except Exception:
                pass
        if (self.listing_date_source is not None and coverage.bar_count < self.ELIGIBLE_BARS
                and coverage.latest_trade_date == job.target_date):
            stored = stored_override if stored_override is not None else self.bar_repository.latest_many([symbol], self.BACKFILL_BARS, job.target_date)[symbol]
            if self._confirm_new_listing(symbol, stored, job.target_date):
                state = "ready" if precommitted else "skipped"
                self.jobs.complete_item(job_id, symbol, state=state, source="tencent" if precommitted else None, written_rows=precommitted)
                return state
        if (
            job.mode == "backfill"
            and coverage.bar_count >= self.BACKFILL_BARS
            and coverage.latest_trade_date is not None
            and coverage.latest_trade_date >= job.target_date
        ) or (
            job.mode == "incremental"
            and coverage.latest_trade_date is not None
            and coverage.latest_trade_date >= job.target_date
        ):
            self.jobs.complete_item(
                job_id,
                symbol,
                state="skipped",
                source=None,
                written_rows=precommitted,
            )
            return "skipped"

        limit = (
            self.BACKFILL_BARS
            if job.mode == "backfill"
            else self.INCREMENTAL_WINDOW
        )
        try:
            source, bars = self._fetch(symbol, limit, target_date=job.target_date)
            verified = self._verify(symbol, bars, job.target_date)
            missing = [
                bar
                for bar in verified
                if job.mode == "backfill"
                or coverage.latest_trade_date is None
                or bar.trade_date > coverage.latest_trade_date
            ]
            written_rows = self.bar_repository.append_missing(missing)
            if self.fallback_sources and len(verified) < self.ELIGIBLE_BARS:
                combined = self.bar_repository.latest_many([symbol], self.BACKFILL_BARS, job.target_date)[symbol] if hasattr(self.bar_repository, "latest_many") else verified
                self._confirm_new_listing(symbol, combined, job.target_date)
            self.jobs.complete_item(
                job_id,
                symbol,
                state="ready",
                source=source,
                written_rows=written_rows + precommitted,
            )
            return "ready"
        except Exception as error:
            try:
                reason = getattr(self.close_source, "unavailable_reason", lambda *_: None)(symbol, job.target_date)
            except Exception:
                reason = None
            self.jobs.complete_item(
                job_id,
                symbol,
                state="failed",
                source=None,
                written_rows=precommitted,
                error_code=type(error).__name__,
                error_detail=((reason + "；" if reason else "") + str(error))[:1200],
            )
            return "failed"

    def _confirm_new_listing(self, symbol: str, bars: list[DailyBar], target_date: date) -> bool:
        """A short history is complete only with independent listing evidence
        and every exchange session since listing, not just a short response."""
        if not bars or bars[-1].trade_date != target_date or not hasattr(self.bar_repository, "trade_dates"):
            return False
        listing_sources = ((("sina", self.listing_date_source),) if self.listing_date_source is not None else ()) + self.fallback_sources
        for name, source in listing_sources:
            listing = getattr(source, "listing_date", None)
            if listing is None:
                continue
            try:
                listed = listing(symbol)
                sessions = {day for day in (self._repair_sessions if self._repair_sessions is not None else self.bar_repository.trade_dates(limit=400))
                            if listed <= day <= target_date}
                available = {bar.trade_date for bar in bars}
                complete = sessions == available
                if not complete and available <= sessions:
                    verify = getattr(source, "verify_history", None)
                    complete = verify is not None and verify(symbol, bars, target_date, listed)
                if listed in sessions and target_date in sessions and complete:
                    self.jobs.confirm_listing_history(symbol, target_date, listed, len(available), name)
                    return True
            except Exception:
                # Missing listing evidence cannot weaken the 250-bar rule.
                continue
        return False

    def _fetch(self, symbol: str, limit: int, *, target_date: date) -> tuple[str, list[DailyBar]]:
        if self.fallback_sources:
            errors = []
            # HTTP OHLCV+actual amount first: fast, bounded requests. Original
            # TDX and Baidu paths remain independent fallbacks.
            sources = (*self.fallback_sources, ("mootdx", self.tdx_source), ("baidu", self.baidu_source))
            for name, source in sources:
                with self._source_lock:
                    failures, retry_after = self._source_failures.get(name, (0, 0))
                if monotonic_time.monotonic() < retry_after:
                    errors.append(f"{name}: 来源连续失败，冷却后自动重试")
                    continue
                for attempt in range(2):
                    try:
                        bars = self._verify(symbol, source.fetch_daily(symbol, limit), target_date)
                        if not bars:
                            raise DataSourceUnavailable("未返回目标日期范围日线")
                        if bars[-1].trade_date != target_date:
                            raise DataSourceUnavailable(f"最新日线 {bars[-1].trade_date} 未覆盖目标日 {target_date}")
                        if len(bars) < self.ELIGIBLE_BARS:
                            local = self.bar_repository.coverage([symbol], target_date)[symbol]
                            if local.bar_count < self.ELIGIBLE_BARS:
                                stored = self.bar_repository.latest_many([symbol], self.BACKFILL_BARS, target_date)[symbol] if hasattr(self.bar_repository, "latest_many") else []
                                combined = {bar.trade_date: bar for bar in stored}
                                combined.update({bar.trade_date: bar for bar in bars})
                                merged = sorted(combined.values(), key=lambda bar: bar.trade_date)
                                if len(merged) < self.ELIGIBLE_BARS and not self._confirm_new_listing(symbol, merged, target_date):
                                    raise DataSourceUnavailable("历史不足 250 条，且尚未核实上市以来的全部日线，继续尝试下一来源")
                        with self._source_lock:
                            self._source_failures[name] = (0, 0)
                        return name, bars
                    except Exception as error:
                        import httpx
                        status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
                        errors.append(f"{name}: HTTP {status}" if status else f"{name}: {type(error).__name__}: {str(error)[:160]}")
                        transient = isinstance(error, (httpx.TransportError, OSError)) or status in {429, 500, 502, 503, 504} or (name == "mootdx" and type(error).__name__ == "TdxOperationError")
                        if not attempt and transient and name != "mootdx":
                            monotonic_time.sleep(0.2)
                            continue
                        with self._source_lock:
                            failures = self._source_failures.get(name, (0, 0))[0] + 1
                            self._source_failures[name] = (failures, monotonic_time.monotonic() + 30 if failures >= 3 and transient else 0)
                        break
            raise DataSourceUnavailable("；".join(errors))
        try:
            bars = self.tdx_source.fetch_daily(symbol, limit)
            bars = self._verify(symbol, bars, target_date)
            if not bars:
                raise DataSourceUnavailable("mootdx returned no daily bars")
            return "mootdx", bars
        except Exception:
            bars = self.baidu_source.fetch_daily(symbol, limit)
            bars = self._verify(symbol, bars, target_date)
            if not bars:
                raise DataSourceUnavailable("Baidu returned no daily bars")
            return "baidu", bars

    @staticmethod
    def _verify(
        symbol: str, bars: list[DailyBar], target_date: date
    ) -> list[DailyBar]:
        if not bars:
            raise DataSourceUnavailable("daily history response is empty")
        ordered = sorted(bars, key=lambda item: item.trade_date)
        if any(item.symbol != symbol for item in ordered):
            raise DataSourceUnavailable("daily history response has mixed symbols")
        dates = [item.trade_date for item in ordered]
        if len(dates) != len(set(dates)):
            raise DataSourceUnavailable("daily history response has duplicate dates")
        return [item for item in ordered if item.trade_date <= target_date]

    def _today(self) -> date:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("history sync clock must return an aware datetime")
        return value.astimezone(ZoneInfo("Asia/Shanghai")).date()

    def default_target_date(self) -> date:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("history sync clock must return an aware datetime")
        local = value.astimezone(ZoneInfo("Asia/Shanghai"))
        candidate = local.date()
        if local.time() < time(15, 5):
            candidate -= timedelta(days=1)
        if self.trading_calendar is None:
            while candidate.weekday() >= 5:
                candidate -= timedelta(days=1)
            return candidate
        for _ in range(15):
            if self.trading_calendar.is_trading_day(candidate):
                return candidate
            candidate -= timedelta(days=1)
        raise ValueError("最近已完成交易日无法确认")

    def _trading_day_lag(self, dominant_date: date | None, target_date: date) -> int:
        if dominant_date is None or dominant_date >= target_date:
            return 0
        count = 0
        candidate = dominant_date + timedelta(days=1)
        while candidate <= target_date:
            is_session = (
                self.trading_calendar.is_trading_day(candidate)
                if self.trading_calendar is not None
                else candidate.weekday() < 5
            )
            if is_session:
                count += 1
            candidate += timedelta(days=1)
        return count
