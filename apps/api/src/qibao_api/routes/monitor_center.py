from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from qibao_api.a_shares.monitor_center import MonitorCenterService

router = APIRouter(prefix="/api/v1/monitor-center", tags=["监控中心"])


def _service(request: Request) -> MonitorCenterService:
    path = Path(getattr(request.app.state, "data_dir", "data")) / "monitor-center.json"
    return MonitorCenterService(path)


@router.get("/rules")
def rules(request: Request) -> list[dict[str, Any]]:
    return _service(request)._state["rules"]


@router.post("/rules")
def save_rule(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    try:
        return _service(request).save_rule(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/alerts")
def alerts(request: Request, limit: int = 50) -> list[dict[str, Any]]:
    return _service(request).history(limit)


@router.post("/test")
def test_alert(payload: dict[str, Any], request: Request) -> dict[str, Any] | None:
    observed_at = datetime.fromisoformat(payload.pop("observed_at")) if payload.get("observed_at") else datetime.now().astimezone()
    return _service(request).evaluate(payload, observed_at)
