from datetime import datetime, timezone

from qibao_api.contracts.unified_event import UnifiedDecisionEvent


NOW = datetime(2026, 8, 12, 2, 30, tzinfo=timezone.utc)


def test_unified_event_keeps_unknown_market_effects_explicit() -> None:
    event = UnifiedDecisionEvent(
        event_id="event-1",
        source_event_type="company_announcement",
        category="company_announcement",
        category_reason="event_type:company_announcement",
        headline="公司公告",
        occurred_at=NOW,
        affected_symbols=("600000",),
        industries=(),
        themes=(),
        direction="uncertain",
        direction_confidence=None,
        strength="unknown",
        credibility="verified",
        source_count=1,
        duration="unknown",
        price_reflection="unknown",
        follow_up_indicators=("核对公告执行进度",),
        interpretation_id=None,
        evidence_ids=("citation-1",),
    )

    assert event.duration == "unknown"
    assert event.price_reflection == "unknown"
    assert event.direction_confidence is None


def test_unified_event_rejects_claimed_direction_without_confidence() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="direction confidence"):
        UnifiedDecisionEvent(
            event_id="event-1",
            source_event_type="market_news",
            category="industry_sector",
            category_reason="theme_match",
            headline="板块消息",
            occurred_at=NOW,
            direction="positive",
            direction_confidence=None,
            strength="high",
            credibility="verified",
            source_count=1,
            follow_up_indicators=("观察板块成交额与扩散家数",),
            evidence_ids=("citation-1",),
        )
