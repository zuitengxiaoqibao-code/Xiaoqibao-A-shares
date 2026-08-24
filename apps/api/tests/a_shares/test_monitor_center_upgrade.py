from datetime import datetime, timedelta, timezone

import pytest

from qibao_api.a_shares.monitor_center import MonitorCenterService
from qibao_api.a_shares.monitor_center import MonitorRuntime
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


def test_new_alert_has_lifecycle_defaults_and_summary_counts(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "risk-high",
            "name": "风险升高",
            "topics": ["quant_strategy"],
            "conditions": {"risk_score": {"gte": 65}},
        }
    )
    observed_at = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)

    alert = service.evaluate(
        {"symbol": "600519", "risk_score": 70}, observed_at, topic="quant_strategy"
    )

    assert alert is not None
    assert alert["severity"] == "warning"
    assert alert["state"] == "active"
    assert alert["confirmed"] is False
    assert alert["trigger_count"] == 1
    assert alert["recovered_at"] is None
    summary = service.summary(now=observed_at + timedelta(seconds=5))
    assert summary["alerts"]["total"] == 1
    assert summary["alerts"]["active"] == 1
    assert summary["alerts"]["unconfirmed"] == 1
    assert "quant_strategy" in {item["topic"] for item in summary["topics"]}


def test_confirm_marks_alert_with_user_and_persists(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))

    confirmed = service.confirm(alert["alert_id"], confirmed_by="张三")

    assert confirmed["confirmed"] is True
    assert confirmed["confirmed_by"] == "张三"
    assert confirmed["confirmed_at"]
    assert service.history()[0]["confirmed"] is True


def test_recovery_event_closes_active_alert_and_links_original(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {"id": "r1", "name": "风险提醒", "conditions": {"risk_score": {"gte": 65}}}
    )
    first_time = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)
    alert = service.evaluate(
        {"symbol": "600519", "risk_score": 70}, first_time, topic="quant_strategy"
    )

    recovery = service.evaluate_recovery(
        {"symbol": "600519", "risk_score": 40},
        first_time + timedelta(minutes=1),
        topic="quant_strategy",
    )

    assert recovery is not None
    assert recovery["state"] == "recovered"
    assert recovery["recovery_alert_id"] == alert["alert_id"]
    original = next(item for item in service.history() if item["alert_id"] == alert["alert_id"])
    assert original["state"] == "recovered"
    assert original["recovered_at"]
    assert service.evaluate_recovery(
        {"symbol": "600519", "risk_score": 40},
        first_time + timedelta(minutes=2),
        topic="quant_strategy",
    ) is None


def test_old_alert_json_is_read_with_lifecycle_defaults(tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(
        '{"rules": [], "alerts": [{"alert_id": "a1", "rule_id": "r1", '
        '"symbol": "600519", "observed_at": "2026-08-24T02:00:00+00:00", '
        '"input_hash": "hash", "delivery": {"in_app": "sent"}}]}',
        encoding="utf-8",
    )

    alert = MonitorCenterService(path).history()[0]

    assert alert["severity"] == "warning"
    assert alert["state"] == "active"
    assert alert["confirmed"] is False
    assert alert["trigger_count"] == 1


def test_delivery_retry_requeues_failed_channel(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))
    service.complete_delivery(alert["alert_id"], "feishu", "failed", "网络不可用")

    retried = service.retry_delivery(alert["alert_id"], "feishu")

    assert retried["delivery"]["feishu"] == "pending"
    assert retried["retry_count"]["feishu"] == 1
    assert "feishu" not in retried["delivery_reason"]


def test_confirm_unknown_alert_raises_key_error(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")

    with pytest.raises(KeyError):
        service.confirm("missing")


def test_runtime_emits_recovery_when_verified_snapshot_no_longer_matches(tmp_path):
    bus = RealtimeSnapshotBus()
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {"id": "r1", "name": "风险", "topics": ["quant_strategy"], "conditions": {"risk_score": {"gte": 65}}}
    )
    runtime = MonitorRuntime(bus, service)
    runtime.start()
    first_time = datetime.now(timezone.utc)
    try:
        bus.publish("quant_strategy", {"symbol": "600519", "risk_score": 70}, observed_at=first_time, source="test", freshness="verified")
        bus.publish("quant_strategy", {"symbol": "600519", "risk_score": 40}, observed_at=first_time + timedelta(seconds=1), source="test", freshness="verified")
        for _ in range(40):
            if len(service.history()) >= 2:
                break
            import time
            time.sleep(0.01)
        assert len(service.history()) == 2
        assert service.history()[0]["state"] == "recovered"
    finally:
        runtime.close()
