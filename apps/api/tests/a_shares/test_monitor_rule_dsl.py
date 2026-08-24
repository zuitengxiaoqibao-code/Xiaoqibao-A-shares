from datetime import datetime, timedelta, timezone

import pytest

from qibao_api.a_shares.monitor_center import MonitorCenterService
from qibao_api.a_shares.monitor_center import MonitorRuntime
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


def test_legacy_condition_map_is_normalized_to_all_condition_list(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")

    normalized = service.normalize_rule(
        {"id": "r1", "name": "风险", "conditions": {"risk_score": {"gte": 65}}}
    )

    assert normalized["logic"] == "all"
    assert normalized["conditions"] == [
        {"field": "risk_score", "op": "gte", "value": 65}
    ]
    assert normalized["confirm_count"] == 1
    assert normalized["freshness_seconds"] == 120


def test_any_logic_matches_when_one_condition_is_true(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    rule = service.normalize_rule(
        {
            "id": "r1",
            "name": "波动或放量",
            "logic": "any",
            "conditions": [
                {"field": "change_pct", "op": "gte", "value": 5},
                {"field": "volume_ratio", "op": "gte", "value": 2},
            ],
        }
    )

    assert service.matches_rule({"change_pct": 0, "volume_ratio": 2.1}, rule)
    assert not service.matches_rule({"change_pct": 0, "volume_ratio": 1.2}, rule)


def test_n_of_logic_requires_configured_number_of_conditions(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    rule = service.normalize_rule(
        {
            "id": "r1",
            "name": "组合信号",
            "logic": "n_of",
            "n": 2,
            "conditions": [
                {"field": "a", "op": "eq", "value": 1},
                {"field": "b", "op": "eq", "value": 1},
                {"field": "c", "op": "eq", "value": 1},
            ],
        }
    )

    assert service.matches_rule({"a": 1, "b": 1, "c": 0}, rule)
    assert not service.matches_rule({"a": 1, "b": 0, "c": 0}, rule)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"id": "r1", "name": "坏规则", "conditions": [{"field": "x", "op": "near", "value": 1}]}, "不支持的规则比较符"),
        ({"id": "r1", "name": "坏规则", "conditions": [], "confirm_count": 0}, "规则至少需要一个触发条件"),
        ({"id": "r1", "name": "坏规则", "conditions": [{"field": "x", "op": "gte", "value": 1}], "confirm_window_seconds": -1}, "确认窗口必须大于等于 1 秒"),
        ({"id": "r1", "name": "坏规则", "conditions": [{"field": "x", "op": "gte", "value": 1}], "logic": "n_of"}, "n_of 规则必须提供 n"),
    ],
)
def test_invalid_rule_is_rejected_with_chinese_reason(tmp_path, payload, message):
    service = MonitorCenterService(tmp_path / "monitor.json")

    with pytest.raises(ValueError, match=message):
        service.validate_rule(payload)


def test_rule_topics_and_channels_are_preserved(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")

    normalized = service.validate_rule(
        {
            "id": "r1",
            "name": "主题规则",
            "topics": ["quant_strategy"],
            "conditions": [{"field": "risk_score", "op": "gte", "value": 65}],
            "channels": {"in_app": True, "tts": False, "feishu": True},
            "severity": "critical",
        }
    )

    assert normalized["topics"] == ["quant_strategy"]
    assert normalized["channels"]["tts"] is False
    assert normalized["severity"] == "critical"


def test_stale_snapshot_is_not_a_match_when_freshness_is_required(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "r1",
            "name": "实时风险",
            "conditions": {"risk_score": {"gte": 65}},
            "freshness_seconds": 5,
            "require_freshness": True,
        }
    )

    alert = service.evaluate(
        {"risk_score": 70, "observed_at": "2026-08-24T01:59:00+00:00"},
        datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc),
    )

    assert alert is None


def test_confirm_count_requires_consecutive_snapshots_before_alert(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "r1",
            "name": "连续确认",
            "conditions": {"risk_score": {"gte": 65}},
            "confirm_count": 3,
            "confirm_window_seconds": 10,
        }
    )
    start = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)

    assert service.evaluate({"risk_score": 70}, start) is None
    assert service.evaluate({"risk_score": 71}, start + timedelta(seconds=2)) is None
    alert = service.evaluate({"risk_score": 72}, start + timedelta(seconds=4))

    assert alert is not None
    assert alert["trigger_count"] == 1


def test_confirmation_window_resets_after_gap(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "r1",
            "name": "窗口确认",
            "conditions": {"risk_score": {"gte": 65}},
            "confirm_count": 2,
            "confirm_window_seconds": 5,
        }
    )
    start = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)

    assert service.evaluate({"risk_score": 70}, start) is None
    assert service.evaluate({"risk_score": 71}, start + timedelta(seconds=6)) is None
    assert service.history() == []


def test_cooldown_blocks_new_trigger_even_when_input_changes(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "r1",
            "name": "冷却",
            "conditions": {"risk_score": {"gte": 65}},
            "cooldown_seconds": 60,
        }
    )
    start = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)

    first = service.evaluate({"risk_score": 70}, start)
    second = service.evaluate({"risk_score": 72}, start + timedelta(seconds=10))

    assert first is not None
    assert second is None


def test_custom_recovery_condition_is_used(tmp_path):
    service = MonitorCenterService(tmp_path / "monitor.json")
    service.save_rule(
        {
            "id": "r1",
            "name": "恢复条件",
            "conditions": {"risk_score": {"gte": 65}},
            "recovery": {"enabled": True, "conditions": {"risk_score": {"lte": 50}}},
        }
    )
    start = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)
    alert = service.evaluate({"symbol": "600519", "risk_score": 70}, start)

    assert alert is not None
    assert service.evaluate_recovery(
        {"symbol": "600519", "risk_score": 60}, start + timedelta(seconds=1)
    ) is None
    recovery = service.evaluate_recovery(
        {"symbol": "600519", "risk_score": 50}, start + timedelta(seconds=2)
    )
    assert recovery is not None


def test_runtime_subscribes_to_stock_and_data_source_topics(tmp_path):
    bus = RealtimeSnapshotBus()
    service = MonitorCenterService(tmp_path / "monitor.json")
    runtime = MonitorRuntime(bus, service)
    runtime.start()
    try:
        subscription_kinds = next(iter(bus._subscribers.values()))
        assert subscription_kinds is not None
        assert {"stock_observation", "data_sources"}.issubset(subscription_kinds)
    finally:
        runtime.close()
