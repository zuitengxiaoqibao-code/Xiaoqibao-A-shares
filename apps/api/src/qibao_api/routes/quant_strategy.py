from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from qibao_api.contracts.quant_strategy import QuantStrategyDashboard
from qibao_api.dependencies import get_quant_strategy_service, get_server_time


router = APIRouter(
    prefix="/api/v1/a-shares/quant-strategy",
    tags=["A股量化策略"],
)


@router.get("", response_model=QuantStrategyDashboard)
def current_quant_strategy(
    service: Annotated[object, Depends(get_quant_strategy_service)],
    now: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
) -> QuantStrategyDashboard:
    try:
        return service.current(now, as_of=as_of, limit=limit)
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "quant_strategy_unavailable",
                "message": "短线风格与策略数据暂不可用，请检查本地行情和日线覆盖",
            },
        ) from error
