from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from qibao_api.a_shares.market_sentiment import (
    MarketSentimentNotTradingDay,
    MarketSentimentResponse,
    MarketSentimentWrongPhase,
)
from qibao_api.a_shares.market_sentiment_repository import (
    MarketSentimentStoreError,
)
from qibao_api.contracts.market_sentiment import MarketSentimentSnapshot
from qibao_api.dependencies import (
    get_market_sentiment_service,
    get_server_time,
    run_latency_critical_read,
)
from qibao_api.gongbu.tencent_market_sentiment import (
    MarketSentimentSourceUnavailable,
)
from qibao_api.libu_compliance.repository import SourceAuthorizationError


router = APIRouter(
    prefix="/api/v1/a-shares/market-sentiment",
    tags=["A股市场情绪"],
)


class MarketSentimentHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_date: date
    trajectory: tuple[MarketSentimentSnapshot, ...]


@router.get("/current", response_model=MarketSentimentResponse)
async def current_market_sentiment(
    request: Request,
    service: Annotated[object, Depends(get_market_sentiment_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> MarketSentimentResponse:
    try:
        return await run_latency_critical_read(request, service.current, now)
    except Exception as error:
        _raise_safe_error(error)


@router.get("/{trading_date}", response_model=MarketSentimentHistoryResponse)
def market_sentiment_history(
    trading_date: date,
    service: Annotated[object, Depends(get_market_sentiment_service)],
) -> MarketSentimentHistoryResponse:
    try:
        trajectory = service.history(trading_date)
    except Exception as error:
        _raise_safe_error(error)
    return MarketSentimentHistoryResponse(
        trading_date=trading_date,
        trajectory=trajectory,
    )


@router.post("/refresh", response_model=MarketSentimentSnapshot)
def refresh_market_sentiment(
    service: Annotated[object, Depends(get_market_sentiment_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> MarketSentimentSnapshot:
    try:
        return service.refresh(now)
    except Exception as error:
        _raise_safe_error(error)


def _raise_safe_error(error: Exception) -> None:
    if isinstance(error, SourceAuthorizationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "market_sentiment_source_not_authorized",
                "message": "请先在数据设置中授权腾讯 A 股实时行情来源",
            },
        ) from error
    if isinstance(error, MarketSentimentWrongPhase):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "market_sentiment_wrong_phase",
                "message": "盘前只展示昨收基线，请在盘中或盘后刷新",
            },
        ) from error
    if isinstance(error, MarketSentimentNotTradingDay):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "market_sentiment_not_trading_day",
                "message": "当前不是已确认的 A 股交易日",
            },
        ) from error
    if isinstance(
        error,
        (
            MarketSentimentSourceUnavailable,
            MarketSentimentStoreError,
            OSError,
            ValueError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "market_sentiment_unavailable",
                "message": "A 股市场情绪数据暂不可用，请稍后重试",
            },
        ) from error
    raise error
