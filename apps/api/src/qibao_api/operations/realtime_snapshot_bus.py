from __future__ import annotations

import json
import queue
import threading
from datetime import datetime
from typing import Any


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
        self._latest: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[queue.Queue[dict[str, Any]], frozenset[str] | None] = {}

    def subscribe(self, kinds: set[str] | frozenset[str] | None = None) -> queue.Queue[dict[str, Any]]:
        subscription: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self.max_queue_size)
        with self._lock:
            self._subscribers[subscription] = None if kinds is None else frozenset(kinds)
        return subscription

    def unsubscribe(self, subscription: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.pop(subscription, None)

    def latest(self, kind: str) -> dict[str, Any] | None:
        with self._lock:
            event = self._latest.get(kind)
            return dict(event) if event is not None else None

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
            event = {
                "event_id": f"{kind}-{self._sequence}",
                "kind": kind,
                "sequence": self._sequence,
                "observed_at": observed_at.isoformat(),
                "source": source,
                "freshness": freshness,
                "payload": payload,
            }
            self._latest[kind] = event
            subscribers = tuple(self._subscribers.items())
        for subscription, kinds in subscribers:
            if kinds is not None and kind not in kinds:
                continue
            self._offer(subscription, event)
        return event

    @staticmethod
    def _offer(subscription: queue.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        try:
            subscription.put_nowait(event)
        except queue.Full:
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
