from dataclasses import dataclass
from datetime import datetime
from typing import Literal


FreshnessState = Literal["live", "fresh", "stale", "expired", "unavailable"]


@dataclass(frozen=True)
class FreshnessPolicy:
    live_seconds: int
    fresh_seconds: int
    stale_seconds: int

    def __post_init__(self) -> None:
        if not (0 <= self.live_seconds <= self.fresh_seconds <= self.stale_seconds):
            raise ValueError("freshness thresholds must be monotonic")


@dataclass(frozen=True)
class FreshnessResult:
    state: FreshnessState
    age_seconds: int | None
    reason: str


def classify_freshness(
    observed_at: datetime | None,
    now: datetime,
    policy: FreshnessPolicy,
) -> FreshnessResult:
    if observed_at is None:
        return FreshnessResult("unavailable", None, "没有可核验的观测时间")
    age = max(0, round((now - observed_at).total_seconds()))
    if age <= policy.live_seconds:
        return FreshnessResult("live", age, f"观测年龄不超过 {policy.live_seconds} 秒")
    if age <= policy.fresh_seconds:
        return FreshnessResult("fresh", age, f"观测年龄不超过 {policy.fresh_seconds} 秒")
    if age <= policy.stale_seconds:
        return FreshnessResult("stale", age, f"观测年龄超过 {policy.fresh_seconds} 秒但未过期")
    return FreshnessResult("expired", age, f"观测年龄超过 {policy.stale_seconds} 秒")


DEFAULT_FRESHNESS_POLICIES = {
    "intraday_quote": FreshnessPolicy(120, 300, 900),
    "market_snapshot": FreshnessPolicy(120, 600, 3600),
    "news": FreshnessPolicy(300, 3600, 86400),
    "financial": FreshnessPolicy(86400, 86400 * 120, 86400 * 400),
    "research_report": FreshnessPolicy(86400, 86400 * 30, 86400 * 180),
    "daily_bar": FreshnessPolicy(86400, 86400 * 3, 86400 * 10),
}

