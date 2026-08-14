from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from qibao_api.contracts.briefing import BriefingPhase
from qibao_api.contracts.source_health import SourceHealthResponse
from qibao_api.contracts.task_progress import TaskProgress
from qibao_api.dependencies import (
    get_backup_service,
    get_operations_read_model,
    get_operations_repository,
    get_tdx_auto_import_monitor,
    get_scheduler,
    get_task_progress_registry,
    get_performance_store,
)
from qibao_api.gongbu.backup_service import BackupRecord, BackupVerification
from qibao_api.operations.freshness import DEFAULT_FRESHNESS_POLICIES


router = APIRouter(prefix="/api/v1/operations", tags=["工部运维"])


@router.get("/tasks/{task_id}", response_model=TaskProgress)
def task_progress(
    task_id: str,
    registry: Annotated[object, Depends(get_task_progress_registry)],
) -> TaskProgress:
    task = registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="后台任务不存在或已过期")
    return task


@router.get("/status")
def operations_status(
    scheduler: Annotated[object, Depends(get_scheduler)],
    backups: Annotated[object, Depends(get_backup_service)],
    read_model: Annotated[object, Depends(get_operations_read_model)],
    tdx_auto_import: Annotated[object, Depends(get_tdx_auto_import_monitor)],
):
    return {
        "scheduler": scheduler.status(),
        "backups": backups.backups(),
        "inventory": read_model.snapshot(),
        "tdx_auto_import": tdx_auto_import.status(),
    }


@router.get("/diagnostics")
def diagnostics_summary(
    request: Request,
    scheduler: Annotated[object, Depends(get_scheduler)],
    backups: Annotated[object, Depends(get_backup_service)],
    read_model: Annotated[object, Depends(get_operations_read_model)],
    repository: Annotated[object, Depends(get_operations_repository)],
    tdx_auto_import: Annotated[object, Depends(get_tdx_auto_import_monitor)],
):
    inventory = read_model.snapshot()
    health_items = repository.source_health_snapshot() if hasattr(repository, "source_health_snapshot") else {"sources": repository.source_health(20)}
    sources = health_items.get("sources", [])
    audit_repository = getattr(request.app.state, "audit_repository", None)
    source_conflicts = (
        audit_repository.source_conflict_summary(asset="a_share")
        if audit_repository is not None and hasattr(audit_repository, "source_conflict_summary")
        else {"state": "unavailable", "conflict_count": 0, "conflicts": []}
    )
    return {
        "generated_at": datetime.now(timezone.utc),
        "scheduler_paused": bool(scheduler.status().get("paused", False)),
        "backup_count": len(backups.backups()),
        "persistent_bytes": inventory.get("release", {}).get("persistent_bytes", 0),
        "rebuildable_bytes": inventory.get("release", {}).get("rebuildable_bytes", 0),
        "source_health": {
            "ready": sum(item.get("status") == "ready" for item in sources),
            "degraded": sum(item.get("status") == "degraded" for item in sources),
            "unavailable": sum(item.get("status") == "unavailable" for item in sources),
        },
        "tdx_auto_import": tdx_auto_import.status(),
        "source_conflicts": source_conflicts,
    }


@router.get("/source-conflicts")
def source_conflicts(
    request: Request,
    symbol: str | None = Query(default=None, min_length=6, max_length=6),
    field: str | None = Query(default=None, min_length=1, max_length=128),
):
    repository = getattr(request.app.state, "audit_repository", None)
    if repository is None or not hasattr(repository, "source_conflict_summary"):
        raise HTTPException(status_code=503, detail="source_conflict_store_unavailable")
    return repository.source_conflict_summary(asset="a_share", symbol=symbol, field=field)


@router.post("/cache/cleanup")
def cleanup_cache(
    read_model: Annotated[object, Depends(get_operations_read_model)],
    older_than_hours: Annotated[int, Query(ge=0, le=8760)] = 72,
):
    try:
        return read_model.cleanup_cache(older_than_hours=older_than_hours)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="缓存保留时间无效") from error


@router.get("/storage/cleanup-preview")
def cleanup_preview(
    read_model: Annotated[object, Depends(get_operations_read_model)],
    older_than_hours: Annotated[int, Query(ge=0, le=8760)] = 72,
):
    return read_model.cleanup_preview(older_than_hours=older_than_hours)


@router.post("/storage/cleanup")
def cleanup_rebuildable(
    read_model: Annotated[object, Depends(get_operations_read_model)],
    older_than_hours: Annotated[int, Query(ge=0, le=8760)] = 72,
    confirm: Annotated[bool, Query()] = False,
):
    if not confirm:
        raise HTTPException(status_code=409, detail="请先预览并确认清理范围")
    return read_model.cleanup_rebuildable(older_than_hours=older_than_hours)


@router.get("/performance")
def performance_summary(
    store: Annotated[object, Depends(get_performance_store)],
):
    return {
        "generated_at": datetime.now(timezone.utc),
        "metrics": store.summary(),
        "snapshots": store.snapshot_summary(),
    }


@router.get("/freshness-policies")
def freshness_policies():
    return {
        "generated_at": datetime.now(timezone.utc),
        "policies": {
            name: {
                "live_seconds": policy.live_seconds,
                "fresh_seconds": policy.fresh_seconds,
                "stale_seconds": policy.stale_seconds,
            }
            for name, policy in DEFAULT_FRESHNESS_POLICIES.items()
        },
    }


@router.get("/source-health", response_model=SourceHealthResponse)
def source_health(
    repository: Annotated[object, Depends(get_operations_repository)],
) -> SourceHealthResponse:
    snapshot = (
        repository.source_health_snapshot()
        if hasattr(repository, "source_health_snapshot") else None
    )
    if snapshot is not None:
        return SourceHealthResponse.model_validate(snapshot)
    window_size = 20
    return SourceHealthResponse(
        generated_at=datetime.now(timezone.utc),
        window_size=window_size,
        sources=tuple(repository.source_health(window_size)),
    )


@router.post("/scheduler/{action}")
def scheduler_action(
    action: str,
    scheduler: Annotated[object, Depends(get_scheduler)],
):
    if action not in {"pause", "resume"}:
        raise HTTPException(status_code=404, detail="未知调度操作")
    scheduler.set_paused(action == "pause", datetime.now(timezone.utc))
    return scheduler.status()


@router.post("/jobs/{phase}/{trading_date}/run")
def run_manual_job(
    phase: BriefingPhase,
    trading_date: date,
    scheduler: Annotated[object, Depends(get_scheduler)],
):
    report = scheduler.run_manual(
        phase, trading_date, datetime.now(timezone.utc)
    )
    if report is None:
        raise HTTPException(status_code=503, detail="手动补跑失败，已记录运行日志")
    return {"report_id": report.report_id}


@router.get("/backups", response_model=list[BackupRecord])
def list_backups(backups: Annotated[object, Depends(get_backup_service)]):
    return backups.backups()


@router.post("/backups", response_model=BackupRecord)
def create_backup(backups: Annotated[object, Depends(get_backup_service)]):
    try:
        return backups.create()
    except (RuntimeError, OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail="一致性备份创建失败，详细原因已写入本地运行日志") from error


@router.post("/backups/{backup_id}/verify", response_model=BackupVerification)
def verify_backup(
    backup_id: str,
    backups: Annotated[object, Depends(get_backup_service)],
    restore_drill: Annotated[bool, Query()] = True,
):
    try:
        return backups.verify(backup_id, restore_drill=restore_drill)
    except (ValueError, FileNotFoundError, OSError) as error:
        raise HTTPException(status_code=404, detail="备份不存在或标识无效") from error
