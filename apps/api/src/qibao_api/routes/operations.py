from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from qibao_api.contracts.briefing import BriefingPhase
from qibao_api.contracts.data_quality_matrix import DataQualityItem, DataQualityMatrix
from qibao_api.contracts.source_health import SourceHealthResponse
from qibao_api.contracts.task_progress import TaskProgress
from qibao_api.contracts.replay_snapshot import (
    ReplayCaptureRequest,
    ReplayInputReference,
    ReplaySnapshot,
    ReplaySnapshotList,
)
from qibao_api.dependencies import (
    get_backup_service,
    get_operations_read_model,
    get_operations_repository,
    get_tdx_auto_import_monitor,
    get_scheduler,
    get_task_progress_registry,
    get_performance_store,
    get_observability_store,
    get_replay_snapshot_store,
    get_shared_snapshot_registry,
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
    generated_at = datetime.now(timezone.utc)
    quality_items = []
    for item in sources:
        status = item.get("status", "unavailable")
        observed_at = item.get("last_success_at") or item.get("last_failure_at")
        attempts = int(item.get("attempts") or 0)
        successes = int(item.get("successes") or 0)
        error_code = item.get("last_error_code")
        limitations = () if status == "ready" else (
            f"最近探针状态：{error_code or status}",
        )
        quality_items.append(DataQualityItem(
            domain=f"source_probe:{item.get('operation', 'unknown')}",
            status="partial" if status == "degraded" else status,
            source=str(item.get("source") or "unknown"),
            trade_date=item.get("latest_trade_date"),
            observed_at=observed_at,
            valid_count=successes,
            total_count=attempts,
            coverage_percent=round(successes / attempts * 100, 2) if attempts else 0,
            cache_state="not_applicable",
            limitations=limitations,
        ))
    quality_matrix = DataQualityMatrix(
        generated_at=generated_at,
        items=tuple(quality_items),
    )
    return {
        "generated_at": generated_at,
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
        "quality_matrix": quality_matrix.model_dump(mode="json"),
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


@router.get("/observability")
def observability_summary(
    store: Annotated[object, Depends(get_observability_store)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return store.snapshot(limit)


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


@router.get("/replay-snapshots", response_model=ReplaySnapshotList)
def replay_snapshots(
    store: Annotated[object, Depends(get_replay_snapshot_store)],
    trading_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ReplaySnapshotList:
    return ReplaySnapshotList(
        generated_at=datetime.now(timezone.utc),
        trading_date=trading_date,
        snapshots=store.list(trading_date=trading_date, limit=limit),
    )


@router.post("/replay-snapshots/capture", response_model=ReplaySnapshot)
def capture_replay_snapshot(
    request: ReplayCaptureRequest,
    store: Annotated[object, Depends(get_replay_snapshot_store)],
    registry: Annotated[object, Depends(get_shared_snapshot_registry)],
    repository: Annotated[object, Depends(get_operations_repository)],
) -> ReplaySnapshot:
    now = datetime.now(timezone.utc)
    selected_date = request.trading_date or now.astimezone().date()
    if selected_date > now.astimezone().date():
        raise HTTPException(status_code=422, detail="不能为未来日期生成重放快照")
    summary = registry.summary() if registry is not None else []
    inputs = tuple(
        ReplayInputReference(
            domain=item["kind"],
            reference=f"shared-snapshot:{item['kind']}:{item['snapshot_version']}",
            content_hash=item.get("content_hash"),
            source=item.get("source") or "unavailable",
            observed_at=item.get("observed_at"),
            status=(
                "unavailable" if item.get("snapshot_version", 0) == 0
                else "stale" if item.get("freshness") == "stale"
                else "ready"
            ),
        )
        for item in summary
    )
    source_health = repository.source_health_snapshot() or {
        "sources": repository.source_health(20),
    }
    return store.append(
        trading_date=selected_date,
        captured_at=now,
        inputs=inputs,
        source_health=source_health,
        strategy_version=request.strategy_version,
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
