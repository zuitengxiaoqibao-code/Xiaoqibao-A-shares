import json
from datetime import datetime, timezone

from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


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
