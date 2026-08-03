from concurrent.futures import Executor
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from qibao_api.contracts.bars import DailyBar, SyncReport
from qibao_api.contracts.history_sync import HistoryCoverageSummary, HistorySyncJob
from qibao_api.contracts.instruments import AShareCode
from qibao_api.dependencies import (
    get_full_market_history_service,
    get_history_sync_executor,
    get_market_data_service,
    get_server_time,
)
from qibao_api.gongbu.data_service import MarketDataService
from qibao_api.gongbu.full_market_history import FullMarketHistoryService

router = APIRouter(prefix="/api/v1/a-shares", tags=["工部数据"])


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


@router.post(
    "/history-sync/{job_id}/pause",
    response_model=HistorySyncJob,
)
def pause_history_sync(
    job_id: Annotated[str, Path(min_length=1)],
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
    job_id: Annotated[str, Path(min_length=1)],
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
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 250,
) -> SyncReport:
    return service.sync_symbol(symbol, limit)


@router.get("/{symbol}/history", response_model=list[DailyBar])
def history(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 250,
) -> list[DailyBar]:
    return service.repository.latest(symbol, limit)
