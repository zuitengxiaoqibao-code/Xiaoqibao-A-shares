from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from qibao_api.contracts.market_overview import MarketOverviewResponse
from qibao_api.dependencies import get_market_overview_service, get_server_time


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
