from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from qibao_api.a_shares.monitor_center import MonitorCenterService
from qibao_api.notifications.settings import (
    NotificationSettings,
    NotificationSettingsRepository,
)

router = APIRouter(prefix="/api/v1/monitor-center", tags=["监控中心"])


def _service(request: Request) -> MonitorCenterService:
    existing = getattr(request.app.state, "monitor_center_service", None)
    if existing is not None:
        return existing
    path = Path(getattr(request.app.state, "data_dir", "data")) / "monitor-center.json"
    return MonitorCenterService(path)


def _notification_repository(request: Request) -> NotificationSettingsRepository:
    repository = getattr(request.app.state, "notification_settings_repository", None)
    if repository is not None:
        return repository
    return NotificationSettingsRepository(
        Path(getattr(request.app.state, "data_dir", "data"))
    )


@router.get("/rules")
def rules(request: Request) -> list[dict[str, Any]]:
    return _service(request).rule_views()


@router.post("/rules")
def save_rule(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    try:
        return _service(request).save_rule(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/rules/{rule_id}/status")
def update_rule_status(rule_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=422, detail="规则启用状态必须是布尔值")
    try:
        return _service(request).set_rule_enabled(rule_id, enabled)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="监控规则不存在") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, request: Request) -> dict[str, str]:
    try:
        return _service(request).delete_rule(rule_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="监控规则不存在") from error


@router.get("/alerts")
def alerts(request: Request, limit: int = 50) -> list[dict[str, Any]]:
    return _service(request).history(limit)


@router.get("/summary")
def summary(request: Request) -> dict[str, Any]:
    return _service(request).summary()


@router.get("/alerts/pending-tts")
def pending_tts(request: Request, limit: int = 10) -> list[dict[str, Any]]:
    return _service(request).pending_tts(limit)


@router.post("/alerts/{alert_id}/delivery")
def complete_delivery(alert_id: str, payload: dict[str, Any], request: Request) -> dict[str, str]:
    try:
        return _service(request).complete_delivery(
            alert_id, str(payload.get("channel", "")), str(payload.get("status", "")), payload.get("reason")
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="告警不存在") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/alerts/{alert_id}/confirm")
def confirm_alert(alert_id: str, payload: dict[str, Any] | None, request: Request) -> dict[str, Any]:
    try:
        confirmed_by = str((payload or {}).get("confirmed_by", "用户"))
        return _service(request).confirm(alert_id, confirmed_by=confirmed_by)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="告警不存在") from error


@router.post("/alerts/{alert_id}/delivery/retry")
def retry_delivery(alert_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    try:
        return _service(request).retry_delivery(alert_id, str(payload.get("channel", "")))
    except KeyError as error:
        raise HTTPException(status_code=404, detail="告警不存在") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/notification-settings/test")
def test_notification_settings(request: Request) -> dict[str, str]:
    delivery = getattr(request.app.state, "feishu_delivery", None)
    if delivery is None:
        return {"status": "未配置", "message": "飞书投递器尚未初始化"}
    try:
        result = delivery.send(title="易数-A股观测台测试", lines=("这是一条本机配置测试消息，不代表交易信号。",))
        return {"status": result.status, "message": result.message}
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/notification-settings")
def notification_settings(request: Request) -> dict[str, object]:
    return _notification_repository(request).view()


@router.put("/notification-settings")
def save_notification_settings(
    payload: dict[str, Any], request: Request
) -> dict[str, object]:
    if set(payload) != {"feishu_enabled", "feishu_webhook"}:
        raise HTTPException(status_code=422, detail="通知设置字段不完整")
    try:
        repository = _notification_repository(request)
        webhook = payload["feishu_webhook"]
        if webhook is None and repository.view()["feishu_configured"]:
            webhook = repository.load().feishu_webhook
        settings = NotificationSettings(
            feishu_enabled=payload["feishu_enabled"],
            feishu_webhook=webhook,
        )
        repository.save(settings)
        return repository.view()
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/notification-settings")
def delete_notification_settings(request: Request) -> dict[str, object]:
    repository = _notification_repository(request)
    repository.delete()
    return repository.view()


@router.post("/test")
def test_alert(payload: dict[str, Any], request: Request) -> dict[str, Any] | None:
    observed_at = datetime.fromisoformat(payload.pop("observed_at")) if payload.get("observed_at") else datetime.now().astimezone()
    return _service(request).evaluate(payload, observed_at)
