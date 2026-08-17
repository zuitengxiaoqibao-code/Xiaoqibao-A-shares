from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from qibao_api.a_shares.late_session_selection import (
    classify_phase,
    evaluate_candidate,
)
from qibao_api.contracts.late_session_selection import LateSessionQuote
from qibao_api.contracts.late_session_selection import LateSessionRuleSettings
from qibao_api.contracts.late_session_selection import LateSessionCandidateResult, LateSessionSelectionResponse
from qibao_api.a_shares.late_session_ai import LateSessionAIAnalyzer


def quote(**overrides) -> LateSessionQuote:
    values = dict(
        symbol="600519",
        name="贵州茅台",
        price=Decimal("105"),
        previous_close=Decimal("100"),
        change_percent=Decimal("5"),
        volume_ratio=Decimal("3"),
        turnover_rate=Decimal("10"),
        market_cap_yi=Decimal("100"),
        twenty_day_limit_up_count=1,
        intraday_average_price=Decimal("104"),
        observed_at=datetime(2026, 8, 17, 6, 45, tzinfo=timezone.utc),
        source="tdx-local-realtime+tencent",
    )
    values.update(overrides)
    return LateSessionQuote(**values)


def test_phase_boundaries_are_strict() -> None:
    tz = ZoneInfo("Asia/Shanghai")
    assert classify_phase(datetime(2026, 8, 17, 14, 29, 59, tzinfo=tz)) == "pre_screen"
    assert classify_phase(datetime(2026, 8, 17, 14, 30, tzinfo=tz)) == "live_monitor"
    assert classify_phase(datetime(2026, 8, 17, 14, 59, 59, tzinfo=tz)) == "live_monitor"
    assert classify_phase(datetime(2026, 8, 17, 15, 0, tzinfo=tz)) == "post_close"


def test_candidate_requires_all_seven_rules() -> None:
    result = evaluate_candidate(quote())
    assert result.passed is True
    assert {rule.key for rule in result.rules} == {
        "time_window", "change_percent", "volume_ratio", "turnover_rate",
        "market_cap", "twenty_day_limit_up", "above_intraday_average",
    }


def test_missing_intraday_average_cannot_pass_by_proxy() -> None:
    result = evaluate_candidate(quote(intraday_average_price=None))
    average_rule = next(rule for rule in result.rules if rule.key == "above_intraday_average")
    assert result.passed is False
    assert average_rule.status == "unavailable"
    assert "分时黄线" in average_rule.detail


def test_custom_rule_settings_change_thresholds_and_can_disable_rules() -> None:
    settings = LateSessionRuleSettings(
        time_enabled=False,
        change_min=Decimal("1"),
        change_max=Decimal("2"),
        volume_ratio_enabled=False,
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
        intraday_average_enabled=False,
    )

    result = evaluate_candidate(
        quote(change_percent=Decimal("1.5"), volume_ratio=None),
        settings=settings,
    )

    assert result.passed is True
    assert next(rule for rule in result.rules if rule.key == "change_percent").status == "passed"
    assert next(rule for rule in result.rules if rule.key == "volume_ratio").status == "disabled"


def test_ai_analyzer_explains_no_candidates_without_claiming_ai() -> None:
    snapshot = LateSessionSelectionResponse(
        status="partial",
        trading_date=date(2026, 8, 17),
        server_time=datetime(2026, 8, 17, 6, 30, tzinfo=timezone.utc),
        phase="live_monitor",
        refresh_interval_ms=1000,
        next_refresh_ms=1000,
        source_quality="partial",
        universe_count=5200,
        quote_count=5200,
        candidate_count=0,
        rules=(),
        data_state="no_candidates",
        no_data_reason="全市场已扫描 5200 只，但当前规则没有股票满足全部条件",
    )

    result = LateSessionAIAnalyzer(settings=None).analyze_sync(snapshot)

    assert result.status == "no_candidates"
    assert result.mode == "unavailable"
    assert "没有产生候选" in result.summary
    assert result.reason == snapshot.no_data_reason


def test_ai_analyzer_falls_back_to_rule_interpretation_when_unconfigured() -> None:
    snapshot = LateSessionSelectionResponse(
        status="ready",
        trading_date=date(2026, 8, 17),
        server_time=datetime(2026, 8, 17, 6, 30, tzinfo=timezone.utc),
        phase="live_monitor",
        refresh_interval_ms=1000,
        next_refresh_ms=1000,
        source_quality="ready",
        universe_count=5200,
        quote_count=5200,
        candidate_count=1,
        rules=(),
        candidates=(LateSessionCandidateResult(quote=quote(), passed=True, rules=()),),
    )

    result = LateSessionAIAnalyzer(settings=None).analyze_sync(snapshot)

    assert result.status == "unconfigured"
    assert result.mode == "rule_interpretation"
    assert "AI" in result.title
    assert result.candidate_count == 1
    assert result.key_points
