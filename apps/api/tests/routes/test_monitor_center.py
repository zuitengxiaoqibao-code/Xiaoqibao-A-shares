from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.a_shares.monitor_center import MonitorCenterService
from qibao_api.routes.monitor_center import router


def test_monitor_routes_are_exposed():
    paths = {route.path for route in router.routes}
    assert "/api/v1/monitor-center/rules" in paths
    assert "/api/v1/monitor-center/alerts" in paths
    assert "/api/v1/monitor-center/summary" in paths
    assert "/api/v1/monitor-center/alerts/{alert_id}/confirm" in paths
    assert "/api/v1/monitor-center/alerts/{alert_id}/delivery/retry" in paths


def _client(tmp_path):
    app = FastAPI()
    app.include_router(router)
    service = MonitorCenterService(tmp_path / "monitor.json")
    app.state.monitor_center_service = service
    return TestClient(app), service


def test_summary_route_returns_dashboard_projection(tmp_path):
    client, service = _client(tmp_path)
    service.save_rule({"id": "r1", "name": "风险", "conditions": {"score": {"gte": 1}}})
    service.evaluate(
        {"symbol": "000001", "score": 2}, datetime.now(timezone.utc), topic="quant_strategy"
    )

    response = client.get("/api/v1/monitor-center/summary")

    assert response.status_code == 200
    assert response.json()["alerts"]["total"] == 1
    assert "quant_strategy" in {item["topic"] for item in response.json()["topics"]}


def test_confirm_route_returns_chinese_not_found(tmp_path):
    client, _ = _client(tmp_path)

    response = client.post(
        "/api/v1/monitor-center/alerts/missing/confirm", json={"confirmed_by": "用户"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "告警不存在"


def test_retry_route_requeues_failed_delivery(tmp_path):
    client, service = _client(tmp_path)
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))
    service.complete_delivery(alert["alert_id"], "feishu", "failed", "网络不可用")

    response = client.post(
        f"/api/v1/monitor-center/alerts/{alert['alert_id']}/delivery/retry",
        json={"channel": "feishu"},
    )

    assert response.status_code == 200
    assert response.json()["delivery"]["feishu"] == "pending"


def test_retry_route_rejects_unknown_channel(tmp_path):
    client, service = _client(tmp_path)
    service.save_rule({"id": "r1", "name": "提醒", "conditions": {"score": {"gte": 1}}})
    alert = service.evaluate({"symbol": "000001", "score": 2}, datetime.now(timezone.utc))

    response = client.post(
        f"/api/v1/monitor-center/alerts/{alert['alert_id']}/delivery/retry",
        json={"channel": "email"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "不支持的告警投递通道"
