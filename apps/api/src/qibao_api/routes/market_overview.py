import asyncio
import queue
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from qibao_api.contracts.market_review import MarketIntervalReviewSnapshot
from qibao_api.contracts.market_overview import MarketOverviewResponse
from qibao_api.dependencies import (
    get_local_market_review_source,
    get_market_overview_service,
    get_realtime_snapshot_bus,
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


@router.get("/stream")
async def stream_market_overview(
    request: Request,
    service: Annotated[object, Depends(get_market_overview_service)],
    bus: Annotated[object | None, Depends(get_realtime_snapshot_bus)],
    now: Annotated[datetime, Depends(get_server_time)],
):
    if bus is None or not hasattr(bus, "subscribe"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "realtime_stream_unavailable", "message": "实时推送总线尚未就绪"},
        )
    subscription = bus.subscribe({"market_overview"})
    try:
        current = service.current(now)
    except (OSError, ValueError) as error:
        bus.unsubscribe(subscription)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "market_overview_unavailable", "message": "信息总览数据暂不可用，请稍后重试"},
        ) from error
    initial = bus.latest("market_overview")
    if initial is None:
        initial = bus.publish(
            "market_overview",
            current.model_dump(mode="json"),
            observed_at=current.market_data.observed_at or current.observed_at,
            source=current.market_data.source,
            freshness=current.market_data.freshness,
        )

    async def events():
        try:
            yield bus.sse_frame(initial)
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


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
