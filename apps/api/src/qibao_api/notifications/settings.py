from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from qibao_api.credential_protection import (
    CredentialProtector,
    default_credential_protector,
)


_FEISHU_HOSTS = frozenset({"open.feishu.cn", "open.larksuite.com"})
_FEISHU_HOOK_PREFIX = "/open-apis/bot/v2/hook/"


@dataclass(frozen=True, slots=True)
class NotificationSettings:
    feishu_enabled: bool = False
    feishu_webhook: str | None = None

    def __post_init__(self) -> None:
        webhook = self.feishu_webhook.strip() if self.feishu_webhook else None
        object.__setattr__(self, "feishu_webhook", webhook)
        if self.feishu_enabled and not webhook:
            raise ValueError("启用飞书前必须填写飞书 Webhook")
        if webhook:
            parsed = urlsplit(webhook)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in _FEISHU_HOSTS
                or not parsed.path.startswith(_FEISHU_HOOK_PREFIX)
                or len(parsed.path) <= len(_FEISHU_HOOK_PREFIX)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("飞书 Webhook 地址无效")


class NotificationSettingsRepository:
    def __init__(
        self,
        data_dir: Path,
        *,
        protector: CredentialProtector | None = default_credential_protector(),
    ) -> None:
        self.path = Path(data_dir) / "notification-settings.json"
        self.protector = protector
        self._lock = threading.RLock()

    def load(self) -> NotificationSettings:
        with self._lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                protected = raw.get("feishu_webhook_protected")
                webhook = None
                if protected:
                    if self.protector is None:
                        raise ValueError("protected credential is unavailable")
                    webhook = self.protector.unprotect(protected)
                elif raw.get("feishu_webhook"):
                    webhook = raw["feishu_webhook"]
                settings = NotificationSettings(
                    feishu_enabled=bool(raw.get("feishu_enabled", False)),
                    feishu_webhook=webhook,
                )
                if raw.get("feishu_webhook") and self.protector is not None:
                    self.save(settings)
                return settings
            except (FileNotFoundError, KeyError, TypeError, ValueError, OSError):
                return NotificationSettings()

    def save(self, settings: NotificationSettings) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, object] = {"feishu_enabled": settings.feishu_enabled}
            if settings.feishu_webhook:
                if self.protector is None:
                    raise RuntimeError("本机凭据保护不可用，拒绝明文保存飞书 Webhook")
                else:
                    payload["feishu_webhook_protected"] = self.protector.protect(
                        settings.feishu_webhook
                    )
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary_path, self.path)
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                temporary_path.unlink(missing_ok=True)
                raise

    def delete(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)

    def view(self) -> dict[str, object]:
        settings = self.load()
        webhook = settings.feishu_webhook
        hint = None
        if webhook:
            parsed = urlsplit(webhook)
            token = parsed.path.removeprefix(_FEISHU_HOOK_PREFIX)
            hint = f"{parsed.hostname} / ****{token[-4:]}"
        return {
            "feishu_configured": bool(webhook),
            "feishu_enabled": settings.feishu_enabled,
            "webhook_hint": hint,
        }
