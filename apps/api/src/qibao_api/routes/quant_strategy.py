from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from qibao_api.contracts.quant_shadow import QuantShadowAnalytics, ShadowDecisionRecord
from qibao_api.contracts.decision_journal import DecisionJournalCreate, DecisionJournalEntry
from qibao_api.contracts.quant_strategy import QuantStrategyDashboard
from qibao_api.dependencies import get_decision_journal, get_quant_shadow_ledger, get_quant_strategy_service, get_server_time


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
) -> QuantShadowAnalytics:
    if horizon not in (1, 3, 5, 10, 20):
        raise HTTPException(status_code=422, detail="评估周期只支持 1、3、5、10、20 个交易日")
    return ledger.analytics(horizon=horizon)


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
