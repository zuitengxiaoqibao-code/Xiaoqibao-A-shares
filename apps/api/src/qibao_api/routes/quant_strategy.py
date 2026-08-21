from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from qibao_api.contracts.quant_shadow import QuantShadowAnalytics, ShadowDecisionRecord
from qibao_api.contracts.quant_calibration import QuantCalibrationReport
from qibao_api.a_shares.quant_calibration import build_calibration_report
from qibao_api.contracts.decision_journal import DecisionJournalCreate, DecisionJournalEntry
from qibao_api.contracts.quant_strategy import QuantStrategyDashboard
from qibao_api.dependencies import get_decision_journal, get_quant_shadow_ledger, get_quant_strategy_service, get_server_time
from qibao_api.a_shares.strategy_draft_gate import StrategyDraftGate


router = APIRouter(
    prefix="/api/v1/a-shares/quant-strategy",
    tags=["A股量化策略"],
)


@router.post("/drafts/validate")
def validate_strategy_draft(payload: dict) -> dict:
    """只做确定性门禁校验，不执行 AI 或用户提交的 Python 代码。"""
    data_version = str(payload.pop("data_version", "unknown"))
    result = StrategyDraftGate.review(payload, data_version)
    return {
        "status": result.status,
        "reasons": result.reasons,
        "evidence": result.evidence,
        "probability": result.probability,
    }


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


@router.get("/shadow", response_model=list[ShadowDecisionRecord])
def recent_shadow_decisions(
    ledger: Annotated[object, Depends(get_quant_shadow_ledger)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[ShadowDecisionRecord]:
    return list(ledger.recent(limit=limit))


@router.get("/shadow/analytics", response_model=QuantShadowAnalytics)
def shadow_analytics(
    ledger: Annotated[object, Depends(get_quant_shadow_ledger)],
    horizon: Annotated[int, Query()] = 5,
    decision_source: Literal[
        "quant_strategy", "opportunity_scan", "ai_hypothesis", "manual_watch"
    ] | None = None,
    opportunity_type: Annotated[
        str | None, Query(pattern=r"^[a-z][a-z0-9_]*$")
    ] = None,
) -> QuantShadowAnalytics:
    if horizon not in (1, 3, 5, 10, 20, 60):
        raise HTTPException(
            status_code=422,
            detail="评估周期只支持 1、3、5、10、20、60 个交易日",
        )
    return ledger.analytics(
        horizon=horizon,
        decision_source=decision_source,
        opportunity_type=opportunity_type,
    )


@router.get("/shadow/calibration", response_model=QuantCalibrationReport)
def shadow_calibration(
    ledger: Annotated[object, Depends(get_quant_shadow_ledger)],
    now: Annotated[datetime, Depends(get_server_time)],
    horizon: Annotated[int, Query()] = 5,
) -> QuantCalibrationReport:
    if horizon not in (1, 3, 5, 10, 20, 60):
        raise HTTPException(
            status_code=422,
            detail="校准周期只支持 1、3、5、10、20、60 个交易日",
        )
    return build_calibration_report(ledger, horizon=horizon, generated_at=now)


@router.get("/journal", response_model=list[DecisionJournalEntry])
def recent_decision_journal(
    journal: Annotated[object, Depends(get_decision_journal)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[DecisionJournalEntry]:
    return list(journal.recent(limit=limit))


@router.get("/journal/date/{trading_date}", response_model=list[DecisionJournalEntry])
def decision_journal_on_date(
    trading_date: date,
    journal: Annotated[object, Depends(get_decision_journal)],
) -> list[DecisionJournalEntry]:
    return list(journal.on_date(trading_date))


@router.post("/journal", response_model=DecisionJournalEntry, status_code=201)
def append_decision_journal(
    request: DecisionJournalCreate,
    journal: Annotated[object, Depends(get_decision_journal)],
) -> DecisionJournalEntry:
    return journal.append(request)


@router.get("/shadow/{decision_id}", response_model=ShadowDecisionRecord)
def shadow_decision(
    decision_id: str,
    ledger: Annotated[object, Depends(get_quant_shadow_ledger)],
) -> ShadowDecisionRecord:
    try:
        return ledger.get(decision_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="影子决策记录不存在") from error
