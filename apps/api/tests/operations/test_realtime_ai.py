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
        })()


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
        assert len(gateway.requests) == 1
        assert queue.status()["submitted"] == 1
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
