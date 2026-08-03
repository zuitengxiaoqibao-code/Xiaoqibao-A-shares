from collections.abc import Callable
from datetime import date, datetime
from threading import Event
from zoneinfo import ZoneInfo

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.history_sync import (
    HistoryCoverageSummary,
    HistorySyncJob,
)
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
        while True:
            if self._shutdown_requested.is_set():
                return self.jobs.get(job_id)
            item = self.jobs.next_pending(job_id)
            if item is None:
                current = self.jobs.get(job_id)
                if current.state == "paused" or current.pause_requested:
                    return current
                return self.jobs.finish(job_id)
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
        values = self.bar_repository.coverage(symbols, target_date)
        return HistoryCoverageSummary(
            target_date=target_date,
            universe_count=len(symbols),
            backfill_complete_count=sum(
                item.bar_count >= self.BACKFILL_BARS for item in values.values()
            ),
            eligible_count=sum(
                item.bar_count >= self.ELIGIBLE_BARS for item in values.values()
            ),
            target_date_count=sum(
                item.latest_trade_date == target_date for item in values.values()
            ),
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
