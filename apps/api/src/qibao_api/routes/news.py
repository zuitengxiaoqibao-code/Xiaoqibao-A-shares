from typing import Annotated
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    AIInterpretation,
    NewsCorrection,
    NormalizedNewsEvent,
)
from qibao_api.contracts.news_alerts import BreakingNewsAlertResponse
from qibao_api.dependencies import (
    get_decision_calendar,
    get_hotspot_service,
    get_news_repository,
    get_news_alert_service,
    get_news_service,
    get_server_time,
)
from qibao_api.gongbu.hotspot import HotspotSyncResult
from qibao_api.gongbu.news_repository import NewsIntegrityError
from qibao_api.libu_compliance.repository import SourceAuthorizationError
from qibao_api.zhongshu.news_quality import NewsQualityMetrics, NewsQualityService


router = APIRouter(prefix="/api/v1/news", tags=["工部新闻"])
CHINA_TZ = timezone(timedelta(hours=8))


class CorrectionRequest(BaseModel):
    event_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    review_state: Literal["pending", "verified", "rejected"]
    affected_instruments: tuple[tuple[AssetKind, str], ...] = ()
    industries: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()


async def _sync_news(service, symbol: str | None = None):
    try:
        if symbol is None:
            return await service.sync()
        return await service.sync_symbol(symbol)
    except SourceAuthorizationError as error:
        raise HTTPException(
            status_code=403, detail="A 股新闻数据源尚未授权：eastmoney"
        ) from error
    except (OSError, httpx.HTTPError) as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "news_upstream_unavailable", "message": "新闻源暂不可用"},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_news_data", "message": "新闻数据格式无法验证"},
        ) from error


@router.post("/sync")
async def sync_news(service: Annotated[object, Depends(get_news_service)]):
    return await _sync_news(service)


@router.post("/sync/{symbol}")
async def sync_symbol_news(
    symbol: Annotated[str, Path(pattern=r"^\d{6}$")],
    service: Annotated[object, Depends(get_news_service)],
):
    return await _sync_news(service, symbol)


@router.post("/hotspots/sync", response_model=HotspotSyncResult)
def sync_hotspots(
    trading_date: Annotated[date | None, Query()] = None,
    service: Annotated[object, Depends(get_hotspot_service)] = None,
    calendar: Annotated[object, Depends(get_decision_calendar)] = None,
    now: Annotated[datetime, Depends(get_server_time)] = None,
):
    local_date = now.astimezone(CHINA_TZ).date()
    target_date = trading_date or local_date
    if target_date > local_date:
        raise HTTPException(
            status_code=422,
            detail={"code": "future_trading_date", "message": "不能同步未来交易日热点"},
        )
    if not calendar.is_trading_day(target_date):
        raise HTTPException(
            status_code=422,
            detail={"code": "not_trading_day", "message": "所选日期不是交易日"},
        )
    try:
        return service.sync(target_date, fetched_at=now)
    except SourceAuthorizationError as error:
        raise HTTPException(
            status_code=403, detail="A 股热点数据源尚未授权：tonghuashun"
        ) from error
    except (OSError, httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "hotspot_upstream_unavailable",
                "message": "热点源暂不可用，既有新闻和建议不受影响",
            },
        ) from error


@router.get("/events", response_model=list[NormalizedNewsEvent])
def news_events(repository: Annotated[object, Depends(get_news_repository)]):
    try:
        return repository.events()
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "news_integrity_error", "message": "新闻证据存档校验失败"},
        ) from error


@router.get("/alerts", response_model=BreakingNewsAlertResponse)
def news_alerts(
    service: Annotated[object, Depends(get_news_alert_service)],
    now: Annotated[datetime, Depends(get_server_time)],
    symbol: Annotated[str | None, Query(pattern=r"^\d{6}$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    try:
        return service.current(now, symbol=symbol, limit=limit)
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "news_integrity_error", "message": "新闻证据存档校验失败"},
        ) from error


@router.get("/interpretations", response_model=list[AIInterpretation])
def news_interpretations(repository: Annotated[object, Depends(get_news_repository)]):
    try:
        return repository.interpretations()
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "news_integrity_error", "message": "新闻解释存档校验失败"},
        ) from error


@router.get("/quality", response_model=NewsQualityMetrics)
def news_quality(repository: Annotated[object, Depends(get_news_repository)]):
    try:
        return NewsQualityService(repository).metrics()
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "news_integrity_error", "message": "新闻质量数据校验失败"},
        ) from error


@router.post("/corrections", response_model=NewsCorrection)
def create_correction(
    request: CorrectionRequest,
    repository: Annotated[object, Depends(get_news_repository)],
):
    correction = NewsCorrection(
        correction_id=f"correction-{uuid4().hex}",
        event_id=request.event_id,
        corrected_at=datetime.now(timezone.utc),
        reason=request.reason,
        review_state=request.review_state,
        affected_instruments=request.affected_instruments,
        industries=request.industries,
        themes=request.themes,
    )
    try:
        repository.append_correction(correction)
    except NewsIntegrityError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return correction


@router.get("/corrections", response_model=list[NewsCorrection])
def news_corrections(repository: Annotated[object, Depends(get_news_repository)]):
    try:
        return repository.corrections()
    except NewsIntegrityError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "news_integrity_error", "message": "新闻修正存档校验失败"},
        ) from error
