from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, status

from qibao_api.contracts.instruments import AShareCode
from qibao_api.contracts.portfolio_risk import (
    PortfolioPositionInput,
    PortfolioPositionUpdate,
    PortfolioRiskRequest,
    PortfolioRiskResponse,
)
from qibao_api.dependencies import (
    get_portfolio_risk_service,
    get_portfolio_risk_store,
    get_quant_strategy_service,
    get_server_time,
)


router = APIRouter(prefix="/api/v1/a-shares/portfolio-risk", tags=["A股组合风险"])
CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _market_regime(quant_service, now: datetime, selected_date) -> str | None:
    try:
        dashboard = quant_service.current(now, as_of=selected_date, limit=1)
        return dashboard.regime.regime
    except (OSError, ValueError):
        return None


def _analyze(service, quant_service, positions, now: datetime, selected_date) -> PortfolioRiskResponse:
    return service.analyze(
        positions,
        as_of=selected_date,
        market_regime=_market_regime(quant_service, now, selected_date),
    )


@router.get("", response_model=PortfolioRiskResponse)
def current_portfolio_risk(
    store: Annotated[object, Depends(get_portfolio_risk_store)],
    service: Annotated[object, Depends(get_portfolio_risk_service)],
    quant_service: Annotated[object, Depends(get_quant_strategy_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> PortfolioRiskResponse:
    selected_date = now.astimezone(CHINA_TZ).date()
    return _analyze(service, quant_service, store.current(), now, selected_date)


@router.post("", response_model=PortfolioRiskResponse)
def analyze_portfolio_risk(
    request: PortfolioRiskRequest,
    service: Annotated[object, Depends(get_portfolio_risk_service)],
    quant_service: Annotated[object, Depends(get_quant_strategy_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> PortfolioRiskResponse:
    selected_date = request.as_of or now.astimezone(CHINA_TZ).date()
    try:
        return _analyze(service, quant_service, request.positions, now, selected_date)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.put("/positions/{symbol}", response_model=PortfolioRiskResponse)
def upsert_portfolio_position(
    symbol: Annotated[AShareCode, Path()],
    update: PortfolioPositionUpdate,
    store: Annotated[object, Depends(get_portfolio_risk_store)],
    service: Annotated[object, Depends(get_portfolio_risk_service)],
    quant_service: Annotated[object, Depends(get_quant_strategy_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> PortfolioRiskResponse:
    store.upsert(PortfolioPositionInput(
        symbol=symbol,
        shares=update.shares,
        cost_price=update.cost_price,
    ))
    selected_date = now.astimezone(CHINA_TZ).date()
    return _analyze(service, quant_service, store.current(), now, selected_date)


@router.delete("/positions/{symbol}", response_model=PortfolioRiskResponse)
def delete_portfolio_position(
    symbol: Annotated[AShareCode, Path()],
    store: Annotated[object, Depends(get_portfolio_risk_store)],
    service: Annotated[object, Depends(get_portfolio_risk_service)],
    quant_service: Annotated[object, Depends(get_quant_strategy_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> PortfolioRiskResponse:
    store.delete(symbol)
    selected_date = now.astimezone(CHINA_TZ).date()
    return _analyze(service, quant_service, store.current(), now, selected_date)
