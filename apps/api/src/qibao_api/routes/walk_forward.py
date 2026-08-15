from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path

from qibao_api.a_shares.walk_forward import run_walk_forward
from qibao_api.contracts.instruments import AShareCode
from qibao_api.contracts.walk_forward import WalkForwardReport, WalkForwardRequest
from qibao_api.dependencies import get_market_data_service


router = APIRouter(prefix="/api/v1/a-shares", tags=["中书省样本外验证"])


@router.post("/{symbol}/walk-forward", response_model=WalkForwardReport)
def walk_forward(
    symbol: Annotated[AShareCode, Path()],
    request: Annotated[WalkForwardRequest, Body()],
    service: Annotated[object, Depends(get_market_data_service)],
) -> WalkForwardReport:
    bars = service.repository.latest(symbol, 2000)
    return run_walk_forward(bars, request)
