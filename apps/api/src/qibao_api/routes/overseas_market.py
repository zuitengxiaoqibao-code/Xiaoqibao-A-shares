from typing import Annotated

from fastapi import APIRouter, Depends, Request

from qibao_api.contracts.overseas_market import OverseasMarketSnapshot
from qibao_api.dependencies import get_overseas_market_service


router = APIRouter(prefix="/api/v1/market", tags=["海外市场"])


@router.get("/overseas", response_model=OverseasMarketSnapshot)
async def current_overseas_market(
    request: Request,
    service: Annotated[object, Depends(get_overseas_market_service)],
) -> OverseasMarketSnapshot:
    return await service.current()
