import json
from datetime import datetime, timezone
import threading
from concurrent.futures import ThreadPoolExecutor

from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


def test_bus_isolates_payloads_between_producer_subscribers_and_latest():
    bus = RealtimeSnapshotBus()
    first, second = bus.subscribe(), bus.subscribe()
    payload = {"nested": {"value": 1}}
    event = bus.publish("news_events", payload, observed_at=datetime.now(timezone.utc), source="test", freshness="live")
    payload["nested"]["value"] = 2
    event["payload"]["nested"]["value"] = 3
    first.get_nowait()["payload"]["nested"]["value"] = 4
    bus.latest("news_events")["payload"]["nested"]["value"] = 5
    assert second.get_nowait()["payload"]["nested"]["value"] == 1
    assert bus.latest("news_events")["payload"]["nested"]["value"] == 1
    assert RealtimeSnapshotBus()._stream_id != event["stream_id"]


def test_concurrent_publish_cannot_overtake_a_slow_delivery(monkeypatch):
    bus = RealtimeSnapshotBus()
    subscription = bus.subscribe()
    delivering, release, second_started, second_returned = (threading.Event() for _ in range(4))
    offer = bus._offer

    def slow_offer(target, event):
        if event["sequence"] == 1:
            delivering.set()
            assert release.wait(2)
        offer(target, event)

    monkeypatch.setattr(bus, "_offer", slow_offer)

    def publish(second=False):
        if second:
            second_started.set()
        bus.publish("news_events", {}, observed_at=datetime.now(timezone.utc), source="test", freshness="live")
        if second:
            second_returned.set()

    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(publish)
        assert delivering.wait(2)
        second = executor.submit(publish, True)
        try:
            assert second_started.wait(2)
            assert not second_returned.wait(0.05)
        finally:
            release.set()
        first.result(timeout=2)
        second.result(timeout=2)
    assert [subscription.get_nowait()["sequence"] for _ in range(2)] == [1, 2]


def test_bus_publishes_monotonic_events_and_replays_latest_snapshot() -> None:
    bus = RealtimeSnapshotBus(max_queue_size=2)
    subscription = bus.subscribe()
    first = bus.publish(
        "market_overview",
        {"observed_at": "2026-08-18T01:00:00+00:00", "indices": []},
        observed_at=datetime(2026, 8, 18, 1, 0, tzinfo=timezone.utc),
        source="tdx-local-rpc / tencent-index",
        freshness="live",
    )
    second = bus.publish(
        "market_overview",
        {"observed_at": "2026-08-18T01:00:05+00:00", "indices": [{"value": "3823.73"}]},
        observed_at=datetime(2026, 8, 18, 1, 0, 5, tzinfo=timezone.utc),
        source="tdx-local-rpc / tencent-index",
        freshness="live",
    )

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert subscription.get_nowait()["sequence"] == 1
    assert subscription.get_nowait()["sequence"] == 2
    assert bus.latest("market_overview")["sequence"] == 2
    bus.unsubscribe(subscription)
    status = bus.status()
    assert status["published"] == 2
    assert status["subscriptions_total"] == 1
    assert status["active_subscribers"] == 0


def test_bus_filters_subscriptions_and_serializes_sse_frames() -> None:
    bus = RealtimeSnapshotBus()
    subscription = bus.subscribe({"news_events"})
    bus.publish(
        "market_overview",
        {"ignored": True},
        observed_at=datetime(2026, 8, 18, 1, 0, tzinfo=timezone.utc),
        source="test",
        freshness="live",
    )
    event = bus.publish(
        "news_events",
        {"headline": "测试资讯"},
        observed_at=datetime(2026, 8, 18, 1, 0, tzinfo=timezone.utc),
        source="local-news-cache",
        freshness="live",
    )

    assert subscription.qsize() == 1
    frame = bus.sse_frame(event)
    assert frame.startswith("id: news_events-2\nevent: news_events\ndata: ")
    assert frame.endswith("\n\n")
    assert json.loads(frame.split("data: ", 1)[1].strip())["sequence"] == event["sequence"]
    bus.unsubscribe(subscription)


def test_bus_reports_dropped_intermediate_frames_without_blocking_publish() -> None:
    bus = RealtimeSnapshotBus(max_queue_size=1)
    bus.subscribe()
    for value in (1, 2, 3):
        bus.publish(
            "quant_strategy", {"value": value},
            observed_at=datetime(2026, 8, 18, 1, 0, value, tzinfo=timezone.utc),
            source="test", freshness="live",
        )
    assert bus.status()["published"] == 3
    assert bus.status()["dropped_intermediate"] == 2
