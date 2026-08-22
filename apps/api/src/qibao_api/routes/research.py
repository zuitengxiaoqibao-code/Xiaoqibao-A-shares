from datetime import date, datetime, timedelta
import asyncio
from decimal import DecimalException
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
import httpx
from pydantic import BaseModel, ConfigDict, Field

from qibao_api.a_shares.candidate_sentiment_repository import (
    CandidateSentimentStoreError,
)
from qibao_api.a_shares.candidate_sentiment_service import (
    CandidateSentimentInputError,
    CandidateSnapshotNotFoundError,
)
from qibao_api.a_shares.diagnosis import AShareDiagnosis, DiagnosisUnavailableError
from qibao_api.a_shares.cockpit import StockCockpitSnapshot, UnknownAShareError
from qibao_api.a_shares.instrument_directory import AShareInstrument, AShareInstrumentDirectory
from qibao_api.a_shares.models import CandidateBoard, CandidateScoreBoard
from qibao_api.a_shares.preparation import StockPreparation
from qibao_api.a_shares.repository import AShareResearchStoreError
from qibao_api.contracts.instruments import AShareCode, validate_a_share_code
from qibao_api.contracts.market import DataQuality
from qibao_api.contracts.candidate_sentiment import CandidateSentimentBatch
from qibao_api.contracts.company_research import CompanyResearchResponse
from qibao_api.contracts.company_research_task import CompanyResearchTaskSnapshot
from qibao_api.contracts.company_research_ai_task import CompanyResearchAITaskSnapshot
from qibao_api.contracts.research_compare import ResearchCompareRequest, ResearchCompareResponse
from qibao_api.a_shares.research_compare import build_research_comparison
from qibao_api.contracts.research import ResearchCard
from qibao_api.contracts.stock_timeline import StockTimelineResponse
from qibao_api.dependencies import (
    get_a_share_diagnosis_service,
    get_a_share_cockpit_service,
    get_a_share_instrument_directory,
    get_a_share_preparation_service,
    get_a_share_quote_source,
    get_a_share_universe_source,
    get_candidate_sentiment_service,
    get_company_research_service,
    get_company_research_task_service,
    get_company_research_ai_task_service,
    get_company_research_version_repository,
    get_compliance_repository,
    get_poll_state_repository,
    get_pipeline,
    get_server_time,
    get_stock_timeline_service,
)
from qibao_api.gongbu.market_feed import MarketFeedSnapshot
from qibao_api.gongbu.tencent_quotes import market_prefix
from qibao_api.shangshu.pipeline import ResearchPipeline
from qibao_api.shangshu.decision_repository import DecisionIntegrityError
from qibao_api.libu_compliance.repository import SourceAuthorizationError

router = APIRouter(prefix="/api/v1/a-shares", tags=["A股"])


class AShareSearchItem(AShareInstrument):
    asset: Literal["a_share"] = "a_share"


class AShareSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    items: tuple[AShareSearchItem, ...]
    server_time: datetime
    source_status: Literal["ready", "unavailable"] = "ready"


class AShareUniverseSyncResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready"]
    count: int
    observed_at: datetime
    source: str


class AShareDirectoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[AShareSearchItem, ...]
    observed_at: datetime | None
    count: int


class CandidateSentimentBatchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_snapshot_id: str = Field(min_length=1)


class IntradayFocusRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["quant_analysis", "watchlist"] = "quant_analysis"
    ttl_seconds: int = Field(default=900, ge=60, le=3600)


class IntradayFocusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready"] = "ready"
    symbol: str
    source: str
    registered_at: datetime
    expires_at: datetime


def _quote_observed_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return value


def _quote_quality(value: DataQuality) -> Literal["ready", "stale", "unavailable"]:
    if value == DataQuality.FRESH:
        return "ready"
    if value == DataQuality.STALE:
        return "stale"
    return "unavailable"


@router.post("/universe/sync", response_model=AShareUniverseSyncResponse)
async def sync_universe(
    directory: Annotated[AShareInstrumentDirectory, Depends(get_a_share_instrument_directory)],
    source: Annotated[object, Depends(get_a_share_universe_source)],
    compliance: Annotated[object, Depends(get_compliance_repository)],
) -> AShareUniverseSyncResponse:
    try:
        compliance.require_feature_sources("a_share_universe", "a_share")
        instruments = await source.fetch()
    except SourceAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "source_authorization_required",
                "message": "请先在礼部完成 A 股基础证券目录授权",
            },
        ) from error
    except (httpx.HTTPError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "a_share_universe_unavailable",
                "message": "A 股证券目录来源暂不可用，请稍后重试",
            },
        ) from error
    if not instruments:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "a_share_universe_empty",
                "message": "A 股证券目录来源未返回有效标的",
            },
        )
    directory.observe_many(instruments)
    observed_at = max(item.observed_at for item in instruments)
    return AShareUniverseSyncResponse(
        status="ready", count=len(instruments), observed_at=observed_at,
        source=str(getattr(source, "last_source", "eastmoney-a-share-universe")),
    )


@router.get("/directory", response_model=AShareDirectoryResponse)
def instrument_directory_snapshot(
    directory: Annotated[AShareInstrumentDirectory, Depends(get_a_share_instrument_directory)],
) -> AShareDirectoryResponse:
    snapshot = getattr(directory, "snapshot", None)
    if callable(snapshot):
        items = snapshot()
    else:
        # Keep lightweight test and plugin directory adapters compatible with
        # the read-only endpoint while production uses the indexed snapshot.
        items = tuple(getattr(directory, "items", {}).values())
    latest = getattr(directory, "latest_observed_at", lambda: None)()
    return AShareDirectoryResponse(
        items=tuple(AShareSearchItem(**item.model_dump()) for item in items),
        observed_at=latest,
        count=len(items),
    )


@router.get("/search", response_model=AShareSearchResponse)
async def search_instruments(
    directory: Annotated[AShareInstrumentDirectory, Depends(get_a_share_instrument_directory)],
    quote_source: Annotated[object, Depends(get_a_share_quote_source)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> AShareSearchResponse:
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="q must not be empty",
        )
    items = directory.search(query, limit)
    source_status: Literal["ready", "unavailable"] = "ready"
    try:
        exact_symbol = validate_a_share_code(query)
    except ValueError:
        exact_symbol = None
    if exact_symbol is not None:
        local_instrument = next(
            (
                item
                for item in items
                if item.symbol == exact_symbol and item.name.strip() != exact_symbol
            ),
            None,
        )
        if local_instrument is not None:
            items = (local_instrument,)
        else:
            try:
                quote = await quote_source.fetch(exact_symbol)
                if quote.symbol != exact_symbol:
                    raise ValueError("Tencent quote symbol does not match requested A-share")
                instrument = AShareInstrument(
                    symbol=quote.symbol,
                    name=quote.name,
                    exchange=market_prefix(quote.symbol),
                    observed_at=_quote_observed_at(quote.observed_at),
                    quote_quality=_quote_quality(quote.quality),
                )
            except (httpx.HTTPError, ValueError, DecimalException):
                items = ()
                source_status = "unavailable"
            else:
                directory.observe(instrument)
                items = (instrument,)
    return AShareSearchResponse(
        query=query,
        items=tuple(AShareSearchItem(**item.model_dump()) for item in items),
        server_time=server_time,
        source_status=source_status,
    )


def _beijing_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _research_date(value: date | None) -> date:
    today = _beijing_today()
    result = value or today
    if result > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "future_as_of_not_allowed",
                "message": "研究截止日期不能晚于北京时间今天",
            },
        )
    return result


def _research_date_at(value: date | None, server_time: datetime) -> date:
    today = server_time.astimezone(ZoneInfo("Asia/Shanghai")).date()
    result = value or today
    if result > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "future_as_of_not_allowed",
                "message": "研究截止日期不能晚于北京时间今天",
            },
        )
    return result


def _store_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "a_share_research_store_error",
            "message": "A 股研究存档暂不可用",
        },
    )


def _candidate_sentiment_error(error: Exception) -> HTTPException:
    if isinstance(error, CandidateSnapshotNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "candidate_snapshot_not_found",
                "message": "未找到该短线候选快照",
            },
        )
    if isinstance(error, CandidateSentimentInputError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "candidate_sentiment_input_invalid",
                "message": "短线候选情绪输入无效",
            },
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "candidate_sentiment_store_error",
            "message": "短线候选情绪存档暂不可用",
        },
    )


@router.get("/candidates", response_model=CandidateBoard)
def candidates(
    service: Annotated[object, Depends(get_a_share_diagnosis_service)],
    as_of: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CandidateBoard:
    try:
        return service.candidates(_research_date(as_of), limit)
    except AShareResearchStoreError as error:
        raise _store_error() from error


@router.get("/candidate-scores", response_model=CandidateScoreBoard)
def candidate_scores(
    service: Annotated[object, Depends(get_a_share_diagnosis_service)],
    symbols: Annotated[list[AShareCode], Query()],
    as_of: date | None = None,
    horizon: Literal["short_term", "swing"] = "short_term",
) -> CandidateScoreBoard:
    return service.candidate_scores(
        _research_date(as_of), tuple(symbols), horizon=horizon
    )


@router.post(
    "/candidate-sentiment/batch",
    response_model=CandidateSentimentBatch,
)
def candidate_sentiment_batch(
    request: CandidateSentimentBatchRequest,
    service: Annotated[object, Depends(get_candidate_sentiment_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
) -> CandidateSentimentBatch:
    try:
        return service.current(request.candidate_snapshot_id, server_time)
    except (
        CandidateSnapshotNotFoundError,
        CandidateSentimentInputError,
        CandidateSentimentStoreError,
        AShareResearchStoreError,
    ) as error:
        raise _candidate_sentiment_error(error) from error


@router.post(
    "/candidate-sentiment/batch/refresh",
    response_model=CandidateSentimentBatch,
)
async def refresh_candidate_sentiment_batch(
    request: CandidateSentimentBatchRequest,
    service: Annotated[object, Depends(get_candidate_sentiment_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
) -> CandidateSentimentBatch:
    try:
        return await service.refresh(request.candidate_snapshot_id, server_time)
    except (
        CandidateSnapshotNotFoundError,
        CandidateSentimentInputError,
        CandidateSentimentStoreError,
        AShareResearchStoreError,
    ) as error:
        raise _candidate_sentiment_error(error) from error


@router.get("/{symbol}/diagnosis", response_model=AShareDiagnosis)
async def diagnosis(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_a_share_diagnosis_service)],
    as_of: date | None = None,
) -> AShareDiagnosis:
    try:
        return await service.diagnose(symbol, _research_date(as_of))
    except SourceAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "source_authorization_required",
                "message": "请先在礼部完成 A 股行情和财务数据授权",
            },
        ) from error
    except DiagnosisUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "a_share_diagnosis_unavailable",
                "message": "A 股基础行情和本地历史均不可用",
            },
        ) from error
    except AShareResearchStoreError as error:
        raise _store_error() from error


@router.get("/{symbol}/intraday-ticks", response_model=list[MarketFeedSnapshot])
def intraday_ticks(
    symbol: Annotated[AShareCode, Path()],
    repository: Annotated[object | None, Depends(get_poll_state_repository)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    trading_date: date | None = None,
) -> tuple[MarketFeedSnapshot, ...]:
    if repository is None:
        return ()
    selected_date = _research_date_at(trading_date, server_time)
    return repository.intraday_snapshots(
        symbol, selected_date, cutoff=server_time,
    )


@router.post("/{symbol}/intraday-focus", response_model=IntradayFocusResponse)
def register_intraday_focus(
    symbol: Annotated[AShareCode, Path()],
    request: IntradayFocusRequest,
    repository: Annotated[object | None, Depends(get_poll_state_repository)],
    server_time: Annotated[datetime, Depends(get_server_time)],
) -> IntradayFocusResponse:
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "intraday_monitor_unavailable",
                "message": "盘中监测服务暂不可用",
            },
        )
    expires_at = server_time + timedelta(seconds=request.ttl_seconds)
    repository.register_focus_symbol(
        symbol,
        source=request.source,
        registered_at=server_time,
        expires_at=expires_at,
    )
    return IntradayFocusResponse(
        symbol=symbol,
        source=request.source,
        registered_at=server_time,
        expires_at=expires_at,
    )


@router.get("/{symbol}/timeline", response_model=StockTimelineResponse)
def stock_timeline(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_stock_timeline_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = None,
) -> StockTimelineResponse:
    return service.get(
        symbol,
        _research_date_at(as_of, server_time),
        server_time,
    )


@router.post("/{symbol}/prepare", response_model=StockPreparation)
async def prepare(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_a_share_preparation_service)],
    directory: Annotated[AShareInstrumentDirectory, Depends(get_a_share_instrument_directory)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = None,
) -> StockPreparation:
    research_date = _research_date_at(as_of, server_time)
    if directory.resolve_at(symbol, server_time) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "a_share_not_found", "message": "未找到该 A 股"},
        )
    live = research_date == server_time.astimezone(ZoneInfo("Asia/Shanghai")).date()
    return await service.prepare(
        symbol, as_of=research_date, cutoff=None if live else server_time
    )


@router.get("/{symbol}/cockpit", response_model=StockCockpitSnapshot)
async def cockpit(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_a_share_cockpit_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
    as_of: date | None = None,
    include_ai: bool = False,
) -> StockCockpitSnapshot:
    try:
        return await service.get(
            symbol, _research_date_at(as_of, server_time), server_time,
            include_ai=include_ai,
        )
    except UnknownAShareError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "a_share_not_found", "message": "未找到该 A 股"},
        ) from error
    except DecisionIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "decision_integrity_error",
                "message": "决策历史完整性校验失败",
            },
        ) from error


@router.get("/{symbol}/company-research", response_model=CompanyResearchResponse)
async def company_research(
    request: Request,
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_company_research_service)],
    as_of: date | None = None,
) -> CompanyResearchResponse:
    selected_date = _research_date(as_of)
    repository = getattr(request.app.state, "company_research_version_repository", None)
    if repository is not None:
        try:
            latest = await asyncio.to_thread(repository.latest, symbol)
        except Exception:
            latest = None
        if latest is not None and latest.as_of <= selected_date:
            _schedule_company_research_refresh(request, service, symbol, selected_date)
            cache_kind = "本地研究缓存" if latest.as_of == selected_date else "历史研究缓存"
            cache_reason = (
                f"已展示{cache_kind}（研究截止日 {latest.as_of.isoformat()}），"
                "后台正在刷新最新真实数据。"
            )
            return latest.model_copy(update={
                "status": latest.status if latest.as_of == selected_date else "partial",
                "reasons": tuple(dict.fromkeys((*latest.reasons, cache_reason))),
            })
    try:
        return await service.get(symbol, selected_date)
    except (OSError, httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "company_research_unavailable",
                "message": "公司研究数据暂不可用，请稍后重试",
            },
        ) from error


def _schedule_company_research_refresh(
    request: Request,
    service: object,
    symbol: str,
    selected_date: date,
) -> None:
    tasks = getattr(request.app.state, "company_research_route_refresh_tasks", None)
    if tasks is None:
        tasks = {}
        request.app.state.company_research_route_refresh_tasks = tasks
    key = (symbol, selected_date)
    existing = tasks.get(key)
    if existing is not None and not existing.done():
        return

    async def refresh() -> None:
        try:
            await service.get(symbol, selected_date, cache_first=False)
        except (OSError, httpx.HTTPError, ValueError):
            return

    task = asyncio.create_task(refresh())
    tasks[key] = task

    def remove(completed: asyncio.Task) -> None:
        tasks.pop(key, None)
        if not completed.cancelled():
            completed.exception()

    task.add_done_callback(remove)


@router.post("/company-research/compare", response_model=ResearchCompareResponse)
async def compare_company_research(
    request: ResearchCompareRequest,
    service: Annotated[object, Depends(get_company_research_service)],
    server_time: Annotated[datetime, Depends(get_server_time)],
) -> ResearchCompareResponse:
    selected_date = _research_date(request.as_of)
    results = await asyncio.gather(
        *(service.get(symbol, selected_date) for symbol in request.symbols),
        return_exceptions=True,
    )
    values = [item for item in results if isinstance(item, CompanyResearchResponse)]
    if not values:
        raise HTTPException(
            status_code=503,
            detail={"code": "research_compare_unavailable", "message": "比较标的的真实公司研究数据均不可用"},
        )
    response = build_research_comparison(
        values, as_of=selected_date, generated_at=server_time
    )
    failures = len(results) - len(values)
    if failures:
        response = response.model_copy(update={
            "status": "partial",
            "limitations": (*response.limitations, f"{failures} 个比较标的数据加载失败"),
        })
    return response


@router.post("/{symbol}/company-research/tasks", response_model=CompanyResearchTaskSnapshot)
async def start_company_research_task(
    symbol: Annotated[AShareCode, Path()],
    service: Annotated[object, Depends(get_company_research_task_service)],
    as_of: date | None = None,
) -> CompanyResearchTaskSnapshot:
    return service.start(symbol, _research_date(as_of))


@router.get("/{symbol}/company-research/versions", response_model=list[CompanyResearchResponse])
async def company_research_versions(
    symbol: Annotated[AShareCode, Path()],
    repository: Annotated[object, Depends(get_company_research_version_repository)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CompanyResearchResponse]:
    try:
        return list(repository.history(symbol, limit=limit))
    except ValueError as error:
        raise HTTPException(status_code=422, detail="公司研究版本查询参数无效") from error


@router.get("/company-research/tasks/{task_id}", response_model=CompanyResearchTaskSnapshot)
async def company_research_task(
    task_id: str,
    service: Annotated[object, Depends(get_company_research_task_service)],
) -> CompanyResearchTaskSnapshot:
    snapshot = service.snapshot(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="公司研究任务不存在或已过期")
    return snapshot


@router.post("/company-research/versions/{snapshot_id}/ai/tasks", response_model=CompanyResearchAITaskSnapshot)
async def start_company_research_ai_task(
    snapshot_id: str,
    service: Annotated[object, Depends(get_company_research_ai_task_service)],
) -> CompanyResearchAITaskSnapshot:
    return service.start(snapshot_id)


@router.get("/company-research/ai/tasks/{task_id}", response_model=CompanyResearchAITaskSnapshot)
async def company_research_ai_task(
    task_id: str,
    service: Annotated[object, Depends(get_company_research_ai_task_service)],
) -> CompanyResearchAITaskSnapshot:
    snapshot = service.snapshot(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="公司研究 AI 任务不存在或已过期")
    return snapshot

@router.get("/{symbol}/snapshot", response_model=ResearchCard)
async def snapshot(
    symbol: Annotated[AShareCode, Path()],
    pipeline: Annotated[ResearchPipeline, Depends(get_pipeline)],
) -> ResearchCard:
    try:
        return await pipeline.run(symbol)
    except SourceAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "source_authorization_required",
                "message": "请先在礼部完成腾讯行情授权并确认免责声明",
            },
        ) from error
