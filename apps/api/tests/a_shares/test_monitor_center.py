from datetime import datetime, timedelta, timezone

import pytest

from qibao_api.a_shares.monitor_center import AlertDeliveryQueue, MonitorCenterService, MonitorRuntime
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


def test_monitor_rule_dedupes_during_cooldown_and_persists_delivery_state(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "涨幅提醒", "conditions": {"change_pct": {"gte": 5}}, "cooldown_seconds": 60})
    now = datetime(2026, 8, 21, 2, 0, tzinfo=timezone.utc)
    first = service.evaluate({"symbol": "600519", "change_pct": 6}, now)
    second = service.evaluate({"symbol": "600519", "change_pct": 6}, now + timedelta(seconds=10))
    assert first is not None
    assert second is None
    assert service.history(10)[0]["delivery"]["in_app"] == "pending"


def test_monitor_unconfigured_feishu_is_explicit(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"volume": {"gte": 1}}})
    alert = service.evaluate({"symbol": "600519", "volume": 2}, datetime.now(timezone.utc))
    assert alert is not None
    assert service.deliver(alert["alert_id"], feishu_configured=False)["feishu"] == "未配置"


def test_delivery_queue_isolates_tts_failure_from_feishu_and_in_app():
    def failed_tts(_alert):
        raise RuntimeError("tts failed")

    queue = AlertDeliveryQueue(tts=failed_tts, feishu=lambda _alert: None)
    result = queue.dispatch({"alert_id": "a1", "symbol": "600519"})
    assert result == {"in_app": "sent", "tts": "failed", "feishu": "sent"}


def test_pending_tts_can_be_completed_without_changing_feishu(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"change_pct": {"gte": 5}}})
    alert = service.evaluate({"symbol": "600519", "change_pct": 6}, datetime.now(timezone.utc))

    assert service.pending_tts()[0]["alert_id"] == alert["alert_id"]
    state = service.complete_delivery(alert["alert_id"], "tts", "sent")

    assert state["tts"] == "sent"
    assert state["feishu"] == "pending"
    assert service.pending_tts() == []


def test_delivery_state_rejects_unknown_status(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {"id": "r1", "name": "提醒", "conditions": {"change_pct": {"gte": 5}}}
    )
    alert = service.evaluate(
        {"symbol": "600519", "change_pct": 6}, datetime.now(timezone.utc)
    )

    with pytest.raises(ValueError, match="不支持的告警投递状态"):
        service.complete_delivery(alert["alert_id"], "tts", "unknown")


def test_runtime_consumes_verified_bus_snapshot_and_delivers_feishu(tmp_path):
    bus = RealtimeSnapshotBus()
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"change_pct": {"gte": 5}}})

    class Delivery:
        def send(self, **_payload):
            return type("Result", (), {"status": "sent"})()

    runtime = MonitorRuntime(bus, service, feishu=Delivery())
    runtime.start()
    try:
        bus.publish(
            "quant_strategy",
            {"symbol": "600519", "change_pct": 6},
            observed_at=datetime.now(timezone.utc),
            source="test",
            freshness="verified",
        )
        for _ in range(20):
            if service.history():
                break
            import time
            time.sleep(0.01)
        alert = service.history()[0]
        assert alert["delivery"]["feishu"] == "sent"
        assert alert["delivery"]["tts"] == "pending"
    finally:
        runtime.close()


def test_runtime_does_not_send_feishu_when_rule_channel_is_disabled(tmp_path):
    bus = RealtimeSnapshotBus()
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({
        "id": "r1",
        "name": "提醒",
        "conditions": {"change_pct": {"gte": 5}},
        "channels": {"in_app": True, "tts": True, "feishu": False},
    })

    class Delivery:
        calls = 0
        def send(self, **_payload):
            self.calls += 1
            return type("Result", (), {"status": "sent"})()

    delivery = Delivery()
    runtime = MonitorRuntime(bus, service, feishu=delivery)
    runtime.start()
    try:
        bus.publish(
            "quant_strategy", {"symbol": "600519", "change_pct": 6},
            observed_at=datetime.now(timezone.utc), source="test", freshness="verified",
        )
        for _ in range(20):
            if service.history():
                break
            import time
            time.sleep(0.01)
        assert service.history()[0]["delivery"]["feishu"] == "未配置"
        assert delivery.calls == 0
    finally:
        runtime.close()


def test_rule_matches_only_its_topic_and_supports_nested_field_paths(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "risk-high",
            "name": "风险升高",
            "topics": ["quant_strategy"],
            "conditions": {"regime.risk_score": {"gte": 65}},
        }
    )
    now = datetime.now(timezone.utc)

    assert (
        service.evaluate(
            {"regime": {"risk_score": 70}}, now, topic="market_overview"
        )
        is None
    )
    alert = service.evaluate(
        {"regime": {"risk_score": 70}}, now, topic="quant_strategy"
    )

    assert alert is not None
    assert alert["topic"] == "quant_strategy"


def test_rule_channels_are_isolated_in_alert_delivery_state(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "risk-high",
            "name": "风险升高",
            "conditions": {"risk_score": {"gte": 65}},
            "channels": {"in_app": True, "tts": False, "feishu": True},
        }
    )

    alert = service.evaluate(
        {"risk_score": 70}, datetime.now(timezone.utc), topic="quant_strategy"
    )

    assert alert["delivery"] == {
        "in_app": "sent",
        "tts": "未配置",
        "feishu": "pending",
    }


def test_pending_tts_excludes_expired_alerts(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {"id": "r1", "name": "提醒", "conditions": {"change_pct": {"gte": 5}}}
    )
    service.evaluate(
        {"symbol": "600519", "change_pct": 6},
        datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert service.pending_tts(max_age_seconds=300) == []


def test_rule_can_pause_and_resume_with_active_alert_lifecycle(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "风险提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))

    paused = service.set_rule_enabled("r1", False)
    assert paused["enabled"] is False
    assert service.history()[0]["alert_id"] == alert["alert_id"]
    assert service.history()[0]["state"] == "recovered"
    assert service.history()[0]["recovery_reason"] == "规则已暂停"
    assert service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc)) is None

    resumed = service.set_rule_enabled("r1", True)
    assert resumed["enabled"] is True


def test_rule_delete_keeps_alert_audit_history(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "风险提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))

    result = service.delete_rule("r1")
    assert result == {"status": "deleted", "rule_id": "r1"}
    assert service.rule_views() == []
    assert service.history()[0]["alert_id"] == alert["alert_id"]
    assert service.history()[0]["recovery_reason"] == "规则已删除"

    with pytest.raises(KeyError, match="监控规则不存在"):
        service.delete_rule("missing")
