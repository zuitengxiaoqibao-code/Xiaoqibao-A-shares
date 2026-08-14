from concurrent.futures import Executor
from datetime import date, datetime
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
from qibao_api.contracts.tdx_import import TdxImportJob, TdxImportScan
from qibao_api.contracts.instruments import AShareCode
from qibao_api.dependencies import (
    get_full_market_history_service,
    get_history_sync_executor,
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


def _submit(
    service: FullMarketHistoryService,
    executor: Executor,
    job: HistorySyncJob,
) -> HistorySyncJob:
    executor.submit(service.run, job.job_id)
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
    job = service.create_incremental(target_date or _china_date(now))
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
    return service.coverage(target_date or _china_date(now))


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
        target_date or _china_date(now), offset=offset, limit=limit,
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
