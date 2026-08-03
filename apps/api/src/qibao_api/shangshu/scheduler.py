import asyncio
import inspect
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone


CHINA_TZ = timezone(timedelta(hours=8))
SCHEDULE = (
    ("premarket", "0920", time(9, 20)),
    ("intraday", "1030", time(10, 30)),
    ("intraday", "1330", time(13, 30)),
    ("intraday", "1430", time(14, 30)),
    ("postclose", "1530", time(15, 30)),
)
MIN_ANALYSIS_COVERAGE_RATIO = 0.95


@dataclass(frozen=True)
class ManualRunResult:
    report_id: str | None
    status: str = "completed"


class DailyBriefingScheduler:
    def __init__(
        self, workflow, calendar, repository, *,
        max_attempts: int = 3, catchup_days: int = 7, decision_workflow=None,
        intraday_monitor=None, hotspot_service=None,
        market_sentiment_service=None,
        first_limit_up_service=None,
        full_market_history_service=None,
        history_sync_submitter=None,
    ) -> None:
        self.workflow = workflow
        self.calendar = calendar
        self.repository = repository
        self.max_attempts = max_attempts
        self.catchup_days = catchup_days
        self.decision_workflow = decision_workflow
        self.intraday_monitor = intraday_monitor
        self.hotspot_service = hotspot_service
        self.market_sentiment_service = market_sentiment_service
        self.first_limit_up_service = first_limit_up_service
        self.full_market_history_service = full_market_history_service
        self.history_sync_submitter = history_sync_submitter
        self._submitted_history_jobs: set[str] = set()
        self._run_lock = threading.RLock()

    def tick(self, now: datetime) -> None:
        with self._run_lock:
            local_now = now.astimezone(CHINA_TZ)
            if self.repository.paused():
                return
            latest_history_date = self._latest_due_postclose_date(local_now)
            for days_ago in range(self.catchup_days, -1, -1):
                trading_date = local_now.date() - timedelta(days=days_ago)
                if not self.calendar.is_trading_day(trading_date):
                    continue
                for phase, slot, scheduled_time in SCHEDULE:
                    scheduled_at = datetime.combine(trading_date, scheduled_time, CHINA_TZ)
                    if local_now >= scheduled_at:
                        if phase == "intraday" and self.hotspot_service is not None:
                            self._run_hotspots(
                                trading_date,
                                slot,
                                occurred_at=now,
                                trigger="scheduled",
                            )
                        self._run_market_sentiment(
                            phase,
                            trading_date,
                            slot,
                            occurred_at=now,
                            trigger="scheduled",
                        )
                        history_ready = True
                        if phase == "postclose":
                            history_ready = (
                                self.full_market_history_service is None
                                or (
                                    trading_date == latest_history_date
                                    and self._postclose_history_ready(trading_date)
                                )
                            )
                        if (
                            phase == "postclose"
                            and history_ready
                            and self.first_limit_up_service is not None
                        ):
                            self._run_first_limit_up(
                                trading_date, slot, occurred_at=now, trigger="scheduled"
                            )
                        self._run(
                            phase, trading_date, slot,
                            workflow_now=scheduled_at,
                            occurred_at=now,
                            trigger="scheduled",
                        )
                        if (phase == "intraday" and self.intraday_monitor is not None
                                and trading_date == local_now.date()):
                            self._run_monitor(
                                trading_date, slot, scheduled_at, now, "scheduled"
                            )

    def tick_intraday(self, now: datetime):
        if self.intraday_monitor is None or self.repository.paused():
            return None
        local_now = now.astimezone(CHINA_TZ)
        if (
            not self.calendar.is_trading_day(local_now.date())
            or not time(9, 25) <= local_now.time() <= time(15, 0)
        ):
            return None
        due = getattr(self.intraday_monitor, "due", None)
        if callable(due) and not due(now):
            return None
        slot = local_now.strftime("%H%M%S")
        with self._run_lock:
            return self._run_monitor(local_now.date(), slot, now, now, "background")

    def run_manual(
        self, phase: str, trading_date: date, now: datetime
    ):
        slot = f"manual-{now.astimezone(CHINA_TZ).strftime('%H%M%S')}"
        with self._run_lock:
            if phase == "intraday" and self.hotspot_service is not None:
                self._run_hotspots(
                    trading_date,
                    slot,
                    occurred_at=now,
                    trigger="manual",
                )
            self._run_market_sentiment(
                phase,
                trading_date,
                slot,
                occurred_at=now,
                trigger="manual",
            )
            history_ready = (
                self._postclose_history_ready(trading_date)
                if phase == "postclose"
                else True
            )
            if (
                phase == "postclose"
                and history_ready
                and self.first_limit_up_service is not None
            ):
                self._run_first_limit_up(
                    trading_date, slot, occurred_at=now, trigger="manual"
                )
            return self._run(
                phase, trading_date, slot,
                workflow_now=now,
                occurred_at=now,
                trigger="manual",
                force=True,
            )

    def set_paused(self, paused: bool, now: datetime) -> None:
        self.repository.set_paused(paused, now)

    def status(self) -> dict:
        return {"paused": self.repository.paused(), "jobs": self.repository.jobs()}

    def _run(
        self, phase: str, trading_date: date, slot: str, *,
        workflow_now: datetime, occurred_at: datetime, trigger: str,
        force: bool = False,
    ):
        job_key = f"{trading_date.isoformat()}:{phase}:{slot}"
        events = self.repository.attempts_for(job_key)
        attempt_count = max((item["attempt"] for item in events), default=0)
        if events and events[-1]["status"] == "started":
            report = self._persisted_report(phase, trading_date, workflow_now)
            if report is not None:
                self.repository.append_attempt(
                    job_key=job_key, phase=phase, trading_date=trading_date,
                    slot=slot, trigger=trigger, attempt=attempt_count,
                    status="completed", occurred_at=occurred_at,
                    report_id=report.report_id,
                )
                decision_result = self._run_decision(
                    phase, trading_date, slot, workflow_now=workflow_now,
                    occurred_at=occurred_at, trigger=trigger,
                    briefing_report_id=report.report_id,
                )
                if trigger == "manual" and self.decision_workflow is not None:
                    return decision_result
                return report
        completed = next(
            (item for item in reversed(events) if item["status"] == "completed"), None
        )
        if not force and completed is not None:
            decision_result = self._run_decision(
                phase, trading_date, slot, workflow_now=workflow_now,
                occurred_at=occurred_at, trigger=trigger,
                briefing_report_id=completed.get("report_id"),
            )
            if trigger == "manual" and self.decision_workflow is not None:
                return decision_result
            return None
        if not force and attempt_count >= self.max_attempts:
            return None
        attempt = attempt_count + 1
        self.repository.append_attempt(
            job_key=job_key, phase=phase, trading_date=trading_date,
            slot=slot, trigger=trigger, attempt=attempt, status="started",
            occurred_at=occurred_at,
        )
        try:
            report = self.workflow.run(phase, trading_date, now=workflow_now)
        except Exception as error:
            self.repository.append_attempt(
                job_key=job_key, phase=phase, trading_date=trading_date,
                slot=slot, trigger=trigger, attempt=attempt, status="failed",
                occurred_at=occurred_at, error_code=_error_code(error),
            )
            return None
        self.repository.append_attempt(
            job_key=job_key, phase=phase, trading_date=trading_date,
            slot=slot, trigger=trigger, attempt=attempt, status="completed",
            occurred_at=occurred_at, report_id=report.report_id,
        )
        decision_result = self._run_decision(
            phase, trading_date, slot, workflow_now=workflow_now,
            occurred_at=occurred_at, trigger=trigger,
            briefing_report_id=report.report_id,
        )
        if trigger == "manual" and self.decision_workflow is not None:
            return decision_result
        return report

    def _run_decision(
        self, phase: str, trading_date: date, slot: str, *,
        workflow_now: datetime, occurred_at: datetime, trigger: str,
        briefing_report_id: str | None,
    ) -> ManualRunResult | None:
        if self.decision_workflow is None:
            return None
        decision_job_key = f"{trading_date.isoformat()}:{phase}:{slot}:decision"
        events = self.repository.attempts_for(decision_job_key)
        attempt_count = max((item["attempt"] for item in events), default=0)
        if (
            any(item["status"] == "completed" for item in events)
            or attempt_count >= self.max_attempts
        ):
            return None
        attempt = attempt_count + 1
        values = dict(
            job_key=decision_job_key, phase=phase, trading_date=trading_date,
            slot=f"{slot}:decision", trigger=trigger, attempt=attempt,
            occurred_at=occurred_at,
        )
        self.repository.append_attempt(**values, status="started")
        try:
            decision = self.decision_workflow.run(
                phase, trading_date, now=workflow_now
            )
        except Exception as error:
            self.repository.append_attempt(
                **values, status="failed", error_code=_error_code(error)
            )
            return None
        snapshot = getattr(decision, "snapshot", decision)
        snapshot_id = getattr(snapshot, "snapshot_id", None)
        self.repository.append_attempt(
            **values, status="completed", report_id=snapshot_id,
        )
        return ManualRunResult(report_id=snapshot_id or briefing_report_id)

    def _persisted_report(
        self, phase: str, trading_date: date, generated_at: datetime
    ):
        repository = getattr(self.workflow, "briefing_repository", None)
        if repository is None:
            return None
        return next((
            report for report in repository.reports(
                phase=phase, trading_date=trading_date
            )
            if report.generated_at == generated_at
        ), None)

    def _run_monitor(self, trading_date, slot, workflow_now, occurred_at, trigger):
        job_key = f"{trading_date.isoformat()}:monitor:{slot}"
        if trigger == "scheduled":
            job_key = f"{trading_date.isoformat()}:intraday:{slot}:monitor"
        events = self.repository.attempts_for(job_key)
        if any(item["status"] == "completed" for item in events):
            return None
        attempt = max((item["attempt"] for item in events), default=0) + 1
        values = dict(
            job_key=job_key, phase="intraday_monitor", trading_date=trading_date,
            slot=f"{slot}:monitor", trigger=trigger, attempt=attempt,
            occurred_at=occurred_at,
        )
        self.repository.append_attempt(**values, status="started")
        try:
            result = self.intraday_monitor.check(workflow_now)
        except Exception as error:
            self.repository.append_attempt(
                **values, status="failed", error_code=_error_code(error)
            )
            return None
        self.repository.append_attempt(
            **values, status="completed", report_id=getattr(result, "result_id", None)
        )
        return result

    def _run_hotspots(
        self,
        trading_date: date,
        slot: str,
        *,
        occurred_at: datetime,
        trigger: str,
    ) -> None:
        job_key = f"{trading_date.isoformat()}:intraday:{slot}:hotspots"
        events = self.repository.attempts_for(job_key)
        attempt_count = max((item["attempt"] for item in events), default=0)
        if (
            any(item["status"] == "completed" for item in events)
            or attempt_count >= self.max_attempts
        ):
            return
        attempt = attempt_count + 1
        values = dict(
            job_key=job_key,
            phase="intraday_hotspots",
            trading_date=trading_date,
            slot=f"{slot}:hotspots",
            trigger=trigger,
            attempt=attempt,
            occurred_at=occurred_at,
        )
        self.repository.append_attempt(**values, status="started")
        try:
            self.hotspot_service.sync(trading_date, fetched_at=occurred_at)
        except Exception as error:
            self.repository.append_attempt(
                **values,
                status="failed",
                error_code=_error_code(error),
            )
            return
        self.repository.append_attempt(**values, status="completed")

    def _run_market_sentiment(
        self,
        phase: str,
        trading_date: date,
        slot: str,
        *,
        occurred_at: datetime,
        trigger: str,
    ) -> None:
        if self.market_sentiment_service is None or phase == "premarket":
            return
        local_now = occurred_at.astimezone(CHINA_TZ)
        if local_now.date() != trading_date:
            return
        if phase == "intraday" and not time(9, 30) <= local_now.time() < time(15, 0):
            return
        if phase == "postclose" and local_now.time() < time(15, 0):
            return
        job_key = f"{trading_date.isoformat()}:{phase}:{slot}:sentiment"
        events = self.repository.attempts_for(job_key)
        attempt_count = max((item["attempt"] for item in events), default=0)
        if (
            any(item["status"] == "completed" for item in events)
            or attempt_count >= self.max_attempts
        ):
            return
        attempt = attempt_count + 1
        values = dict(
            job_key=job_key,
            phase=f"{phase}_sentiment",
            trading_date=trading_date,
            slot=f"{slot}:sentiment",
            trigger=trigger,
            attempt=attempt,
            occurred_at=occurred_at,
        )
        self.repository.append_attempt(**values, status="started")
        try:
            snapshot = self.market_sentiment_service.refresh(occurred_at)
        except Exception as error:
            self.repository.append_attempt(
                **values,
                status="failed",
                error_code=_error_code(error),
            )
            return
        self.repository.append_attempt(
            **values,
            status="completed",
            report_id=getattr(snapshot, "snapshot_id", None),
        )

    def _run_first_limit_up(
        self, trading_date: date, slot: str, *, occurred_at: datetime, trigger: str
    ) -> None:
        job_key = f"{trading_date.isoformat()}:postclose:{slot}:first-limit-up"
        events = self.repository.attempts_for(job_key)
        attempt_count = max((item["attempt"] for item in events), default=0)
        if (
            any(item["status"] == "completed" for item in events)
            or attempt_count >= self.max_attempts
        ):
            return
        attempt = attempt_count + 1
        values = dict(
            job_key=job_key,
            phase="first_limit_up",
            trading_date=trading_date,
            slot=f"{slot}:first-limit-up",
            trigger=trigger,
            attempt=attempt,
            occurred_at=occurred_at,
        )
        self.repository.append_attempt(**values, status="started")
        try:
            result = self.first_limit_up_service.refresh(trading_date)
            if inspect.isawaitable(result):
                result = asyncio.run(result)
        except Exception as error:
            self.repository.append_attempt(
                **values, status="failed", error_code=_error_code(error)
            )
            return
        self.repository.append_attempt(
            **values, status="completed", report_id=getattr(result, "rule_version", None)
        )

    def _postclose_history_ready(self, trading_date: date) -> bool:
        service = self.full_market_history_service
        if service is None:
            return True
        coverage = service.coverage(trading_date)
        coverage_ready = (
            coverage.universe_count > 0
            and coverage.eligible_count / coverage.universe_count
            >= MIN_ANALYSIS_COVERAGE_RATIO
        )
        current = service.current_job()
        if current is not None and current.state in ("pending", "running", "paused"):
            job = current
        elif coverage_ready:
            job = service.create_incremental(trading_date)
        else:
            job = service.create_backfill()
        if job.state == "pending":
            if (
                self.history_sync_submitter is not None
                and job.job_id not in self._submitted_history_jobs
            ):
                self.history_sync_submitter(service.run, job.job_id)
                self._submitted_history_jobs.add(job.job_id)
            return False
        if job.state != "completed":
            return False
        coverage = service.coverage(trading_date)
        if coverage.universe_count <= 0:
            return False
        return (
            coverage.eligible_count / coverage.universe_count
            >= MIN_ANALYSIS_COVERAGE_RATIO
        )

    def _latest_due_postclose_date(self, local_now: datetime) -> date | None:
        latest = None
        for days_ago in range(self.catchup_days, -1, -1):
            candidate = local_now.date() - timedelta(days=days_ago)
            scheduled_at = datetime.combine(candidate, time(15, 30), CHINA_TZ)
            if self.calendar.is_trading_day(candidate) and local_now >= scheduled_at:
                latest = candidate
        return latest


def _error_code(error: Exception) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", error.__class__.__name__).lower()
