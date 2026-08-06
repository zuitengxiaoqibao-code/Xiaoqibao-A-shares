from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from qibao_api.contracts.market_review import MarketIntervalReviewSnapshot
from qibao_api.contracts.market_overview import MarketOverviewResponse
from qibao_api.dependencies import (
    get_local_market_review_source,
    get_market_overview_service,
    get_server_time,
)


router = APIRouter(
    prefix="/api/v1/a-shares/market-overview",
    tags=["A股信息总览"],
)


@router.get("", response_model=MarketOverviewResponse)
def current_market_overview(
    service: Annotated[object, Depends(get_market_overview_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> MarketOverviewResponse:
    try:
        return service.current(now)
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "market_overview_unavailable",
                "message": "信息总览数据暂不可用，请稍后重试",
            },
        ) from error


@router.get("/interval", response_model=MarketIntervalReviewSnapshot)
def interval_market_review(
    source: Annotated[object | None, Depends(get_local_market_review_source)],
    now: Annotated[datetime, Depends(get_server_time)],
    start_date: date = Query(..., description="区间起始日期"),
    end_date: date = Query(..., description="区间结束日期"),
) -> MarketIntervalReviewSnapshot:
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "interval_dates_invalid", "message": "起始日期必须早于结束日期"},
        )
    if end_date > now.astimezone().date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "interval_end_date_in_future", "message": "结束日期不能晚于当前日期"},
        )
    if source is None or not hasattr(source, "interval"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "interval_review_unavailable", "message": "本地日线区间接口尚未就绪"},
        )
    try:
        return source.interval(start_date=start_date, end_date=end_date)
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "interval_review_unavailable", "message": "本地区间日线数据暂不可用"},
        ) from error
