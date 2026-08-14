from __future__ import annotations

import hashlib
from datetime import datetime, time, timedelta

from qibao_api.contracts.alert_inbox import AlertInboxItem
from qibao_api.contracts.unified_event import UnifiedDecisionEvent


def event_fingerprint(event: UnifiedDecisionEvent) -> str:
    normalized = "|".join((
        event.category,
        event.headline.strip().casefold(),
        ",".join(sorted(event.affected_symbols)),
        event.occurred_at.isoformat(),
    ))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class AlertInbox:
    def __init__(self, *, cooldown: timedelta = timedelta(minutes=10)) -> None:
        self.cooldown = cooldown
        self._items: dict[str, AlertInboxItem] = {}

    def ingest(
        self,
        event: UnifiedDecisionEvent,
        *,
        now: datetime,
        silent_start: time | None = None,
        silent_end: time | None = None,
    ) -> AlertInboxItem:
        fingerprint = event_fingerprint(event)
        existing = self._items.get(fingerprint)
        if existing is not None:
            merged = existing.model_copy(update={
                "evidence_ids": tuple(dict.fromkeys((*existing.evidence_ids, *event.evidence_ids))),
                "source_count": max(existing.source_count, event.source_count),
                "status": "cooldown" if now - existing.occurred_at < self.cooldown else existing.status,
            })
            self._items[fingerprint] = merged
            return merged
        priority = self._priority(event)
        silent = self._is_silent(now.time(), silent_start, silent_end)
        voice_eligible = (
            priority == "high"
            and event.credibility in {"verified", "multi_source_verified"}
            and event.direction != "uncertain"
            and not silent
        )
        item = AlertInboxItem(
            fingerprint=fingerprint,
            event_id=event.event_id,
            headline=event.headline,
            priority=priority,
            status="silent" if silent else "new",
            occurred_at=event.occurred_at,
            affected_symbols=event.affected_symbols,
            evidence_ids=event.evidence_ids,
            source_count=event.source_count,
            voice_eligible=voice_eligible,
        )
        self._items[fingerprint] = item
        return item

    @staticmethod
    def _priority(event: UnifiedDecisionEvent) -> str:
        if event.category == "risk_event" or event.strength == "high":
            return "high"
        if event.strength == "medium" or event.credibility == "multi_source_verified":
            return "medium"
        return "low"

    @staticmethod
    def _is_silent(value: time, start: time | None, end: time | None) -> bool:
        if start is None or end is None:
            return False
        return start <= value < end if start < end else value >= start or value < end

    def items(self) -> tuple[AlertInboxItem, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.occurred_at, reverse=True))
