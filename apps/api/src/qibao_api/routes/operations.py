import asyncio
import queue
from datetime import date, datetime, timezone
import hashlib
import json
from concurrent.futures import Executor
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from qibao_api.contracts.briefing import BriefingPhase
from qibao_api.contracts.data_lineage import DataLineageResponse
from qibao_api.contracts.data_gap_repair import DataGapRepairRequest, DataGapRepairResponse
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
    get_data_lineage_repository,
    get_full_market_history_service,
    get_history_sync_executor,
    get_server_time,
    get_operations_read_model,
    get_operations_repository,
    get_tdx_auto_import_monitor,
    get_scheduler,
    get_task_progress_registry,
    get_performance_store,
    get_precompute_snapshot_store,
    get_observability_store,
    get_replay_snapshot_store,
    get_shared_snapshot_registry,
    get_realtime_snapshot_bus,
)
from qibao_api.gongbu.backup_service import BackupRecord, BackupVerification
from qibao_api.operations.freshness import DEFAULT_FRESHNESS_POLICIES


router = APIRouter(prefix="/api/v1/operations", tags=["工部运维"])


@router.get("/realtime-stream")
async def realtime_stream(
    request: Request,
    bus: Annotated[object | None, Depends(get_realtime_snapshot_bus)],
    topics: str | None = Query(default=None, max_length=512),
):
    """Fan out verified domain snapshots to pages that opt into live updates."""
    if bus is None or not hasattr(bus, "subscribe"):
        raise HTTPException(
            status_code=503,
            detail={"code": "realtime_stream_unavailable", "message": "实时推送总线尚未就绪"},
        )
    requested = frozenset(
        item.strip() for item in (topics or "").split(",") if item.strip()
    )
    if not requested:
        raise HTTPException(
            status_code=422,
            detail={"code": "realtime_topics_required", "message": "至少指定一个实时主题"},
        )
    subscription = bus.subscribe(requested)
    initial = [bus.latest(kind) for kind in requested]
    initial = [event for event in initial if event is not None]

    async def events():
        try:
            for event in sorted(initial, key=lambda item: item.get("sequence", 0)):
                yield bus.sse_frame(event)
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(subscription.get, True, 15)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield bus.sse_frame(event)
        finally:
            bus.unsubscribe(subscription)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/data-gaps/repair", response_model=DataGapRepairResponse, status_code=202)
def repair_data_gaps(
    request: DataGapRepairRequest,
    service: Annotated[object, Depends(get_full_market_history_service)],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> DataGapRepairResponse:
    current = service.current_job()
    if current is not None and current.state in {"pending", "running", "paused"}:
        raise HTTPException(status_code=409, detail="已有全市场日线同步任务")
    today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    if request.target_date > today:
        raise HTTPException(status_code=422, detail="不能修复未来交易日缺口")
    symbols = tuple(dict.fromkeys(item.symbol for item in request.gaps))
    job = service.jobs.create_job("incremental", request.target_date, symbols)
    executor.submit(service.run, job.job_id)
    canonical = json.dumps(
        request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    job_state = getattr(job, "state", "pending")
    return DataGapRepairResponse(
        job_id=job.job_id,
        state=job_state,
        target_date=request.target_date,
        source=request.source,
        symbols=symbols,
        gap_count=len(request.gaps),
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        written_rows=0,
        submitted_at=now.astimezone(timezone.utc),
    )


@router.get("/data-lineage", response_model=DataLineageResponse)
def data_lineage(
    repository: Annotated[object, Depends(get_data_lineage_repository)],
    domain: str | None = Query(default=None, min_length=1, max_length=128),
    field: str | None = Query(default=None, min_length=1, max_length=128),
    symbol: str | None = Query(default=None, min_length=1, max_length=32),
    trade_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> DataLineageResponse:
    records = repository.list(
        domain=domain,
        field=field,
        symbol=symbol,
        trade_date=trade_date,
        limit=limit,
    )
    return DataLineageResponse(
        generated_at=datetime.now(timezone.utc),
        count=len(records),
        records=tuple(records),
    )


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
    realtime_ai = getattr(request.app.state, "realtime_ai_trigger_queue", None)
    realtime_bus = getattr(request.app.state, "realtime_snapshot_bus", None)
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
        "realtime_ai": realtime_ai.status() if realtime_ai is not None and hasattr(realtime_ai, "status") else {"state": "unavailable"},
        "realtime_bus": realtime_bus.status() if realtime_bus is not None and hasattr(realtime_bus, "status") else {"state": "unavailable"},
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


@router.get("/precompute-snapshots")
def precompute_snapshot_inventory(
    store: Annotated[object, Depends(get_precompute_snapshot_store)],
):
    return {
        "generated_at": datetime.now(timezone.utc),
        "snapshots": store.summary(),
    }


@router.get("/precompute-snapshots/{domain}")
def precompute_snapshot(
    domain: str,
    store: Annotated[object, Depends(get_precompute_snapshot_store)],
    trade_date: date | None = None,
    data_version: str | None = Query(default=None, min_length=1, max_length=128),
):
    try:
        snapshot = store.latest_complete(
            domain, trade_date=trade_date, data_version=data_version
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail="未知的预计算域") from error
    if snapshot is None:
        raise HTTPException(status_code=404, detail="尚无可用的完整预计算快照")
    return snapshot.to_dict()


@router.get("/observability")
def observability_summary(
    request: Request,
    store: Annotated[object, Depends(get_observability_store)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    snapshot = store.snapshot(limit)
    alerts = list(snapshot.get("alerts", []))
    bus = getattr(request.app.state, "realtime_snapshot_bus", None)
    if bus is not None and hasattr(bus, "status"):
        metrics = bus.status()
        if metrics.get("dropped_intermediate", 0) > 0:
            alerts.append({"severity": "medium", "code": "realtime_bus_dropped", "event_type": "realtime_bus", "detail": f"实时总线已丢弃 {metrics['dropped_intermediate']} 个旧中间帧，最新快照仍保留"})
    ai_queue = getattr(request.app.state, "realtime_ai_trigger_queue", None)
    if ai_queue is not None and hasattr(ai_queue, "status"):
        metrics = ai_queue.status()
        if metrics.get("pending", 0) >= 10:
            alerts.append({"severity": "high", "code": "realtime_ai_backlog", "event_type": "realtime_ai", "detail": f"实时 AI 队列积压 {metrics['pending']} 个任务"})
    snapshot["alerts"] = alerts[:50]
    return snapshot


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
    bus: Annotated[object | None, Depends(get_realtime_snapshot_bus)],
) -> ReplaySnapshot:
    now = datetime.now(timezone.utc)
    selected_date = request.trading_date or now.astimezone().date()
    if selected_date > now.astimezone().date():
        raise HTTPException(status_code=422, detail="不能为未来日期生成重放快照")
    summary = registry.summary() if registry is not None else []
    input_items = [
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
    ]
    ai_event = bus.latest("ai_analysis") if bus is not None and hasattr(bus, "latest") else None
    ai_payload = ai_event.get("payload") if ai_event is not None else None
    if isinstance(ai_payload, dict) and ai_payload.get("input_snapshot_hash"):
        input_items.append(ReplayInputReference(
            domain="ai_analysis",
            reference=f"ai-trigger:{ai_payload.get('trigger_id', ai_event.get('event_id', 'unknown'))}",
            content_hash=ai_payload["input_snapshot_hash"],
            source=str(ai_payload.get("source") or "unavailable"),
            observed_at=ai_event.get("observed_at"),
            status="ready" if ai_payload.get("status") == "ready" else "unavailable",
        ))
    inputs = tuple(input_items)
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
