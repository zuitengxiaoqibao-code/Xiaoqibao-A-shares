import json
from pathlib import Path

import httpx
import pytest

from qibao_api.notifications.feishu import FeishuDeliveryError, FeishuWebhookDelivery
from qibao_api.notifications.settings import (
    NotificationSettings,
    NotificationSettingsRepository,
)


class Protector:
    def protect(self, value: str) -> str:
        return f"protected:{value[::-1]}"

    def unprotect(self, value: str) -> str:
        return value.removeprefix("protected:")[::-1]


def test_repository_protects_webhook_and_returns_masked_view(tmp_path: Path) -> None:
    repository = NotificationSettingsRepository(tmp_path, protector=Protector())
    settings = NotificationSettings(
        feishu_enabled=True,
        feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
    )

    repository.save(settings)

    raw = repository.path.read_text(encoding="utf-8")
    assert "example-secret" not in raw
    assert repository.load() == settings
    assert repository.view() == {
        "feishu_configured": True,
        "feishu_enabled": True,
        "webhook_hint": "open.feishu.cn / ****cret",
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://open.feishu.cn/open-apis/bot/v2/hook/token",
        "https://example.com/open-apis/bot/v2/hook/token",
        "https://open.feishu.cn/not-a-hook/token",
    ],
)
def test_settings_reject_non_feishu_webhook(url: str) -> None:
    with pytest.raises(ValueError, match="飞书 Webhook"):
        NotificationSettings(feishu_enabled=True, feishu_webhook=url)


def test_delivery_sends_text_card_and_validates_business_code() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 0, "msg": "success"})

    delivery = FeishuWebhookDelivery(
        lambda: NotificationSettings(
            feishu_enabled=True,
            feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = delivery.send(title="监控告警", lines=("贵州茅台 600519", "涨幅触发 5%"))

    assert result.status == "sent"
    payload = json.loads(requests[0].content)
    assert payload["msg_type"] == "interactive"
    assert payload["card"]["header"]["title"]["content"] == "监控告警"
    assert "example-secret" not in json.dumps(payload, ensure_ascii=False)


def test_delivery_classifies_business_failure_without_leaking_webhook() -> None:
    delivery = FeishuWebhookDelivery(
        lambda: NotificationSettings(
            feishu_enabled=True,
            feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        ),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"code": 19002, "msg": "invalid"})
            )
        ),
    )

    with pytest.raises(FeishuDeliveryError, match="飞书返回业务错误") as raised:
        delivery.send(title="测试", lines=("测试",))

    assert "example-secret" not in str(raised.value)


def test_repository_refuses_plaintext_webhook_when_credential_protection_is_unavailable(tmp_path: Path) -> None:
    repository = NotificationSettingsRepository(tmp_path, protector=None)

    with pytest.raises(RuntimeError, match="本机凭据保护不可用"):
        repository.save(NotificationSettings(
            feishu_enabled=True,
            feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/example-secret",
        ))

    assert not repository.path.exists()
