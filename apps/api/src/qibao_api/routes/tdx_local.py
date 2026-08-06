from typing import Annotated

from fastapi import APIRouter, Depends, Query

from qibao_api.contracts.tdx_local import (
    TdxFormulaPointView,
    TdxFormulaResponse,
    TdxIpoCalendarResponse,
    TdxIpoEventView,
    TdxProfessionalResponse,
    TdxProfessionalRowView,
)
from qibao_api.dependencies import (
    get_tdx_formula_source,
    get_tdx_ipo_source,
    get_tdx_professional_source,
)
from qibao_api.gongbu.tdx_formula import TdxFormulaDataUnavailable
from qibao_api.gongbu.tdx_local_calendar import TdxCalendarDataUnavailable
from qibao_api.gongbu.tdx_local_professional import TdxProfessionalDataUnavailable


router = APIRouter(prefix="/api/v1/tdx/local", tags=["通达信只读数据"])


@router.get("/ipo-calendar", response_model=TdxIpoCalendarResponse)
def get_ipo_calendar(
    source: Annotated[object, Depends(get_tdx_ipo_source)],
) -> TdxIpoCalendarResponse:
    try:
        events = source.fetch()
    except (TdxCalendarDataUnavailable, OSError, ValueError) as error:
        return TdxIpoCalendarResponse(
            status="unavailable",
            detail=f"本地通达信新股/新债日历不可用（{type(error).__name__}）",
        )
    views = tuple(TdxIpoEventView.model_validate(item, from_attributes=True) for item in events)
    return TdxIpoCalendarResponse(
        status="ready",
        events=views,
        fetched_at=max(item.fetched_at for item in views),
    )


@router.get("/formula", response_model=TdxFormulaResponse)
def get_formula_batch(
    source: Annotated[object, Depends(get_tdx_formula_source)],
    formula_name: str = Query(pattern=r"^formula_process_mul_[A-Za-z0-9_]+$"),
    stock_codes: tuple[str, ...] = Query(min_length=1, max_length=200),
) -> TdxFormulaResponse:
    try:
        points = source.fetch(formula_name=formula_name, stock_codes=stock_codes)
    except (TdxFormulaDataUnavailable, OSError, ValueError) as error:
        return TdxFormulaResponse(
            status="unavailable",
            detail=f"本地通达信公式结果不可用（{type(error).__name__}）",
        )
    views = tuple(TdxFormulaPointView.model_validate(item, from_attributes=True) for item in points)
    return TdxFormulaResponse(
        status="ready",
        points=views,
        fetched_at=max(item.fetched_at for item in views),
    )


@router.get("/professional", response_model=TdxProfessionalResponse)
def get_professional_data(
    source: Annotated[object, Depends(get_tdx_professional_source)],
    method: str = Query(min_length=1),
    table_list: tuple[str, ...] = Query(min_length=1, max_length=50),
    stock_codes: tuple[str, ...] = Query(default=(), max_length=200),
    start_time: str = Query(default=""),
    end_time: str = Query(default=""),
    report_type: str = Query(default="report_time"),
    year: int = Query(default=0),
    mmdd: int = Query(default=0),
) -> TdxProfessionalResponse:
    try:
        rows = source.fetch(
            method=method,
            fields=table_list,
            stock_codes=stock_codes,
            start_time=start_time,
            end_time=end_time,
            report_type=report_type,
            year=year,
            mmdd=mmdd,
        )
    except (TdxProfessionalDataUnavailable, OSError, ValueError) as error:
        return TdxProfessionalResponse(
            status="unavailable",
            detail=f"本地通达信专业数据不可用（{type(error).__name__}）",
        )
    views = tuple(
        TdxProfessionalRowView.model_validate(item, from_attributes=True)
        for item in rows
    )
    return TdxProfessionalResponse(
        status="ready",
        rows=views,
        fetched_at=max(item.fetched_at for item in views),
    )
