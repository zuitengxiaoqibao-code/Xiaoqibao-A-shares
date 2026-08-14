from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.alert_inbox import AlertInbox
from qibao_api.contracts.unified_event import UnifiedDecisionEvent


NOW = datetime(2026, 8, 13, 2, 30, tzinfo=timezone.utc)


def event(**changes) -> UnifiedDecisionEvent:
    values = dict(
        event_id="event-1", source_event_type="announcement", category="risk_event",
        category_reason="risk", headline="公司收到监管立案通知", occurred_at=NOW,
        affected_symbols=("600001",), direction="negative", direction_confidence=Decimal("0.9"),
        strength="high", credibility="verified", source_count=1, follow_up_indicators=("公告进展",),
        interpretation_id="ai-1", evidence_ids=("evidence-1",),
    )
    values.update(changes)
    return UnifiedDecisionEvent(**values)


def test_inbox_deduplicates_sources_and_merges_evidence() -> None:
    inbox = AlertInbox(cooldown=timedelta(minutes=10))
    first = inbox.ingest(event(), now=NOW)
    second = inbox.ingest(event(source_count=2, evidence_ids=("evidence-2",)), now=NOW + timedelta(minutes=1))
    assert first.fingerprint == second.fingerprint
    assert second.status == "cooldown"
    assert second.evidence_ids == ("evidence-1", "evidence-2")
    assert len(inbox.items()) == 1


def test_voice_requires_high_priority_verified_direction_outside_silent_hours() -> None:
    inbox = AlertInbox()
    assert inbox.ingest(event(), now=NOW).voice_eligible is True
    assert inbox.ingest(event(event_id="event-2", headline="待核验传闻", credibility="pending", direction="uncertain", direction_confidence=None, strength="unknown", interpretation_id=None), now=NOW).voice_eligible is False
    quiet = inbox.ingest(event(event_id="event-3", headline="另一风险事件"), now=NOW, silent_start=time(0, 0), silent_end=time(23, 59))
    assert quiet.status == "silent"
    assert quiet.voice_eligible is False
