from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from qibao_api.a_shares.late_session_selection_service import LateSessionSelectionService
from qibao_api.contracts.late_session_selection import LateSessionRuleSettings, LateSessionSelectionResponse
from qibao_api.dependencies import get_late_session_selection_service, get_server_time


router = APIRouter(
    prefix="/api/v1/a-shares/late-session-selection",
    tags=["A股尾盘选股"],
)


@router.get("", response_model=LateSessionSelectionResponse)
def current_late_session_selection(
    service: Annotated[LateSessionSelectionService, Depends(get_late_session_selection_service)],
    now: Annotated[datetime, Depends(get_server_time)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> LateSessionSelectionResponse:
    return service.current(now, limit=limit)


@router.post("/filter", response_model=LateSessionSelectionResponse)
def filter_late_session_selection(
    settings: LateSessionRuleSettings,
    service: Annotated[LateSessionSelectionService, Depends(get_late_session_selection_service)],
    now: Annotated[datetime, Depends(get_server_time)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> LateSessionSelectionResponse:
    return service.current(now, limit=limit, settings=settings)
