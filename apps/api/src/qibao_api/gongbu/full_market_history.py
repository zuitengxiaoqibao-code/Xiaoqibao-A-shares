from collections.abc import Callable
from datetime import date, datetime
from threading import Event
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
        self._shutdown_requested = Event()

    def create_backfill(self) -> HistorySyncJob:
        return self.jobs.create_job(
            "backfill", self._today(), self.directory.active_symbols()
        )

    def create_incremental(self, target_date: date) -> HistorySyncJob:
        return self.jobs.create_job(
            "incremental", target_date, self.directory.active_symbols()
        )

    def run(self, job_id: str) -> HistorySyncJob:
        job = self.jobs.get(job_id)
        if job.state in ("paused", "completed", "failed"):
            return job
        consecutive_failures = 0
        started_at = self.clock()
        before = self.repair_center(job.target_date, limit=1)
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
            state = self._sync_item(job_id, item.symbol)
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
        coverage = (
            round(aggregate.history_ready_count / aggregate.universe_count * 100, 2)
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
        if not aggregate.universe_count:
            blockers.append("a_share_universe_unavailable")
        if aggregate.dominant_trade_date is None:
            blockers.append("daily_history_unavailable")
        if dominant_coverage is not None and dominant_coverage < 98:
            blockers.append("dominant_date_coverage_below_98_percent")
        if coverage is not None and coverage < 98:
            blockers.append("history_coverage_below_98_percent")
        quality = (
            "ready"
            if aggregate.universe_count and not blockers
            else "partial" if aggregate.universe_count else "unavailable"
        )
        return HistoryCoverageSummary(
            target_date=target_date,
            universe_count=aggregate.universe_count,
            backfill_complete_count=aggregate.backfill_complete_count,
            eligible_count=aggregate.history_ready_count,
            target_date_count=target_date_count,
            target_date_coverage_percent=target_date_coverage,
            dominant_trade_date=aggregate.dominant_trade_date,
            dominant_date_count=aggregate.dominant_date_count,
            dominant_date_coverage_percent=dominant_coverage,
            coverage_percent=coverage,
            fragmented_latest_count=aggregate.fragmented_latest_count,
            missing_history_count=aggregate.missing_history_count,
            quality=quality,
            blockers=tuple(blockers),
        )

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
        gaps: list[HistoryCoverageGap] = []
        for symbol in symbols:
            item = values[symbol]
            if item.bar_count == 0:
                kind = "missing_history"
            elif item.bar_count < self.ELIGIBLE_BARS:
                kind = "insufficient_history"
            elif (
                coverage.dominant_trade_date is not None
                and item.latest_trade_date != coverage.dominant_trade_date
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

    def _sync_item(self, job_id: str, symbol: str) -> str:
        job = self.jobs.get(job_id)
        coverage = self.bar_repository.coverage([symbol], job.target_date)[symbol]
        if (
            job.mode == "backfill"
            and coverage.bar_count >= self.BACKFILL_BARS
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
                written_rows=0,
            )
            return "skipped"

        limit = (
            self.BACKFILL_BARS
            if job.mode == "backfill"
            else self.INCREMENTAL_WINDOW
        )
        try:
            source, bars = self._fetch(symbol, limit)
            verified = self._verify(symbol, bars, job.target_date)
            missing = [
                bar
                for bar in verified
                if coverage.latest_trade_date is None
                or bar.trade_date > coverage.latest_trade_date
            ]
            written_rows = self.bar_repository.append_missing(missing)
            self.jobs.complete_item(
                job_id,
                symbol,
                state="ready",
                source=source,
                written_rows=written_rows,
            )
            return "ready"
        except Exception as error:
            self.jobs.complete_item(
                job_id,
                symbol,
                state="failed",
                source=None,
                written_rows=0,
                error_code=type(error).__name__,
            )
            return "failed"

    def _fetch(self, symbol: str, limit: int) -> tuple[str, list[DailyBar]]:
        try:
            bars = self.tdx_source.fetch_daily(symbol, limit)
            if not bars:
                raise DataSourceUnavailable("mootdx returned no daily bars")
            return "mootdx", bars
        except Exception:
            bars = self.baidu_source.fetch_daily(symbol, limit)
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
