from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from qibao_api.contracts.quant_research import QuantResearchSnapshot
from qibao_api.dependencies import get_quant_research_service, get_server_time


router = APIRouter(
    prefix="/api/v1/a-shares/quant-research",
    tags=["A股量化研究"],
)


@router.get("", response_model=QuantResearchSnapshot)
def current_quant_research(
    service: Annotated[object, Depends(get_quant_research_service)],
    now: Annotated[datetime, Depends(get_server_time)],
) -> QuantResearchSnapshot:
    try:
        return service.current(now)
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "quant_research_unavailable",
                "message": "量化研究快照暂不可用，请稍后重试或检查本地数据状态",
            },
        ) from error
