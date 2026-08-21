import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.notifications.feishu import FeishuWebhookDelivery
from qibao_api.notifications.settings import NotificationSettingsRepository
from qibao_api.routes.monitor_center import router


class Protector:
    def protect(self, value: str) -> str:
        return f"protected:{value[::-1]}"

    def unprotect(self, value: str) -> str:
        return value.removeprefix("protected:")[::-1]


def client_with_notifications(tmp_path, *, transport=None) -> TestClient:
    application = FastAPI()
    application.state.data_dir = tmp_path
    repository = NotificationSettingsRepository(tmp_path, protector=Protector())
    application.state.notification_settings_repository = repository
    application.state.feishu_delivery = FeishuWebhookDelivery(
        repository.load,
        client=httpx.Client(transport=transport) if transport is not None else None,
    )
    application.include_router(router)
    return TestClient(application)


def test_notification_settings_routes_never_return_raw_webhook(tmp_path) -> None:
    client = client_with_notifications(tmp_path)

    saved = client.put(
        "/api/v1/monitor-center/notification-settings",
        json={
            "feishu_enabled": True,
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        },
    )

    assert saved.status_code == 200
    assert saved.json()["feishu_configured"] is True
    assert "example-secret" not in saved.text
    assert "example-secret" not in client.get(
        "/api/v1/monitor-center/notification-settings"
    ).text


def test_notification_test_reports_unconfigured_without_network(tmp_path) -> None:
    client = client_with_notifications(tmp_path)

    response = client.post("/api/v1/monitor-center/notification-settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "status": "未配置",
        "message": "飞书机器人未启用",
    }


def test_notification_test_sends_configured_webhook(tmp_path) -> None:
    client = client_with_notifications(
        tmp_path,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"code": 0, "msg": "success"})
        ),
    )
    saved = client.put(
        "/api/v1/monitor-center/notification-settings",
        json={
            "feishu_enabled": True,
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        },
    )
    assert saved.status_code == 200

    response = client.post("/api/v1/monitor-center/notification-settings/test")

    assert response.status_code == 200
    assert response.json()["status"] == "sent"


def test_notification_test_returns_sanitized_chinese_failure(tmp_path) -> None:
    client = client_with_notifications(
        tmp_path,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"code": 19002, "msg": "invalid"})
        ),
    )
    client.put(
        "/api/v1/monitor-center/notification-settings",
        json={
            "feishu_enabled": True,
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        },
    )

    response = client.post("/api/v1/monitor-center/notification-settings/test")

    assert response.status_code == 503
    assert response.json()["detail"] == "飞书返回业务错误"
    assert "example-secret" not in response.text


def test_notification_settings_can_toggle_existing_webhook_without_reentering_secret(tmp_path) -> None:
    client = client_with_notifications(tmp_path)
    client.put(
        "/api/v1/monitor-center/notification-settings",
        json={"feishu_enabled": True, "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/example-secret"},
    )

    disabled = client.put(
        "/api/v1/monitor-center/notification-settings",
        json={"feishu_enabled": False, "feishu_webhook": None},
    )

    assert disabled.status_code == 200
    assert disabled.json()["feishu_configured"] is True
    assert disabled.json()["feishu_enabled"] is False
    assert "example-secret" not in disabled.text
