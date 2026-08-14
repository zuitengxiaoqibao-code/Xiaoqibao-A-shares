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


def _professional_unavailable_detail(error: Exception) -> str:
    """Return a safe, actionable reason without exposing vendor internals."""
    message = str(error)
    if message == "TDX Python professional call unavailable":
        return "官方 Python 专业接口初始化或调用失败；请确认通达信客户端已打开并完成专业插件初始化"
    if message == "TDX Python professional client unavailable":
        return "已发现官方 Python 模块，但专业客户端未初始化；请先打开通达信并等待插件就绪"
    if message == "TDX Python professional module unavailable":
        return "未能加载官方 Python 专业模块或配套 DLL；请在数据设置中检查通达信安装目录"
    if message == "TDX local bridge unavailable":
        return "本地通达信只读桥不可达；请确认桥接服务已启动并监听配置端口"
    if message == "TDX professional response is empty":
        return "通达信专业接口返回空结果；当前没有可验证的专业字段"
    if message == "TDX professional response has no verified table fields":
        return "通达信返回结果缺少可验证的 Fn/GP/BK/SC/GO 字段"
    return "本地通达信专业数据不可用；未生成替代或模拟数据"


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
            semantic_status="not_applicable",
            detail=_professional_unavailable_detail(error),
        )
    views = tuple(
        TdxProfessionalRowView.model_validate(item, from_attributes=True)
        for item in rows
    )
    return TdxProfessionalResponse(
        status="ready",
        semantic_status="detected_only",
        rows=views,
        fetched_at=max(item.fetched_at for item in views),
        detail="结构响应已验证；字段语义/单位尚未映射，未绑定业务菜单",
    )
