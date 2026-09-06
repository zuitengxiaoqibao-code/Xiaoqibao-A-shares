from datetime import UTC, datetime
import time

from qibao_api.operations.realtime_ai import RealtimeAITriggerQueue
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


NOW = datetime(2026, 8, 18, 2, 30, tzinfo=UTC)


class Gateway:
    def __init__(self):
        self.requests = []

    def explain(self, request):
        self.requests.append(request)
        return type("Result", (), {
            "status": "unavailable",
            "explanation": None,
            "statements": (),
            "provider": "unconfigured",
            "model": "none",
            "prompt_version": "decision-v1",
            "generated_at": NOW,
            "evidence_ids": tuple(item.evidence_id for item in request.evidence),
            "invalid_output_count": 1,
            "provider_error_count": 0,
        })()

    def configuration_identity(self):
        return ("configured", "openai-compatible", "model-a")


def test_realtime_ai_deduplicates_unchanged_market_snapshots_and_publishes_evidence() -> None:
    bus = RealtimeSnapshotBus()
    gateway = Gateway()
    queue = RealtimeAITriggerQueue(bus, gateway, dedupe_seconds=60)
    queue.start()
    try:
        payload = {
            "as_of": "2026-08-18",
            "status": "partial",
            "regime": {"regime": "轮动震荡", "risk_score": "42", "emotion_score": "55", "coverage_percent": "85"},
            "market_data": {"phase": "intraday"},
            "anomalies": [],
            "live_feed": [],
        }
        bus.publish("market_overview", payload, observed_at=NOW, source="tdx-local", freshness="live")
        bus.publish("market_overview", payload, observed_at=NOW, source="tdx-local", freshness="live")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and bus.latest("ai_analysis") is None:
            time.sleep(0.01)
        analysis = bus.latest("ai_analysis")
        assert analysis is not None
        assert analysis["payload"]["input_snapshot_hash"]
        assert analysis["payload"]["fallback"] is True
        assert analysis["payload"]["ai_state"] == "output_invalid"
        assert analysis["payload"]["ai_message"] == "AI 接口已连接，但返回内容未通过证据校验，已保留规则分析"
        assert len(gateway.requests) == 1
        assert queue.status()["submitted"] == 1
    finally:
        queue.close()


def test_realtime_ai_marks_missing_configuration_without_hiding_rule_evidence() -> None:
    bus = RealtimeSnapshotBus()
    gateway = Gateway()
    gateway.configuration_identity = lambda: ("unconfigured", "missing", "decision-v1")
    queue = RealtimeAITriggerQueue(bus, gateway, dedupe_seconds=60)
    queue.start()
    try:
        bus.publish(
            "news_events",
            {"snapshot_id": "news-1", "events": [{"event_id": "event-1"}]},
            observed_at=NOW,
            source="news-cache",
            freshness="live",
        )
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and bus.latest("ai_analysis") is None:
            time.sleep(0.01)
        payload = bus.latest("ai_analysis")["payload"]
        assert payload["ai_state"] == "unconfigured"
        assert payload["ai_message"] == "尚未配置 AI 接口，已保留规则分析"
        assert payload["evidence_ids"]
    finally:
        queue.close()


def test_realtime_ai_preserves_gateway_timeout_state() -> None:
    bus = RealtimeSnapshotBus()

    class TimeoutGateway(Gateway):
        def explain(self, request):
            self.requests.append(request)
            return type("Result", (), {
                "status": "unavailable", "explanation": None, "statements": (),
                "provider": "openai-compatible", "model": "model-a",
                "prompt_version": "decision-v1", "generated_at": NOW,
                "evidence_ids": tuple(item.evidence_id for item in request.evidence),
                "ai_state": "timeout", "ai_message": "AI 接口连接超时，已保留规则分析",
            })()

    queue = RealtimeAITriggerQueue(bus, TimeoutGateway(), dedupe_seconds=60)
    queue.start()
    try:
        bus.publish(
            "news_events",
            {"snapshot_id": "news-timeout", "events": [{"event_id": "event-1"}]},
            observed_at=NOW, source="news-cache", freshness="live",
        )
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and bus.latest("ai_analysis") is None:
            time.sleep(0.01)
        payload = bus.latest("ai_analysis")["payload"]
        assert payload["ai_state"] == "timeout"
        assert payload["ai_message"] == "AI 接口连接超时，已保留规则分析"
    finally:
        queue.close()


def test_realtime_ai_triggers_when_quant_candidate_status_changes() -> None:
    bus = RealtimeSnapshotBus()
    gateway = Gateway()
    queue = RealtimeAITriggerQueue(bus, gateway, dedupe_seconds=60)
    queue.start()
    try:
        base = {"as_of": "2026-08-18", "formula_version": "a-share-short-strategy-v2.0", "regime": {"regime": "情绪主升", "risk_score": "20"}, "candidates": []}
        changed = {**base, "candidates": [{"symbol": "600519", "status": "watch", "strategy_score": "78"}]}
        bus.publish("quant_strategy", base, observed_at=NOW, source="tdx-local", freshness="live")
        bus.publish("quant_strategy", changed, observed_at=NOW, source="tdx-local", freshness="live")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and queue.status()["submitted"] < 2:
            time.sleep(0.01)
        assert queue.status()["submitted"] == 2
    finally:
        queue.close()


def test_late_session_lifecycle_change_builds_ai_trigger() -> None:
    bus = RealtimeSnapshotBus()
    worker = RealtimeAITriggerQueue(bus)
    event = {
        "kind": "late_session_candidates",
        "observed_at": "2026-08-18T06:31:00+00:00",
        "source": "tdx-local-realtime",
        "freshness": "live",
        "payload": {
            "trading_date": "2026-08-18",
            "monitor_stage": "monitor",
            "source_quality": "ready",
            "candidates": [{
                "quote": {"symbol": "600000", "name": "浦发银行"},
                "lifecycle_status": "strict_passed",
                "rule_bitmap": "1111111",
            }],
        },
    }

    trigger = worker._build_trigger(event)

    assert trigger is not None
    assert trigger["reason"] == "initial_verified_snapshot"
    assert trigger["kind"] == "late_session_candidates"
