from concurrent.futures import Executor
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path as RoutePath, Query, status
from pydantic import BaseModel

from qibao_api.contracts.bars import DailyBar, SyncReport
from qibao_api.contracts.history_sync import (
    HistoryCoverageSummary,
    HistoryRepairCenter,
    HistorySyncJob,
    HistoryRepairAudit,
)
from qibao_api.contracts.history_supplement import HistorySupplementJob, OfficialTdxPackageInfo
from qibao_api.contracts.tdx_import import TdxImportJob, TdxImportScan
from qibao_api.contracts.instruments import AShareCode
from qibao_api.dependencies import (
    get_full_market_history_service,
    get_history_sync_executor,
    get_history_supplement_executor,
    get_history_supplement_service,
    get_market_data_service,
    get_tdx_import_executor,
    get_tdx_import_service,
    get_server_time,
)
from qibao_api.gongbu.data_service import MarketDataService
from qibao_api.gongbu.full_market_history import FullMarketHistoryService
from qibao_api.gongbu.tdx_local_import import TdxLocalImportService

router = APIRouter(prefix="/api/v1/a-shares", tags=["工部数据"])


class TdxImportPaths(BaseModel):
    paths: tuple[str, ...] = ()


@router.get(
    "/history-supplement/official-info",
    response_model=OfficialTdxPackageInfo,
)
def official_history_package_info(
    service: Annotated[object, Depends(get_history_supplement_service)],
) -> OfficialTdxPackageInfo:
    try:
        return service.package_info()
    except Exception as error:
        if isinstance(error, UnicodeDecodeError):
            detail = "本地行情数据库暂时不可读取，可能正在被其他任务占用，请等待当前任务完成后重试"
        else:
            message = str(error).strip()
            detail = (
                f"通达信官方日线包信息读取失败：{message}"
                if any("\u4e00" <= char <= "\u9fff" for char in message)
                else "通达信官方日线包信息暂时不可用，请稍后重试"
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        ) from error


@router.get(
    "/history-supplement/current",
    response_model=HistorySupplementJob | None,
)
def current_history_supplement(
    service: Annotated[object, Depends(get_history_supplement_service)],
) -> HistorySupplementJob | None:
    return service.current_job()


@router.post(
    "/history-supplement/official/start",
    response_model=HistorySupplementJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_official_history_supplement(
    service: Annotated[object, Depends(get_history_supplement_service)],
    executor: Annotated[Executor, Depends(get_history_supplement_executor)],
) -> HistorySupplementJob:
    try:
        return service.start_job(executor)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503,
            detail="后台修复服务未能启动或正在关闭，请重新启动程序后重试；已有数据和缓存已保留。") from error


def _local_paths(service: TdxLocalImportService, paths: tuple[str, ...]) -> tuple[Path, ...]:
    if paths:
        return tuple(Path(item) for item in paths)
    discovery = getattr(service, "discovery", None)
    active = getattr(discovery, "active_tdx_vipdoc", None)
    candidates = []
    if active is not None:
        candidates.append(active)
        install_root = active.parent if active.name.casefold() == "vipdoc" else active
        archive_root = install_root / "T0002"
        if archive_root.is_dir():
            candidates.append(archive_root)
    configured = getattr(getattr(discovery, "settings", None), "tdx_archive_paths", ())
    if not configured:
        configured = getattr(service, "archive_paths", ())
    candidates.extend(configured)
    return tuple(candidates)


@router.post("/tdx-import/scan", response_model=TdxImportScan)
def scan_tdx_import(
    payload: TdxImportPaths,
    service: Annotated[TdxLocalImportService, Depends(get_tdx_import_service)],
) -> TdxImportScan:
    paths = _local_paths(service, payload.paths)
    if not paths:
        raise HTTPException(status_code=422, detail="未发现可扫描的通达信 vipdoc 目录")
    return service.scan(paths)


@router.post("/tdx-import/start", response_model=TdxImportJob, status_code=status.HTTP_202_ACCEPTED)
def start_tdx_import(
    payload: TdxImportPaths,
    service: Annotated[TdxLocalImportService, Depends(get_tdx_import_service)],
    executor: Annotated[Executor, Depends(get_tdx_import_executor)],
) -> TdxImportJob:
    current = service.current_job()
    if current is not None and current.state in {"pending", "running", "paused"}:
        raise HTTPException(status_code=409, detail="已有本地通达信导入任务")
    paths = _local_paths(service, payload.paths)
    if not paths:
        raise HTTPException(status_code=422, detail="未发现可导入的通达信 vipdoc 目录")
    job = service.create_job(paths)
    executor.submit(service.run, job.job_id)
    return job


@router.get("/tdx-import/current", response_model=TdxImportJob | None)
def current_tdx_import(
    service: Annotated[TdxLocalImportService, Depends(get_tdx_import_service)],
) -> TdxImportJob | None:
    return service.current_job()


@router.post("/tdx-import/{job_id}/pause", response_model=TdxImportJob)
def pause_tdx_import(
    job_id: Annotated[str, RoutePath(min_length=1)],
    service: Annotated[TdxLocalImportService, Depends(get_tdx_import_service)],
) -> TdxImportJob:
    try:
        return service.pause(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="未找到本地通达信导入任务") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/tdx-import/{job_id}/resume", response_model=TdxImportJob, status_code=status.HTTP_202_ACCEPTED)
def resume_tdx_import(
    job_id: Annotated[str, RoutePath(min_length=1)],
    service: Annotated[TdxLocalImportService, Depends(get_tdx_import_service)],
    executor: Annotated[Executor, Depends(get_tdx_import_executor)],
) -> TdxImportJob:
    try:
        job = service.resume(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="未找到本地通达信导入任务") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    executor.submit(service.run, job.job_id)
    return job


def _china_date(now: datetime) -> date:
    return now.astimezone(ZoneInfo("Asia/Shanghai")).date()


def _fallback_history_target(now: datetime) -> date:
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    target = local.date()
    if local.time() < time(15, 5):
        target -= timedelta(days=1)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target


def _default_history_target(service: FullMarketHistoryService, now: datetime) -> date:
    resolver = getattr(service, "default_target_date", None)
    if resolver is None:
        return _china_date(now)
    try:
        return resolver()
    except (UnicodeDecodeError, OSError, RuntimeError):
        return _fallback_history_target(now)


def _submit(
    service: FullMarketHistoryService,
    executor: Executor,
    job: HistorySyncJob,
) -> HistorySyncJob:
    try:
        executor.submit(service.run, job.job_id)
    except RuntimeError as error:
        # The same shutdown race affects incremental/retry entry points.
        # Pause instead of leaving a newly persisted task permanently active.
        service.pause(job.job_id)
        raise HTTPException(status_code=503,
            detail="日线同步后台服务正在关闭，任务已暂停且已有数据保留；请重新启动程序后继续。") from error
    return job


def _require_no_active_job(service: FullMarketHistoryService) -> None:
    current = service.current_job()
    if current is not None and current.state in ("pending", "running", "paused"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已有全市场日线同步任务，请先等待完成或暂停后恢复",
        )


@router.post(
    "/history-sync/backfill",
    response_model=HistorySyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_history_backfill(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
) -> HistorySyncJob:
    _require_no_active_job(service)
    return _submit(service, executor, service.create_backfill())


@router.post(
    "/history-sync/incremental",
    response_model=HistorySyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_history_incremental(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
    now: Annotated[datetime, Depends(get_server_time)],
    target_date: Annotated[date | None, Query()] = None,
) -> HistorySyncJob:
    _require_no_active_job(service)
    job = service.create_incremental(target_date or _default_history_target(service, now))
    return _submit(service, executor, job)


@router.post(
    "/history-sync/restart-current",
    response_model=HistorySyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def restart_current_history_sync(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
    now: Annotated[datetime, Depends(get_server_time)],
    target_date: Annotated[date | None, Query()] = None,
) -> HistorySyncJob:
    try:
        job = service.restart_current(target_date or _default_history_target(service, now))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前日线补齐任务仍在运行，请先暂停后再重新开始",
        ) from error
    return _submit(service, executor, job)


@router.get(
    "/history-sync/current",
    response_model=HistorySyncJob | None,
)
def current_history_sync(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
) -> HistorySyncJob | None:
    return service.current_job()


@router.get(
    "/history-sync/coverage",
    response_model=HistoryCoverageSummary,
)
def history_sync_coverage(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    now: Annotated[datetime, Depends(get_server_time)],
    target_date: Annotated[date | None, Query()] = None,
) -> HistoryCoverageSummary:
    return service.coverage(target_date or _default_history_target(service, now))


@router.get(
    "/history-sync/repair-center",
    response_model=HistoryRepairCenter,
)
def history_repair_center(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    now: Annotated[datetime, Depends(get_server_time)],
    target_date: Annotated[date | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> HistoryRepairCenter:
    return service.repair_center(
        target_date or _default_history_target(service, now), offset=offset, limit=limit,
    )


@router.get("/history-sync/quality")
def history_sync_quality(
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
):
    try:
        return service.quality_report(limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="历史质量检查参数无效") from error


@router.get("/history-sync/repair-audits", response_model=list[HistoryRepairAudit])
def history_repair_audits(
    service: Annotated[FullMarketHistoryService, Depends(get_full_market_history_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[HistoryRepairAudit]:
    return list(service.jobs.repair_audits(limit=limit))


@router.post(
    "/history-sync/{job_id}/pause",
    response_model=HistorySyncJob,
)
def pause_history_sync(
    job_id: Annotated[str, RoutePath(min_length=1)],
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
) -> HistorySyncJob:
    try:
        return service.pause(job_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到日线同步任务",
        ) from error


@router.post(
    "/history-sync/{job_id}/resume",
    response_model=HistorySyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def resume_history_sync(
    job_id: Annotated[str, RoutePath(min_length=1)],
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
) -> HistorySyncJob:
    try:
        job = service.resume(job_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到日线同步任务",
        ) from error
    if job.state != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="只有已暂停的日线同步任务可以继续",
        )
    return _submit(service, executor, job)


@router.post(
    "/history-sync/{job_id}/retry-failed",
    response_model=HistorySyncJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_failed_history_sync(
    job_id: Annotated[str, RoutePath(min_length=1)],
    service: Annotated[
        FullMarketHistoryService, Depends(get_full_market_history_service)
    ],
    executor: Annotated[Executor, Depends(get_history_sync_executor)],
) -> HistorySyncJob:
    try:
        job = service.retry_failed(job_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到日线同步任务",
        ) from error
    return _submit(service, executor, job)


@router.post("/{symbol}/history/sync", response_model=SyncReport)
def sync_history(
    symbol: Annotated[AShareCode, RoutePath()],
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 250,
) -> SyncReport:
    return service.sync_symbol(symbol, limit)


@router.get("/{symbol}/history", response_model=list[DailyBar])
def history(
    symbol: Annotated[AShareCode, RoutePath()],
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 250,
) -> list[DailyBar]:
    return service.repository.latest(symbol, limit)
