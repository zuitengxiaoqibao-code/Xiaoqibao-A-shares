from __future__ import annotations

import json
import queue
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class RealtimeSnapshotBus:
    """In-process fan-out for verified real-time snapshots.

    Producers publish only after a source snapshot has been accepted by the
    domain service. Subscribers receive bounded queues so a slow UI cannot
    block the market refresh workers. Dropped intermediate events are safe:
    consumers can always request the latest immutable snapshot.
    """

    def __init__(self, *, max_queue_size: int = 32) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be positive")
        self.max_queue_size = max_queue_size
        self._lock = threading.RLock()
        self._sequence = 0
        self._stream_id = uuid4().hex
        self._stream_started_at = datetime.now(timezone.utc).isoformat()
        self._latest: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[queue.Queue[dict[str, Any]], frozenset[str] | None] = {}
        self._published = 0
        self._dropped = 0
        self._subscriptions_total = 0

    def subscribe(self, kinds: set[str] | frozenset[str] | None = None) -> queue.Queue[dict[str, Any]]:
        subscription: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self.max_queue_size)
        with self._lock:
            self._subscribers[subscription] = None if kinds is None else frozenset(kinds)
            self._subscriptions_total += 1
        return subscription

    def unsubscribe(self, subscription: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.pop(subscription, None)

    def status(self) -> dict[str, int]:
        with self._lock:
            return {
                "active_subscribers": len(self._subscribers),
                "published": self._published,
                "dropped_intermediate": self._dropped,
                "subscriptions_total": self._subscriptions_total,
                "latest_topics": len(self._latest),
            }

    def latest(self, kind: str) -> dict[str, Any] | None:
        with self._lock:
            event = self._latest.get(kind)
            return deepcopy(event) if event is not None else None

    def publish(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        observed_at: datetime,
        source: str,
        freshness: str,
    ) -> dict[str, Any]:
        if not kind.strip():
            raise ValueError("snapshot kind must not be empty")
        with self._lock:
            self._sequence += 1
            self._published += 1
            event = {
                "event_id": f"{kind}-{self._sequence}",
                "kind": kind,
                "sequence": self._sequence,
                "stream_id": self._stream_id,
                "stream_started_at": self._stream_started_at,
                "observed_at": observed_at.isoformat(),
                "source": source,
                "freshness": freshness,
                "payload": deepcopy(payload),
            }
            self._latest[kind] = event
            for subscription, kinds in self._subscribers.items():
                if kinds is not None and kind not in kinds:
                    continue
                self._offer(subscription, deepcopy(event))
            return deepcopy(event)

    def _offer(self, subscription: queue.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        try:
            subscription.put_nowait(event)
        except queue.Full:
            with self._lock:
                self._dropped += 1
            try:
                subscription.get_nowait()
            except queue.Empty:
                pass
            try:
                subscription.put_nowait(event)
            except queue.Full:
                pass

    @staticmethod
    def sse_frame(event: dict[str, Any]) -> str:
        kind = str(event.get("kind", "snapshot"))
        event_id = str(event.get("event_id", ""))
        data = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        return f"id: {event_id}\nevent: {kind}\ndata: {data}\n\n"
