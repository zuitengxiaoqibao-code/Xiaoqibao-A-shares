from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException

from qibao_api.contracts.watchlist_risk import WatchlistRiskRequest, WatchlistRiskResponse
from qibao_api.dependencies import get_server_time, get_watchlist_risk_service


router = APIRouter(prefix="/api/v1/a-shares/watchlist-risk", tags=["A股观察篮子风险"])
CHINA_TZ = ZoneInfo("Asia/Shanghai")


@router.post("", response_model=WatchlistRiskResponse)
def analyze_watchlist_risk(
    request: WatchlistRiskRequest,
    service: Annotated[object, Depends(get_watchlist_risk_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> WatchlistRiskResponse:
    try:
        return service.analyze(
            request.symbols,
            as_of=request.as_of or now.astimezone(CHINA_TZ).date(),
            observed_at=now,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

