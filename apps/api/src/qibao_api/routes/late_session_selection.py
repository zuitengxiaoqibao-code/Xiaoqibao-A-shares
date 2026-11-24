from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from qibao_api.a_shares.late_session_ai import LateSessionAIAnalyzer
from qibao_api.a_shares.late_session_selection_service import LateSessionSelectionService
from qibao_api.contracts.late_session_selection import LateSessionAIAnalysis, LateSessionRuleSettings, LateSessionSelectionResponse
from qibao_api.dependencies import get_effective_ai_settings, get_late_session_selection_service, get_server_time
from qibao_api.settings_repository import EffectiveAISettingsResolver
from qibao_api.contracts.late_session_selection import LateSessionAIRequest


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


@router.post("/ai-analysis", response_model=LateSessionAIAnalysis)
async def analyze_late_session_selection(
    request: LateSessionAIRequest,
    settings: Annotated[EffectiveAISettingsResolver, Depends(get_effective_ai_settings)],
    service: Annotated[LateSessionSelectionService, Depends(get_late_session_selection_service)],
) -> LateSessionAIAnalysis:
    try:
        selection = service.analysis_snapshot(request.snapshot_id)
    except KeyError as error:
        raise HTTPException(status_code=409, detail="筛选快照已过期或不存在，请刷新筛选结果后重试") from error
    return await LateSessionAIAnalyzer(settings).analyze(selection)
