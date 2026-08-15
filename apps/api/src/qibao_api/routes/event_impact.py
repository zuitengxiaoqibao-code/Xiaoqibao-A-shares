from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from qibao_api.a_shares.event_impact import EventImpactNotFoundError
from qibao_api.contracts.event_impact import EventImpactReport
from qibao_api.dependencies import get_event_impact_service, get_server_time
from qibao_api.gongbu.news_repository import NewsIntegrityError


router = APIRouter(tags=["新闻事件影响"])


@router.get(
    "/api/v1/news/events/{event_id}/impact",
    response_model=EventImpactReport,
)
@router.get(
    "/api/v1/event-impact/{event_id}",
    response_model=EventImpactReport,
    include_in_schema=False,
)
def event_impact(
    event_id: Annotated[str, Path(min_length=1)],
    service: Annotated[object, Depends(get_event_impact_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> EventImpactReport:
    try:
        return service.report(event_id, cutoff=now)
    except EventImpactNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "news_event_not_found", "message": "未找到该新闻事件"},
        ) from error
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "news_integrity_error", "message": "新闻事件证据校验失败"},
        ) from error
