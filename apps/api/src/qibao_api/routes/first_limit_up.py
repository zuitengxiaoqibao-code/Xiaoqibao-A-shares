from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from qibao_api.contracts.first_limit_up import FirstLimitUpBoard
from qibao_api.contracts.kronos_forecast import KronosForecastResponse
from qibao_api.dependencies import (
    get_first_limit_up_service,
    get_kronos_forecast_service,
    get_server_time,
)
from qibao_api.libu_compliance.repository import SourceAuthorizationError


router = APIRouter(prefix="/api/v1/a-shares/first-limit-up", tags=["首次涨停"])


def _research_date(value: date | None, server_time: datetime) -> date:
    today = server_time.astimezone(ZoneInfo("Asia/Shanghai")).date()
    result = value or today
    if result > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "future_as_of_not_allowed", "message": "研究截止日期不能晚于今天"},
        )
    return result


def _unavailable(error: Exception) -> HTTPException:
    if isinstance(error, SourceAuthorizationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "first_limit_up_source_authorization_required",
                "message": "请先在礼部完成 A 股行情数据授权",
            },
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "first_limit_up_unavailable",
            "message": "首次涨停数据暂不可用，请检查日线同步和数据源后重试",
        },
    )


@router.get("", response_model=FirstLimitUpBoard)
def current(
    service: Annotated[object, Depends(get_first_limit_up_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = Query(default=None),
) -> FirstLimitUpBoard:
    try:
        return service.current(_research_date(as_of, server_time))
    except (SourceAuthorizationError, OSError, ValueError) as error:
        raise _unavailable(error) from error


@router.post("/refresh", response_model=FirstLimitUpBoard)
async def refresh(
    request: Request,
    service: Annotated[object, Depends(get_first_limit_up_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = Query(default=None),
) -> FirstLimitUpBoard:
    selected_date = _research_date(as_of, server_time)
    tasks = getattr(request.app.state, "first_limit_up_refresh_tasks", None)
    if tasks is None:
        tasks = {}
        request.app.state.first_limit_up_refresh_tasks = tasks
    existing = tasks.get(selected_date)
    if existing is None or existing.done():
        async def run_refresh() -> FirstLimitUpBoard:
            return await service.refresh(selected_date)

        existing = asyncio.create_task(run_refresh(), name=f"first-limit-up-refresh-{selected_date}")
        tasks[selected_date] = existing
        existing.add_done_callback(lambda completed: tasks.pop(selected_date, None))
    # Give a fast local implementation a scheduling turn so callers receive
    # the refreshed result in tests and on warm caches; a full-market scan is
    # intentionally allowed to continue after the short response budget.
    try:
        await asyncio.wait_for(asyncio.shield(existing), timeout=0.25)
        return existing.result()
    except asyncio.TimeoutError:
        try:
            return service.current(selected_date)
        except (SourceAuthorizationError, OSError, ValueError) as error:
            raise _unavailable(error) from error
    except (SourceAuthorizationError, OSError, ValueError) as error:
        raise _unavailable(error) from error


@router.get("/quant-forecast", response_model=KronosForecastResponse)
async def quant_forecast(
    service: Annotated[object, Depends(get_kronos_forecast_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    symbol: Annotated[str, Query(pattern=r"^\d{6}$")],
    as_of: date | None = Query(default=None),
    horizon: int = Query(default=20, ge=5, le=20),
) -> KronosForecastResponse:
    try:
        return await service.forecast(
            symbol,
            as_of=_research_date(as_of, server_time),
            horizon=horizon,
        )
    except (SourceAuthorizationError, OSError, ValueError) as error:
        raise _unavailable(error) from error
