from datetime import datetime, timedelta, timezone

from qibao_api.a_shares.monitor_center import AlertDeliveryQueue, MonitorCenterService


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
