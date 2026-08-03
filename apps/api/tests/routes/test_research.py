import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3

import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.contracts.market import AssetKind, DataQuality
from qibao_api.contracts.research import Evidence, ResearchCard
from qibao_api.a_shares.diagnosis import (
    AShareDiagnosis,
    AShareDiagnosisService,
    DiagnosisSection,
    DiagnosisUnavailableError,
)
from qibao_api.a_shares.models import (
    CandidateBoard,
    CandidateScoreBoard,
    CandidateScoreItem,
)
from qibao_api.a_shares.fundamentals import FundamentalSnapshot
from qibao_api.a_shares.instrument_directory import AShareInstrument, AShareInstrumentDirectory
from qibao_api.a_shares.repository import AShareResearchRepository, AShareResearchStoreError
from qibao_api.a_shares.candidate_sentiment_repository import CandidateSentimentStoreError
from qibao_api.a_shares.candidate_sentiment_service import (
    CandidateSentimentInputError,
    CandidateSnapshotNotFoundError,
)
from qibao_api.dependencies import (
    get_a_share_cockpit_service,
    get_a_share_diagnosis_service,
    get_a_share_instrument_directory,
    get_a_share_preparation_service,
    get_a_share_quote_source,
    get_candidate_sentiment_service,
    get_pipeline,
    get_server_time,
    get_stock_timeline_service,
)
from qibao_api.a_shares.cockpit import StockDecisionCockpitService, UnknownAShareError
from qibao_api.a_shares.preparation import AStockPreparationService, PreparationSource, StockPreparation
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.decision import (
    AdviceCard,
    DecisionCycleAggregate,
    DecisionCycleSnapshot,
    EvidenceReference,
)
from qibao_api.shangshu.decision_repository import DecisionIntegrityError
from qibao_api.main import app, serialize_runtime_access
from qibao_api.gongbu.data_service import MarketDataService
from qibao_api.gongbu.news_repository import NewsRepository
from qibao_api.storage.bar_repository import BarRepository
from qibao_api.shangshu.decision_repository import DecisionRepository
from qibao_api.contracts.news import EvidenceCitation, NewsArticle, NormalizedNewsEvent
from qibao_api.contracts.stock_timeline import StockTimelineResponse
from qibao_api.contracts.candidate_sentiment import (
    CandidateSentimentBatch,
    CandidateSentimentComponent,
    CandidateSentimentSnapshot,
)
from qibao_api.gongbu.tencent_quotes import TencentMarketSnapshot, parse_tencent_quote
from qibao_api.gongbu.market_feed import MarketFeedSnapshot
from qibao_api.routes.research import router as research_router
from qibao_api.libu_compliance.repository import SourceAuthorizationError


class FakePipeline:
    async def run(self, symbol: str) -> ResearchCard:
        return ResearchCard(
            symbol=symbol,
            asset=AssetKind.A_SHARE,
            action="observe",
            change_percent=Decimal("1.49"),
            quality=DataQuality.FRESH,
            evidence=[
                Evidence(
                    label="最新价",
                    value="10.25",
                    source="tencent",
                    observed_at=datetime(2026, 7, 13, 10, 30),
                )
            ],
        )


class UnexpectedPipeline:
    async def run(self, symbol: str) -> ResearchCard:
        raise AssertionError(f"pipeline must not receive invalid A-share code {symbol}")


SENTIMENT_CUTOFF = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)


def candidate_sentiment_batch(*, partial: bool = False) -> CandidateSentimentBatch:
    components = (
        CandidateSentimentComponent(
            name="news",
            status="unavailable" if partial else "ready",
            score=None if partial else Decimal("65"),
            weight=Decimal("40"),
            summary="新闻数据不可用" if partial else "新闻偏积极",
            observed_at=None if partial else SENTIMENT_CUTOFF,
            evidence_ids=() if partial else ("news-1",),
        ),
        CandidateSentimentComponent(
            name="hotspot", status="ready", score=Decimal("65"),
            weight=Decimal("30"), summary="热点可用",
            observed_at=SENTIMENT_CUTOFF, evidence_ids=("hotspot-1",),
        ),
        CandidateSentimentComponent(
            name="fund_flow", status="ready", score=Decimal("65"),
            weight=Decimal("30"), summary="资金可用",
            observed_at=SENTIMENT_CUTOFF, evidence_ids=("fund-1",),
        ),
    )
    item = CandidateSentimentSnapshot(
        candidate_snapshot_id="candidate-1",
        candidate_input_hash="a" * 64,
        symbol="600000",
        quality="partial" if partial else "ready",
        freshness="current",
        score=Decimal("65"),
        band="positive",
        coverage_percent=Decimal("60" if partial else "100"),
        components=components,
        primary_reason="热点与资金偏积极。",
        primary_risk="部分分项不可用。" if partial else "情绪可能快速变化。",
        beginner_guidance="继续观察。",
        observed_at=SENTIMENT_CUTOFF,
        generated_at=SENTIMENT_CUTOFF,
        source_snapshot_ids=("hotspot-1", "fund-1") if partial else (
            "news-1", "hotspot-1", "fund-1",
        ),
    )
    return CandidateSentimentBatch(
        candidate_snapshot_id="candidate-1",
        candidate_input_hash="a" * 64,
        as_of=date(2026, 7, 18),
        cutoff=SENTIMENT_CUTOFF,
        quality="partial" if partial else "ready",
        items=(item,),
        generated_at=SENTIMENT_CUTOFF,
    )


class FakeCandidateSentimentService:
    def __init__(
        self,
        result: CandidateSentimentBatch | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or candidate_sentiment_batch()
        self.error = error
        self.current_calls: list[tuple[str, datetime]] = []
        self.refresh_calls: list[tuple[str, datetime]] = []

    def current(self, snapshot_id: str, cutoff: datetime) -> CandidateSentimentBatch:
        self.current_calls.append((snapshot_id, cutoff))
        if self.error is not None:
            raise self.error
        return self.result

    async def refresh(
        self, snapshot_id: str, cutoff: datetime
    ) -> CandidateSentimentBatch:
        self.refresh_calls.append((snapshot_id, cutoff))
        if self.error is not None:
            raise self.error
        return self.result


def candidate_sentiment_client(service: FakeCandidateSentimentService) -> TestClient:
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_candidate_sentiment_service] = lambda: service
    application.dependency_overrides[get_server_time] = lambda: SENTIMENT_CUTOFF
    return TestClient(application)


def test_candidate_sentiment_current_and_refresh_return_candidate_order() -> None:
    service = FakeCandidateSentimentService(candidate_sentiment_batch(partial=True))
    with candidate_sentiment_client(service) as client:
        current = client.post(
            "/api/v1/a-shares/candidate-sentiment/batch",
            json={"candidate_snapshot_id": "candidate-1"},
        )
        refreshed = client.post(
            "/api/v1/a-shares/candidate-sentiment/batch/refresh",
            json={"candidate_snapshot_id": "candidate-1"},
        )

    assert current.status_code == 200
    assert refreshed.status_code == 200
    assert [item["symbol"] for item in current.json()["items"]] == ["600000"]
    assert current.json()["quality"] == "partial"
    assert service.current_calls == [("candidate-1", SENTIMENT_CUTOFF)]
    assert service.refresh_calls == [("candidate-1", SENTIMENT_CUTOFF)]


@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (CandidateSnapshotNotFoundError("missing"), 404, "candidate_snapshot_not_found"),
        (CandidateSentimentInputError("conflict"), 422, "candidate_sentiment_input_invalid"),
        (
            CandidateSentimentStoreError("sqlite:///secret-token"),
            503,
            "candidate_sentiment_store_error",
        ),
    ],
)
def test_candidate_sentiment_routes_map_errors_without_internal_details(
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    with candidate_sentiment_client(FakeCandidateSentimentService(error=error)) as client:
        response = client.post(
            "/api/v1/a-shares/candidate-sentiment/batch",
            json={"candidate_snapshot_id": "candidate-1"},
        )

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == error_code
    assert "secret-token" not in response.text


def make_client() -> TestClient:
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline()
    return TestClient(app)


def test_a_share_snapshot_returns_evidence() -> None:
    with make_client() as client:
        response = client.get("/api/v1/a-shares/600000/snapshot")

    assert response.status_code == 200
    assert response.json()["symbol"] == "600000"
    assert response.json()["evidence"][0]["source"] == "tencent"


@pytest.mark.parametrize("symbol", ["113001", "123001"])
def test_convertible_bond_is_not_routed_through_a_share_endpoint(symbol: str) -> None:
    app.dependency_overrides[get_pipeline] = lambda: UnexpectedPipeline()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/a-shares/{symbol}/snapshot")

    assert response.status_code == 422


def test_beijing_stock_exchange_code_reaches_a_share_snapshot() -> None:
    with make_client() as client:
        response = client.get("/api/v1/a-shares/920001/snapshot")

    assert response.status_code == 200
    assert response.json()["symbol"] == "920001"


def test_health_endpoint_reports_ready() -> None:
    with make_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


class BlockedPipeline:
    async def run(self, symbol: str) -> ResearchCard:
        raise SourceAuthorizationError("tencent:missing")


def test_snapshot_explains_missing_compliance_authorization() -> None:
    app.dependency_overrides[get_pipeline] = lambda: BlockedPipeline()
    with TestClient(app) as client:
        response = client.get("/api/v1/a-shares/600000/snapshot")

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "source_authorization_required",
            "message": "请先在礼部完成腾讯行情授权并确认免责声明",
        }
    }


class FakeDiagnosisService:
    def candidates(self, as_of: date, limit: int) -> CandidateBoard:
        return CandidateBoard(as_of=as_of, short_term=[], swing=[])

    def candidate_scores(self, as_of, symbols, *, horizon):
        return CandidateScoreBoard(
            as_of=as_of,
            horizon=horizon,
            universe_size=8,
            eligible_size=7,
            latest_trade_date=as_of,
            sources=("baidu",),
            items=tuple(
                CandidateScoreItem(
                    symbol=symbol,
                    status="ready",
                    score=Decimal("42"),
                    latest_trade_date=as_of,
                )
                for symbol in symbols
            ),
        )

    async def diagnose(self, symbol: str, as_of: date) -> AShareDiagnosis:
        sections = {
            name: DiagnosisSection(
                status="ready", observed_at=as_of, source="fixture",
                metrics={}, explanation="测试诊断分区",
            )
            for name in (
                "market", "price_volume", "trend", "valuation", "fundamentals",
                "funds", "events", "industry", "risk",
            )
        }
        return AShareDiagnosis(
            symbol=symbol, as_of=as_of, action="observe", overall_status="ready",
            sections=sections,
        )


class UnavailableDiagnosisService(FakeDiagnosisService):
    async def diagnose(self, symbol: str, as_of: date) -> AShareDiagnosis:
        raise DiagnosisUnavailableError("market and local history are unavailable")


class UnauthorizedDiagnosisService(FakeDiagnosisService):
    async def diagnose(self, symbol: str, as_of: date) -> AShareDiagnosis:
        raise SourceAuthorizationError("tencent:missing")


class CorruptResearchService(FakeDiagnosisService):
    def candidates(self, as_of: date, limit: int) -> CandidateBoard:
        raise AShareResearchStoreError("database malformed")


def diagnosis_client(service=None) -> TestClient:
    app.dependency_overrides[get_a_share_diagnosis_service] = lambda: (
        service or FakeDiagnosisService()
    )
    return TestClient(app)


def test_a_share_candidates_return_separate_empty_boards() -> None:
    with diagnosis_client() as client:
        response = client.get("/api/v1/a-shares/candidates?as_of=2026-07-14&limit=20")

    assert response.status_code == 200
    assert response.json()["asset"] == "a_share"
    assert response.json()["as_of"] == "2026-07-14"
    assert response.json()["short_term"] == []
    assert response.json()["swing"] == []
    assert response.json()["factor_version"] == "a-share-factors-v1"
    assert response.json()["universe_status"] == "empty"


def test_a_share_candidate_scores_preserve_requested_watchlist_order() -> None:
    client = diagnosis_client()
    try:
        response = client.get(
            "/api/v1/a-shares/candidate-scores"
            "?symbols=600000&symbols=000001&horizon=short_term&as_of=2026-07-14"
        )
    finally:
        client.close()

    assert response.status_code == 200
    assert response.json()["universe_size"] == 8
    assert response.json()["eligible_size"] == 7
    assert response.json()["sources"] == ["baidu"]
    assert [item["symbol"] for item in response.json()["items"]] == [
        "600000", "000001",
    ]


def test_a_share_diagnosis_returns_all_nine_sections() -> None:
    with diagnosis_client() as client:
        response = client.get("/api/v1/a-shares/600000/diagnosis?as_of=2026-07-14")

    assert response.status_code == 200
    assert response.json()["asset"] == "a_share"
    assert set(response.json()["sections"]) == {
        "market", "price_volume", "trend", "valuation", "fundamentals",
        "funds", "events", "industry", "risk",
    }


def test_convertible_bond_never_reaches_a_share_diagnosis() -> None:
    with diagnosis_client() as client:
        response = client.get("/api/v1/a-shares/113001/diagnosis")

    assert response.status_code == 422


def test_a_share_diagnosis_maps_missing_core_data_to_503() -> None:
    with diagnosis_client(UnavailableDiagnosisService()) as client:
        response = client.get("/api/v1/a-shares/600000/diagnosis?as_of=2026-07-14")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "a_share_diagnosis_unavailable"


def test_a_share_diagnosis_keeps_compliance_denial_explicit() -> None:
    with diagnosis_client(UnauthorizedDiagnosisService()) as client:
        response = client.get("/api/v1/a-shares/600000/diagnosis?as_of=2026-07-14")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "source_authorization_required"


def test_a_share_store_corruption_maps_to_503() -> None:
    with diagnosis_client(CorruptResearchService()) as client:
        response = client.get("/api/v1/a-shares/candidates?as_of=2026-07-14")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "a_share_research_store_error"


def test_future_research_cutoff_is_rejected() -> None:
    with diagnosis_client() as client:
        response = client.get("/api/v1/a-shares/candidates?as_of=2999-01-01")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "future_as_of_not_allowed"


class PreparationDirectory:
    def resolve_at(self, symbol, cutoff):
        return object() if symbol == "600519" else None


class PreparationService:
    def __init__(self) -> None:
        self.calls = []

    async def prepare(self, symbol, *, as_of, cutoff=None):
        self.calls.append((symbol, as_of, cutoff))
        return StockPreparation(
            symbol=symbol, status="ready", refreshed=False,
            started_at=SEARCH_NOW, completed_at=SEARCH_NOW,
            sources=tuple(
                PreparationSource(name=name, status="ready")
                for name in ("quote", "history", "finance", "news")
            ),
        )

    async def inspect(self, symbol, *, as_of, cutoff=None):
        return await self.prepare(symbol, as_of=as_of, cutoff=cutoff)


def preparation_client(service):
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_a_share_preparation_service] = lambda: service
    application.dependency_overrides[get_a_share_instrument_directory] = lambda: PreparationDirectory()
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW
    return TestClient(application)


def test_prepare_returns_typed_result_for_verified_symbol() -> None:
    service = PreparationService()
    response = preparation_client(service).post(
        "/api/v1/a-shares/600519/prepare?as_of=2026-07-15"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert service.calls == [("600519", date(2026, 7, 15), None)]


def test_prepare_returns_404_without_calling_sources_for_unknown_symbol() -> None:
    service = PreparationService()
    response = preparation_client(service).post("/api/v1/a-shares/600999/prepare")

    assert response.status_code == 404
    assert service.calls == []


class ConcurrentPreparation(PreparationService):
    def __init__(self):
        super().__init__()
        self.active = 0
        self.maximum = 0

    async def prepare(self, symbol, *, as_of, cutoff=None):
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0.03)
        try:
            return await super().prepare(symbol, as_of=as_of, cutoff=cutoff)
        finally:
            self.active -= 1


@pytest.mark.asyncio
async def test_prepare_posts_are_serialized_by_runtime_middleware() -> None:
    service = ConcurrentPreparation()
    application = FastAPI()
    application.middleware("http")(serialize_runtime_access)
    application.include_router(research_router)
    application.state.write_gate = asyncio.Lock()
    application.dependency_overrides[get_a_share_preparation_service] = lambda: service
    application.dependency_overrides[get_a_share_instrument_directory] = lambda: PreparationDirectory()
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(*(
            client.post("/api/v1/a-shares/600519/prepare") for _ in range(3)
        ))

    assert all(response.status_code == 200 for response in responses)
    assert service.maximum == 1


@pytest.mark.asyncio
async def test_local_data_source_settings_read_does_not_wait_for_runtime_write() -> None:
    application = FastAPI()
    application.middleware("http")(serialize_runtime_access)
    application.state.write_gate = asyncio.Lock()

    @application.get("/api/v1/settings/data-sources")
    async def local_sources():
        return {"status": "ready"}

    await application.state.write_gate.acquire()
    transport = httpx.ASGITransport(app=application)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await asyncio.wait_for(
                client.get("/api/v1/settings/data-sources"),
                timeout=0.2,
            )
    finally:
        application.state.write_gate.release()

    assert response.status_code == 200


SEARCH_NOW = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


class IntradayTickRepository:
    def __init__(self) -> None:
        self.calls = []

    def intraday_snapshots(self, symbol, trading_date, *, cutoff):
        self.calls.append((symbol, trading_date, cutoff))
        return (
            MarketFeedSnapshot(
                symbol=symbol, price=Decimal("10.12"), change=Decimal("0.12"),
                change_percent=Decimal("1.2"), volume=Decimal("123400"),
                source="fixture-feed", observed_at=SEARCH_NOW,
                fetched_at=SEARCH_NOW, quality="ready",
                source_snapshot_id="tick-600000-1",
            ),
        )


def test_intraday_ticks_return_archived_points_for_requested_beijing_date() -> None:
    repository = IntradayTickRepository()
    application = FastAPI()
    application.include_router(research_router)
    application.state.poll_state_repository = repository
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW

    response = TestClient(application).get(
        "/api/v1/a-shares/600000/intraday-ticks?trading_date=2026-07-15"
    )

    assert response.status_code == 200
    assert response.json()[0]["source_snapshot_id"] == "tick-600000-1"
    assert response.json()[0]["price"] == "10.12"
    assert repository.calls == [("600000", date(2026, 7, 15), SEARCH_NOW)]


class TimelineService:
    def __init__(self) -> None:
        self.calls = []

    def get(self, symbol, as_of, cutoff):
        self.calls.append((symbol, as_of, cutoff))
        return StockTimelineResponse(
            symbol=symbol,
            as_of=as_of,
            cutoff=cutoff,
            status="ready",
            bars=(DailyBar(
                symbol=symbol,
                trade_date=as_of,
                open=Decimal("10"),
                high=Decimal("10.5"),
                low=Decimal("9.8"),
                close=Decimal("10.2"),
                volume=100,
                amount=Decimal("1020"),
                source="local-daily-bars",
            ),),
            events=(),
            sources=("local-daily-bars", "verified-market-news"),
        )


def test_stock_timeline_delegates_to_local_read_only_service() -> None:
    service = TimelineService()
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_stock_timeline_service] = lambda: service
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW

    response = TestClient(application).get(
        "/api/v1/a-shares/600000/timeline?as_of=2026-07-15"
    )

    assert response.status_code == 200
    assert response.json()["bars"][0]["close"] == "10.2"
    assert response.json()["events"] == []
    assert service.calls == [("600000", date(2026, 7, 15), SEARCH_NOW)]


class SearchDirectory:
    def __init__(self) -> None:
        self.items = {
            "000001": AShareInstrument(
                symbol="000001", name="平安银行", exchange="sz",
                observed_at=SEARCH_NOW, quote_quality="ready",
            ),
            "600000": AShareInstrument(
                symbol="600000", name="浦发银行", exchange="sh",
                observed_at=SEARCH_NOW, quote_quality="ready",
            ),
        }

    def search(self, query: str, limit: int = 10):
        normalized = query.strip().casefold()
        matches = [
            item for item in self.items.values()
            if normalized in item.symbol or normalized in item.name.casefold()
        ]
        return tuple(sorted(matches, key=lambda item: item.symbol)[:limit])

    def resolve(self, symbol: str):
        return self.items.get(symbol)

    def observe(self, item: AShareInstrument) -> None:
        self.items[item.symbol] = item


class NeverQuoteSource:
    async def fetch(self, symbol: str):
        request = httpx.Request("GET", "https://qt.gtimg.cn")
        raise httpx.ConnectError(f"unavailable {symbol}", request=request)


class FailIfCalledQuoteSource:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def fetch(self, symbol: str):
        self.calls.append(symbol)
        raise AssertionError("named local instruments must not wait for a remote quote")


class QuoteSource:
    async def fetch(self, symbol: str):
        return type("Quote", (), {
            "symbol": symbol,
            "name": "邯郸钢铁",
            "observed_at": datetime(2026, 7, 15, 10, 1),
            "quality": DataQuality.FRESH,
        })()


class MismatchedQuoteSource:
    async def fetch(self, symbol: str):
        return type("Quote", (), {
            "symbol": "600002",
            "name": "错误标的",
            "observed_at": SEARCH_NOW,
            "quality": DataQuality.FRESH,
        })()


class ProgrammingErrorQuoteSource:
    async def fetch(self, symbol: str):
        raise sqlite3.ProgrammingError("closed database")


class MalformedNumericQuoteSource:
    async def fetch(self, symbol: str):
        fields = [""] * 50
        fields[1:5] = ["坏行情", symbol, "not-a-number", "10.00"]
        fields[30] = "20260715100100"
        return parse_tencent_quote("~".join(fields), source="tencent")


def search_client(directory=None, source=None) -> TestClient:
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_a_share_instrument_directory] = lambda: (
        directory or SearchDirectory()
    )
    application.dependency_overrides[get_a_share_quote_source] = lambda: (
        source or NeverQuoteSource()
    )
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW
    return TestClient(application)


def test_search_returns_only_a_shares_in_rank_order() -> None:
    response = search_client().get("/api/v1/a-shares/search?q=银行&limit=10")

    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()["items"]] == ["000001", "600000"]
    assert all(item["asset"] == "a_share" for item in response.json()["items"])
    assert response.json()["query"] == "银行"
    assert response.json()["server_time"] == "2026-07-15T02:00:00Z"


def test_search_returns_empty_items_without_guessing() -> None:
    response = search_client().get("/api/v1/a-shares/search?q=不存在名称")

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.parametrize("query", ["", "   "])
def test_search_rejects_empty_query(query: str) -> None:
    response = search_client().get("/api/v1/a-shares/search", params={"q": query})

    assert response.status_code == 422


def test_exact_code_source_failure_returns_unavailable_instead_of_500() -> None:
    response = search_client(directory=SearchDirectory()).get(
        "/api/v1/a-shares/search?q=600001"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["source_status"] == "unavailable"


def test_code_only_local_observation_still_requires_quote_verification() -> None:
    directory = SearchDirectory()
    directory.items["600001"] = AShareInstrument(
        symbol="600001", name="600001", exchange="sh",
        observed_at=SEARCH_NOW, quote_quality="unavailable",
    )

    response = search_client(directory=directory).get(
        "/api/v1/a-shares/search?q=600001"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["source_status"] == "unavailable"


def test_exact_code_is_verified_and_observed() -> None:
    directory = SearchDirectory()
    response = search_client(directory=directory, source=QuoteSource()).get(
        "/api/v1/a-shares/search?q=600001"
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["symbol"] == "600001"
    assert response.json()["items"][0]["name"] == "邯郸钢铁"
    assert directory.resolve("600001") is not None


def test_exact_code_returns_named_local_instrument_without_remote_quote() -> None:
    directory = SearchDirectory()
    source = FailIfCalledQuoteSource()

    response = search_client(directory=directory, source=source).get(
        "/api/v1/a-shares/search?q=600000"
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["symbol"] == "600000"
    assert response.json()["items"][0]["name"] == "浦发银行"
    assert response.json()["items"][0]["quote_quality"] == "ready"
    assert source.calls == []


def test_exact_code_rejects_mismatched_upstream_symbol() -> None:
    directory = SearchDirectory()
    response = search_client(directory=directory, source=MismatchedQuoteSource()).get(
        "/api/v1/a-shares/search?q=600001"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["source_status"] == "unavailable"
    assert directory.resolve("600002") is None


def test_exact_code_does_not_hide_programming_or_storage_errors() -> None:
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        search_client(source=ProgrammingErrorQuoteSource()).get(
            "/api/v1/a-shares/search?q=600001"
        )


def test_exact_code_maps_malformed_tencent_numeric_payload_to_unavailable() -> None:
    response = search_client(source=MalformedNumericQuoteSource()).get(
        "/api/v1/a-shares/search?q=600001"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["source_status"] == "unavailable"


class UnknownCockpit:
    async def get(self, symbol, as_of, cutoff, *, include_ai=True):
        raise UnknownAShareError(symbol)


class CorruptCockpit:
    async def get(self, symbol, as_of, cutoff, *, include_ai=True):
        raise DecisionIntegrityError("corrupt advice payload containing secret advice")


def cockpit_client(service, preparation_service=None) -> TestClient:
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_a_share_cockpit_service] = lambda: service
    if preparation_service is not None:
        application.dependency_overrides[get_a_share_preparation_service] = (
            lambda: preparation_service
        )
        application.dependency_overrides[get_a_share_instrument_directory] = (
            lambda: AcceptanceCockpitDirectory()
        )
    application.dependency_overrides[get_server_time] = lambda: SEARCH_NOW
    return TestClient(application)


def test_cockpit_maps_invalid_and_unknown_symbol() -> None:
    client = cockpit_client(UnknownCockpit())
    assert client.get("/api/v1/a-shares/123/cockpit").status_code == 422
    assert client.get("/api/v1/a-shares/600999/cockpit").status_code == 404


def test_cockpit_hides_corrupt_decision_payload() -> None:
    response = cockpit_client(CorruptCockpit()).get(
        "/api/v1/a-shares/600000/cockpit"
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "decision_integrity_error"
    assert "advice" not in response.text


def test_cockpit_rejects_future_as_of_using_server_beijing_time() -> None:
    response = cockpit_client(UnknownCockpit()).get(
        "/api/v1/a-shares/600000/cockpit?as_of=2026-07-16"
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "future_as_of_not_allowed"


COCKPIT_CUTOFF = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)
COCKPIT_DATE = date(2026, 7, 15)


class AcceptanceCockpitDirectory:
    def resolve_at(self, symbol, cutoff):
        assert cutoff == COCKPIT_CUTOFF
        names = {"600000": "浦发银行", "600519": "贵州茅台", "000001": "平安银行"}
        if symbol not in names:
            return None
        return AShareInstrument(
            symbol=symbol, name=names[symbol],
            exchange="sz" if symbol.startswith("0") else "sh",
            observed_at=cutoff, quote_quality="ready",
        )


class AcceptanceCockpitDiagnosis:
    async def diagnose(self, symbol, as_of, *, persist=True):
        assert persist is False
        sections = {
            name: DiagnosisSection(
                status="ready", observed_at=COCKPIT_CUTOFF, source="fixture",
                metrics={"symbol": symbol}, explanation="fixture",
            )
            for name in (
                "market", "price_volume", "trend", "valuation", "fundamentals",
                "funds", "events", "industry", "risk",
            )
        }
        if symbol == "600519":
            sections["trend"] = DiagnosisSection(
                status="unavailable", observed_at=None, source="fixture-history",
                metrics={}, explanation="history unavailable",
            )
        if symbol == "000001":
            sections["events"] = DiagnosisSection(
                status="ready", observed_at=COCKPIT_CUTOFF,
                source="frozen-news-events",
                metrics={"event_count": 1, "adverse_event_count": 1},
                evidence_ids=("verified-adverse-event",), explanation="fixture",
            )
        return AShareDiagnosis(
            symbol=symbol, as_of=as_of, action="observe", overall_status="ready",
            sections=sections,
        )


def acceptance_advice():
    evidence = EvidenceReference(
        evidence_id="e-600000", source="fixture", snapshot_id="source-1",
        summary="fixture", observed_at=COCKPIT_CUTOFF,
    )
    return AdviceCard(
        advice_id="a-600000", snapshot_id="cycle-1", asset=AssetKind.A_SHARE,
        symbol="600000", horizon="intraday", observation_state="watch",
        action="observe", conclusion="observe", confidence=Decimal("0.5"),
        supporting_evidence=(evidence,), contrary_evidence=(), risks=("risk",),
        invalidation_conditions=("invalid",), quantitative_result={},
        strategy_version="v1", created_at=COCKPIT_CUTOFF,
        risk_decision_id="risk-1",
    )


class AcceptanceCockpitDecisions:
    def cycles(self, trading_date=None, phase=None):
        if phase != "intraday":
            return []
        snapshot = DecisionCycleSnapshot(
            snapshot_id="cycle-1", trading_date=COCKPIT_DATE, phase="intraday",
            sequence=1, generated_at=COCKPIT_CUTOFF,
            window_start=COCKPIT_CUTOFF - timedelta(minutes=1),
            window_end=COCKPIT_CUTOFF,
            market_state="range", data_quality="ready", source_snapshot_ids=("source-1",),
            source_observed_at=(COCKPIT_CUTOFF,), candidate_snapshot_id=None,
            news_event_ids=(), risk_event_ids=(), input_snapshot_hash="1" * 64,
            previous_snapshot_id=None, status="ready", ai_status="not_requested",
        )
        return [
            DecisionCycleAggregate(
                snapshot=snapshot, advice=(acceptance_advice(),),
            )
        ]


class IntegrationHistorySource:
    def fetch_daily(self, symbol, limit):
        count = 20 if symbol == "600519" else 80
        start = date(2026, 7, 14) - timedelta(days=count - 1)
        return [DailyBar(
            symbol=symbol, trade_date=start + timedelta(days=index),
            open=Decimal("10"), high=Decimal("10.2"), low=Decimal("9.8"),
            close=Decimal("10.1"), volume=1_000_000 + index,
            amount=Decimal("10100000"), source="fixture-history",
        ) for index in range(count)]


class IntegrationMarketSource:
    async def fetch_snapshot(self, symbol):
        return TencentMarketSnapshot(
            symbol=symbol, name="测试股票", observed_at=COCKPIT_CUTOFF,
            price=Decimal("10.1"), previous_close=Decimal("10"),
            turnover_rate=Decimal("1"), pe_ttm=Decimal("10"),
            market_cap_yi=Decimal("100"), pb=Decimal("1"),
            source="fixture-quote",
        )


class IntegrationFinanceSource:
    def fetch(self, symbol):
        return FundamentalSnapshot(
            symbol=symbol, observed_at=COCKPIT_CUTOFF,
            report_period=COCKPIT_DATE, industry="银行", eps=Decimal("1"),
            source="fixture-finance",
        )


class IntegrationNewsCollector:
    def __init__(self, repository):
        self.repository = repository

    async def sync(self):
        raw = b"verified adverse event"
        content_hash = hashlib.sha256(raw).hexdigest()
        article = NewsArticle(
            article_id="article-adverse-000001",
            canonical_url="https://news.example/adverse-000001",
            publisher="测试来源", title="已核验风险事件",
            published_at=COCKPIT_CUTOFF, fetched_at=COCKPIT_CUTOFF,
            content_hash=content_hash, raw_snapshot=raw, source_verified=True,
        )
        self.repository.append_articles((article,))
        self.repository.append_event(NormalizedNewsEvent(
            event_id="verified-adverse-000001", event_type="credit_risk",
            headline="已核验风险事件", occurred_at=COCKPIT_CUTOFF,
            normalized_at=COCKPIT_CUTOFF,
            affected_instruments=((AssetKind.A_SHARE, "000001"),),
            industries=("银行",), themes=("风险事件",), citations=(EvidenceCitation(
                citation_id="citation-adverse-000001", article_id=article.article_id,
                canonical_url=article.canonical_url, publisher=article.publisher,
                published_at=article.published_at, quoted_text=article.title,
                content_hash=article.content_hash,
            ),),
            association_confidence=Decimal("1"), review_state="verified",
        ))


class IntegrationCalendar:
    def is_trading_day(self, value):
        return True

    def previous_trading_day(self, value):
        return value - timedelta(days=1)


def test_prepare_then_cockpit_covers_observe_wait_and_avoid_without_legacy_products(tmp_path) -> None:
    bars = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    news = NewsRepository(tmp_path / "news.sqlite3")
    research = AShareResearchRepository(tmp_path / "research.sqlite3")
    directory = AShareInstrumentDirectory(tmp_path / "instruments.sqlite3")
    for symbol, name in (("600000", "浦发银行"), ("600519", "贵州茅台"), ("000001", "平安银行")):
        directory.observe(AShareInstrument(
            symbol=symbol, name=name, exchange="sz" if symbol.startswith("0") else "sh",
            observed_at=COCKPIT_CUTOFF, quote_quality="ready",
        ))
    diagnosis = AShareDiagnosisService(
        bars, IntegrationMarketSource(), IntegrationFinanceSource(), news,
        research_repository=research, clock=lambda: COCKPIT_CUTOFF,
    )
    preparation = AStockPreparationService(
        bars, MarketDataService(IntegrationHistorySource(), bars), diagnosis,
        IntegrationNewsCollector(news), news, IntegrationCalendar(),
        lock_dir=tmp_path / "locks", clock=lambda: COCKPIT_CUTOFF,
    )
    service = StockDecisionCockpitService(
        directory, diagnosis, DecisionRepository(tmp_path / "decisions.sqlite3"), preparation,
        clock=lambda: COCKPIT_CUTOFF,
    )
    application = FastAPI()
    application.include_router(research_router)
    application.dependency_overrides[get_a_share_cockpit_service] = lambda: service
    application.dependency_overrides[get_a_share_preparation_service] = lambda: preparation
    application.dependency_overrides[get_a_share_instrument_directory] = lambda: directory
    application.dependency_overrides[get_server_time] = lambda: COCKPIT_CUTOFF
    client = TestClient(application)

    payloads = {}
    for symbol in ("600000", "600519", "000001"):
        prepared = client.post(f"/api/v1/a-shares/{symbol}/prepare")
        assert prepared.status_code == 200
        assert prepared.json()["refreshed"] is True, prepared.json()
        assert {item["name"]: item["status"] for item in prepared.json()["sources"]}["history"] == (
            "partial" if symbol == "600519" else "ready"
        )
        response = client.get(f"/api/v1/a-shares/{symbol}/cockpit")
        assert response.status_code == 200
        payloads[symbol] = response.json()

    assert all(payload["assessment"]["symbol"] == symbol for symbol, payload in payloads.items())
    assert all(payload["ai_status"] == "unconfigured" for payload in payloads.values())
    assert all(payload["ai_explanation"] is None for payload in payloads.values())
    assert payloads["600000"]["assessment"]["action"] == "observe"
    assert payloads["600519"]["assessment"]["action"] == "wait"
    assert payloads["000001"]["assessment"]["action"] == "avoid"
    assert all(payload["current_advice"] == [] for payload in payloads.values())
    assert len(bars.latest_many(["600000"], 120, COCKPIT_DATE)["600000"]) == 80
    assert news.events_for_symbol("000001")
    serialized = json.dumps(payloads, ensure_ascii=False).casefold()
    assert all(term not in serialized for term in (
        "paper_account", "paper_order", "simulation_plan", "api_key",
    ))
    for symbol in ("600519", "000001"):
        payload = payloads[symbol]
        assert payload["current_advice"] == []

    openapi = app.openapi()
    openapi_paths = " ".join(openapi["paths"]).casefold()
    openapi_schemas = json.dumps(openapi["components"]["schemas"], ensure_ascii=False).casefold()
    assert all(term not in openapi_paths for term in (
        "paper", "order", "simulation", "api-key", "api_key",
    ))
    assert all(term not in openapi_schemas for term in (
        "paper_account", "paper_order", "simulation_plan", "api_secret", "secret_key",
    ))
