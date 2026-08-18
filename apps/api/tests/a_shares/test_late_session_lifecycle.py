from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from qibao_api.a_shares.late_session_lifecycle import (
    LateSessionLifecycleTracker,
    classify_monitor_stage,
)
from qibao_api.a_shares.late_session_selection import evaluate_candidate
from qibao_api.contracts.late_session_selection import LateSessionQuote


TZ = ZoneInfo("Asia/Shanghai")


def _candidate(at: datetime, *, average: Decimal | None = Decimal("10.20")):
    return evaluate_candidate(LateSessionQuote(
        symbol="600000",
        name="浦发银行",
        price=Decimal("10.50"),
        previous_close=Decimal("10"),
        change_percent=Decimal("5"),
        volume_ratio=Decimal("3"),
        turnover_rate=Decimal("10"),
        market_cap_yi=Decimal("100"),
        twenty_day_limit_up_count=1,
        intraday_average_price=average,
        observed_at=at,
        source="tdx-local-realtime+tencent",
    ))


def test_monitor_stage_boundaries_distinguish_closing_auction() -> None:
    assert classify_monitor_stage(datetime(2026, 8, 18, 13, 59, 59, tzinfo=TZ)) == "idle"
    assert classify_monitor_stage(datetime(2026, 8, 18, 14, 0, tzinfo=TZ)) == "precompute"
    assert classify_monitor_stage(datetime(2026, 8, 18, 14, 25, tzinfo=TZ)) == "reduce_pool"
    assert classify_monitor_stage(datetime(2026, 8, 18, 14, 30, tzinfo=TZ)) == "monitor"
    assert classify_monitor_stage(datetime(2026, 8, 18, 14, 50, tzinfo=TZ)) == "confirm"
    assert classify_monitor_stage(datetime(2026, 8, 18, 14, 57, tzinfo=TZ)) == "closing_auction"
    assert classify_monitor_stage(datetime(2026, 8, 18, 15, 0, tzinfo=TZ)) == "frozen"


def test_lifecycle_requires_three_consecutive_complete_hits() -> None:
    tracker = LateSessionLifecycleTracker(confirmation_hits=3)
    first = tracker.update(date(2026, 8, 18), (_candidate(datetime(2026, 8, 18, 14, 31, tzinfo=TZ)),), datetime(2026, 8, 18, 14, 31, tzinfo=TZ))[0]
    second = tracker.update(date(2026, 8, 18), (_candidate(datetime(2026, 8, 18, 14, 31, 1, tzinfo=TZ)),), datetime(2026, 8, 18, 14, 31, 1, tzinfo=TZ))[0]
    third = tracker.update(date(2026, 8, 18), (_candidate(datetime(2026, 8, 18, 14, 31, 2, tzinfo=TZ)),), datetime(2026, 8, 18, 14, 31, 2, tzinfo=TZ))[0]

    assert first.lifecycle_status == "near_match"
    assert second.lifecycle_status == "near_match"
    assert third.lifecycle_status == "strict_passed"
    assert third.first_seen_at == first.first_seen_at
    assert third.continuous_hits == 3
    assert third.continuous_seconds == 2
    assert third.trigger_count == 1
    assert third.latest_change == "连续满足 3 次，升级为严格通过"
    assert third.rule_bitmap


def test_missing_required_data_never_upgrades_to_strict_passed() -> None:
    tracker = LateSessionLifecycleTracker(confirmation_hits=2)
    at = datetime(2026, 8, 18, 14, 31, tzinfo=TZ)

    first = tracker.update(date(2026, 8, 18), (_candidate(at, average=None),), at)[0]
    second = tracker.update(date(2026, 8, 18), (_candidate(at.replace(second=1), average=None),), at.replace(second=1))[0]

    assert first.lifecycle_status == "data_pending"
    assert second.lifecycle_status == "data_pending"
    assert second.continuous_hits == 0
    assert second.trigger_count == 0


def test_lifecycle_retains_invalidation_reason_and_resets_next_day() -> None:
    tracker = LateSessionLifecycleTracker(confirmation_hits=1)
    at = datetime(2026, 8, 18, 14, 31, tzinfo=TZ)
    passed = tracker.update(date(2026, 8, 18), (_candidate(at),), at)[0]

    invalidated = tracker.update(date(2026, 8, 18), (), at.replace(second=1))[0]
    next_day = datetime(2026, 8, 19, 14, 31, tzinfo=TZ)
    reset = tracker.update(date(2026, 8, 19), (_candidate(next_day),), next_day)[0]

    assert passed.lifecycle_status == "strict_passed"
    assert invalidated.lifecycle_status == "invalidated"
    assert invalidated.invalidation_reason == "已不在当前候选池"
    assert invalidated.trigger_count == 1
    assert reset.lifecycle_status == "strict_passed"
    assert reset.first_seen_at == next_day
    assert reset.trigger_count == 1
