from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import httpx

from qibao_api.notifications.settings import NotificationSettings


class FeishuDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FeishuDeliveryResult:
    status: str
    message: str


class FeishuWebhookDelivery:
    def __init__(
        self,
        settings_provider: Callable[[], NotificationSettings],
        *,
        client: httpx.Client | None = None,
        timeout: float = 8,
    ) -> None:
        self.settings_provider = settings_provider
        self.client = client or httpx.Client(timeout=timeout)

    def send(self, *, title: str, lines: Iterable[str]) -> FeishuDeliveryResult:
        settings = self.settings_provider()
        if not settings.feishu_enabled or not settings.feishu_webhook:
            return FeishuDeliveryResult(status="未配置", message="飞书机器人未启用")
        content = "\n".join(str(line).strip() for line in lines if str(line).strip())
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [
                    {"tag": "markdown", "content": content or "无可展示内容"}
                ],
            },
        }
        try:
            response = self.client.post(settings.feishu_webhook, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as error:
            raise FeishuDeliveryError("飞书连接超时") from error
        except httpx.HTTPError as error:
            raise FeishuDeliveryError("飞书 HTTP 请求失败") from error
        except (TypeError, ValueError) as error:
            raise FeishuDeliveryError("飞书响应格式无效") from error
        code = body.get("code", body.get("StatusCode")) if isinstance(body, dict) else None
        if code not in (0, "0"):
            raise FeishuDeliveryError("飞书返回业务错误")
        return FeishuDeliveryResult(status="sent", message="飞书消息已送达")
