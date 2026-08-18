from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from threading import RLock
from zoneinfo import ZoneInfo

from qibao_api.contracts.late_session_selection import (
    LateSessionCandidateResult,
    LateSessionMonitorStage,
)


CHINA_TZ = ZoneInfo("Asia/Shanghai")


def classify_monitor_stage(now: datetime) -> LateSessionMonitorStage:
    local = now.astimezone(CHINA_TZ) if now.tzinfo else now.replace(tzinfo=CHINA_TZ)
    current = local.time().replace(tzinfo=None)
    if current < time(14, 0):
        return "idle"
    if current < time(14, 25):
        return "precompute"
    if current < time(14, 30):
        return "reduce_pool"
    if current < time(14, 50):
        return "monitor"
    if current < time(14, 57):
        return "confirm"
    if current < time(15, 0):
        return "closing_auction"
    return "frozen"


@dataclass
class _LifecycleState:
    candidate: LateSessionCandidateResult
    first_seen_at: datetime
    continuous_started_at: datetime | None
    continuous_hits: int
    trigger_count: int


class LateSessionLifecycleTracker:
    def __init__(self, *, confirmation_hits: int = 3) -> None:
        if confirmation_hits < 1:
            raise ValueError("confirmation_hits must be positive")
        self.confirmation_hits = confirmation_hits
        self._lock = RLock()
        self._trading_date: date | None = None
        self._states: dict[str, _LifecycleState] = {}

    def update(
        self,
        trading_date: date,
        candidates: tuple[LateSessionCandidateResult, ...],
        observed_at: datetime,
    ) -> tuple[LateSessionCandidateResult, ...]:
        with self._lock:
            if trading_date != self._trading_date:
                self._trading_date = trading_date
                self._states.clear()

            current_symbols = {item.quote.symbol for item in candidates}
            updated: list[LateSessionCandidateResult] = []
            for candidate in candidates:
                updated.append(self._update_candidate(candidate, observed_at))

            for symbol in tuple(self._states):
                if symbol in current_symbols:
                    continue
                previous = self._states[symbol]
                invalidated = previous.candidate.model_copy(update={
                    "lifecycle_status": "invalidated",
                    "last_updated_at": observed_at,
                    "continuous_hits": 0,
                    "continuous_seconds": 0,
                    "latest_change": "候选状态已失效",
                    "invalidation_reason": "已不在当前候选池",
                })
                previous.candidate = invalidated
                previous.continuous_started_at = None
                previous.continuous_hits = 0
                updated.append(invalidated)
            return tuple(updated)

    def _update_candidate(
        self,
        candidate: LateSessionCandidateResult,
        observed_at: datetime,
    ) -> LateSessionCandidateResult:
        symbol = candidate.quote.symbol
        previous = self._states.get(symbol)
        first_seen_at = previous.first_seen_at if previous is not None else observed_at
        unavailable = any(rule.status == "unavailable" for rule in candidate.rules)
        complete_hit = candidate.passed and not unavailable

        if unavailable:
            status = "data_pending"
            continuous_hits = 0
            continuous_started_at = None
            latest_change = "真实字段待补齐，不进入严格候选"
        elif complete_hit:
            continuous_hits = (previous.continuous_hits if previous is not None else 0) + 1
            continuous_started_at = (
                previous.continuous_started_at
                if previous is not None and previous.continuous_started_at is not None
                else observed_at
            )
            status = "strict_passed" if continuous_hits >= self.confirmation_hits else "near_match"
            latest_change = (
                f"连续满足 {self.confirmation_hits} 次，升级为严格通过"
                if status == "strict_passed" and (previous is None or previous.candidate.lifecycle_status != "strict_passed")
                else f"连续满足 {continuous_hits}/{self.confirmation_hits} 次"
            )
        else:
            status = "near_match"
            continuous_hits = 0
            continuous_started_at = None
            latest_change = "存在未通过规则，保留为接近候选"

        was_strict = previous is not None and previous.candidate.lifecycle_status == "strict_passed"
        trigger_count = previous.trigger_count if previous is not None else 0
        if status == "strict_passed" and not was_strict:
            trigger_count += 1
        continuous_seconds = (
            max(0, int((observed_at - continuous_started_at).total_seconds()))
            if continuous_started_at is not None
            else 0
        )
        result = candidate.model_copy(update={
            "lifecycle_status": status,
            "first_seen_at": first_seen_at,
            "last_updated_at": observed_at,
            "continuous_hits": continuous_hits,
            "continuous_seconds": continuous_seconds,
            "trigger_count": trigger_count,
            "rule_bitmap": _rule_bitmap(candidate),
            "latest_change": latest_change,
            "invalidation_reason": None,
        })
        self._states[symbol] = _LifecycleState(
            candidate=result,
            first_seen_at=first_seen_at,
            continuous_started_at=continuous_started_at,
            continuous_hits=continuous_hits,
            trigger_count=trigger_count,
        )
        return result


def _rule_bitmap(candidate: LateSessionCandidateResult) -> str:
    values = {"passed": "1", "disabled": "1", "failed": "0", "unavailable": "x"}
    return "".join(values[rule.status] for rule in candidate.rules)
