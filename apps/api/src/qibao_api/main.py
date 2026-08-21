import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Request

from qibao_api.a_shares.diagnosis import AShareDiagnosisService
from qibao_api.a_shares.cockpit import StockDecisionCockpitService
from qibao_api.a_shares.assessment_ai import ReloadableAssessmentGateway
from qibao_api.a_shares.fundamentals import TdxFinanceSource
from qibao_api.a_shares.instrument_directory import AShareInstrument, AShareInstrumentDirectory
from qibao_api.a_shares.market_sentiment import (
    MarketSentimentFactorBuilder,
    MarketSentimentEvaluator,
    MarketSentimentService,
    MarketSentimentWrongPhase,
)
from qibao_api.a_shares.market_sentiment_repository import (
    MarketSentimentRepository,
)
from qibao_api.a_shares.market_overview import MarketOverviewService
from qibao_api.a_shares.quant_strategy import (
    ArchivedTriggerEvidenceSource,
    QuantStrategyService,
)
from qibao_api.a_shares.late_session_selection_service import LateSessionSelectionService
from qibao_api.a_shares.quant_strategy_snapshot import QuantStrategySnapshotStore
from qibao_api.a_shares.quant_shadow_ledger import QuantShadowLedgerStore
from qibao_api.a_shares.quant_research_intelligence import (
    QuantResearchIntelligenceService,
)
from qibao_api.a_shares.quant_research_snapshot import QuantResearchSnapshotStore
from qibao_api.a_shares.factor_hypotheses import FactorHypothesisStore
from qibao_api.a_shares.decision_journal import DecisionJournalStore
from qibao_api.a_shares.portfolio_risk import PortfolioRiskService, PortfolioRiskStore
from qibao_api.a_shares.candidate_sentiment import CandidateSentimentEvaluator
from qibao_api.a_shares.candidate_sentiment_repository import (
    CandidateSentimentRepository,
)
from qibao_api.a_shares.candidate_sentiment_service import CandidateSentimentService
from qibao_api.a_shares.first_limit_up_repository import FirstLimitUpRepository
from qibao_api.a_shares.first_limit_up_service import (
    FirstLimitUpService,
    SynchronousTencentQuoteSource,
)
from qibao_api.a_shares.kronos_forecast import KronosForecastService
from qibao_api.a_shares.kronos_runtime import LazyKronosRuntime
from qibao_api.a_shares.repository import AShareResearchRepository
from qibao_api.a_shares.preparation import AStockPreparationService
from qibao_api.a_shares.stock_timeline import StockTimelineService
from qibao_api.a_shares.news_alerts import BreakingNewsAlertService
from qibao_api.a_shares.event_impact import EventImpactService
from qibao_api.gongbu.baidu_history import BaiduHistorySource
from qibao_api.gongbu.data_service import FallbackHistorySource, MarketDataService
from qibao_api.gongbu.full_market_history import FullMarketHistoryService
from qibao_api.gongbu.history_sync_repository import HistorySyncRepository
from qibao_api.gongbu.tdx_import_repository import TdxImportRepository
from qibao_api.gongbu.tdx_local_import import TdxLocalImportService
from qibao_api.gongbu.tdx_auto_import import TdxAutoImportMonitor
from qibao_api.gongbu.tdx_official_package import OfficialTdxPackageService
from qibao_api.gongbu.tdx_client import create_tdx_client
from qibao_api.gongbu.tdx_history import TdxHistorySource
from qibao_api.gongbu.tdx_local_overview import (
    LocalTdxOverviewSource,
    TdxJsonRpcClient,
)
from qibao_api.gongbu.tdx_local_calendar import TdxLocalIpoSource
from qibao_api.gongbu.tdx_formula import TdxLocalFormulaSource
from qibao_api.gongbu.tdx_local_professional import (
    TdxLocalProfessionalSource,
    TdxQuantPythonSource,
)
from qibao_api.gongbu.self_contained_overview import (
    MootdxAShareCatalogSource,
    SelfContainedOverviewProvider,
)
from qibao_api.gongbu.tdx_local_daily import (
    LocalTdxDailyFactorBuilder,
    LocalTdxMarketSentimentSource,
)
from qibao_api.gongbu.local_market_review import LocalMarketReviewSource
from qibao_api.gongbu.eastmoney_market_review import EastmoneyDragonTigerSource
from qibao_api.local_sources.discovery import (
    LocalTerminalDiscovery,
    LocalTerminalDiscoveryResult,
    LocalTerminalDiscoveryState,
)
from qibao_api.local_sources.repository import (
    LocalSourceSettingsRepository,
    LocalTerminalDiscoverySnapshotRepository,
)
from qibao_api.gongbu.tencent_quotes import TencentQuoteSource, market_prefix
from qibao_api.gongbu.tencent_overview import TencentOverviewSource
from qibao_api.convertible_bonds.adapters import (
    EastmoneyBondUniverseSource,
    EastmoneyBondValuationSource,
    EastmoneyClauseSource,
    TencentBondQuoteSource,
)
from qibao_api.convertible_bonds.tdx_local import FallbackClauseSource, TdxLocalClauseSource
from qibao_api.convertible_bonds.universe_repository import BondUniverseRepository
from qibao_api.convertible_bonds.service import ConvertibleBondService
from qibao_api.convertible_bonds.diagnosis_repository import BondDiagnosisRepository
from qibao_api.gongbu.news_collection import (
    EastmoneyGlobalNewsSource,
    EastmoneyStockNewsSource,
)
from qibao_api.gongbu.stock_news_sources import (
    CninfoAnnouncementSource,
    CompositeStockNewsSource,
    TencentStockNewsSource,
)
from qibao_api.gongbu.news_ingestion import NewsIngestionService
from qibao_api.gongbu.news_linking import DeterministicNewsLinker
from qibao_api.gongbu.news_taxonomy import (
    DEFAULT_INDUSTRY_KEYWORDS,
    DEFAULT_THEME_KEYWORDS,
)
from qibao_api.gongbu.news_repository import NewsRepository
from qibao_api.gongbu.hotspot import (
    HotspotIngestionService,
    TonghuashunHotspotSource,
)
from qibao_api.gongbu.fund_flow import (
    EastmoneyFundFlowSource,
    FundFlowRepository,
    FundFlowService,
)
from qibao_api.gongbu.sector_fund_flow import (
    EastmoneySectorFundFlowSource,
    SectorFundFlowRepository,
    SectorFundFlowService,
)
from qibao_api.gongbu.research_enrichment import ResearchEnrichmentRepository
from qibao_api.gongbu.stock_classification import (
    EastmoneyStockClassificationSource,
    StockClassificationRepository,
    StockClassificationService,
)
from qibao_api.gongbu.a_share_universe import (
    CninfoAShareUniverseSource,
    EastmoneyAShareUniverseSource,
    FallbackAShareUniverseSource,
)
from qibao_api.libu_compliance.guard import (
    AuthorizedClassificationSource,
    AuthorizedFinanceSource,
    AuthorizedFundFlowSource,
    AuthorizedHistorySource,
    AuthorizedQuoteSource,
)
from qibao_api.libu_compliance.repository import ComplianceRepository
from qibao_api.routes.backtest import router as backtest_router
from qibao_api.routes.data import router as data_router
from qibao_api.routes.health import router as health_router
from qibao_api.routes.research import router as research_router
from qibao_api.routes.settings import router as settings_router
from qibao_api.routes.market_sentiment import router as market_sentiment_router
from qibao_api.routes.market_overview import router as market_overview_router
from qibao_api.routes.quant_strategy import router as quant_strategy_router
from qibao_api.routes.quant_research import router as quant_research_router
from qibao_api.routes.late_session_selection import router as late_session_selection_router
from qibao_api.routes.walk_forward import router as walk_forward_router
from qibao_api.routes.portfolio_risk import router as portfolio_risk_router
from qibao_api.routes.first_limit_up import router as first_limit_up_router
from qibao_api.routes.tdx_local import router as tdx_local_router
from qibao_api.routes.speech import router as speech_router
from qibao_api.settings import Settings
from qibao_api.static_frontend import install_static_frontend
from qibao_api.settings_repository import AISettingsRepository, EffectiveAISettingsResolver
from qibao_api.speech.edge_tts_service import EdgeTTSService
from qibao_api.speech.settings_repository import SpeechSettingsRepository
from qibao_api.shangshu.pipeline import ResearchPipeline
from qibao_api.storage.bar_repository import BarRepository
from qibao_api.xingbu.gate import RiskGate
from qibao_api.dongchang.repository import AuditFindingRepository
from qibao_api.routes.xingbu import router as xingbu_router
from qibao_api.routes.libu import router as libu_router
from qibao_api.routes.dongchang import router as dongchang_router
from qibao_api.routes.convertible_bonds import router as convertible_bonds_router
from qibao_api.routes.news import router as news_router
from qibao_api.routes.event_impact import router as event_impact_router
from qibao_api.zhongshu.news_ai import (
    ReloadableNewsAIGateway,
)
from qibao_api.shangshu.briefing_repository import BriefingRepository
from qibao_api.shangshu.daily_briefing import DailyBriefingWorkflow
from qibao_api.shangshu.trading_calendar import (
    ExchangeCalendarsTradingDaySchedule,
    StoredTradingCalendar,
    TencentIndexTradingDaySignal,
)
from qibao_api.routes.briefings import router as briefings_router
from qibao_api.shangshu.postclose_context import RepositoryPostcloseContextSource
from qibao_api.shangshu.operations_repository import OperationsRepository
from qibao_api.operations.read_model import OperationsReadModel
from qibao_api.operations.data_lineage import DataLineageRepository
from qibao_api.tasks.progress import TaskProgressRegistry
from qibao_api.bootstrap.lazy_service import AsyncLazyService
from qibao_api.a_shares.company_research_tasks import CompanyResearchTaskService
from qibao_api.operations.performance_store import PerformanceStore
from qibao_api.operations.precompute_snapshots import (
    PrecomputeSnapshotService,
    PrecomputeSnapshotStore,
)
from qibao_api.operations.observability import ObservabilityStore
from qibao_api.operations.shared_snapshots import SharedSnapshotRegistry
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus
from qibao_api.operations.realtime_ai import RealtimeAITriggerQueue
from qibao_api.storage.replay_snapshot_store import ReplaySnapshotStore
from qibao_api.storage.late_session_audit_store import LateSessionAuditStore
from qibao_api.shangshu.scheduler import DailyBriefingScheduler
from qibao_api.gongbu.backup_service import BackupService
from qibao_api.routes.operations import router as operations_router
from qibao_api.routes.watchlist_risk import router as watchlist_risk_router
from qibao_api.a_shares.watchlist_risk import WatchlistRiskService
from qibao_api.routes.decisions import router as decisions_router
from qibao_api.shangshu.decision_repository import DecisionRepository
from qibao_api.shangshu.decision_runtime import (
    CandidateFactorInputSource,
    DecisionSymbolSource,
    DecisionPhaseRunner,
    DeterministicIntradayEvaluator,
    RepositoryCandidateFactorSource,
    RepositoryComplianceSource,
    RepositoryEvidenceSource,
    RepositoryMarketOutcomeSource,
    RepositoryRiskSource,
    TencentPollingMarketFeed,
)
from qibao_api.shangshu.intraday_monitor import IntradayMonitor, PollStateRepository
from qibao_api.zhongshu.decision_ai import ReloadableDecisionAIGateway
from qibao_api.zhongshu.premarket_decision import PremarketDecisionService
from qibao_api.zhongshu.postclose_review import PostcloseReviewService


logger = logging.getLogger(__name__)
PORTABLE_HISTORY_RECONCILIATION_DELAY_SECONDS = 15.0
CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _create_database_engine(database_url: str):
    """Create the schema in a worker so startup can overlap local discovery.

    Both operations are independent filesystem reads/writes during process
    startup.  Keeping this in a tiny helper makes the concurrency boundary
    explicit and leaves all runtime database access on the existing engine.
    """
    # SQLAlchemy is only needed when the lifespan bootstraps the database.  Do
    # not import its large dialect/typing graph while the desktop API module is
    # being imported; this keeps the visible shell and API thread responsive.
    from sqlalchemy import create_engine
    from qibao_api.storage.database import create_schema

    engine = create_engine(database_url)
    create_schema(engine)
    return engine


async def _scheduler_loop(
    scheduler, write_gate: asyncio.Lock, interval_seconds: int
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with write_gate:
                now = datetime.now(timezone.utc)
                await asyncio.to_thread(_runtime_tick, scheduler, now)
        except Exception:
            logger.exception("scheduled briefing tick failed")


async def _sector_fund_flow_sampling_loop(
    service,
    *,
    clock=lambda: datetime.now(timezone.utc),
    sleep=asyncio.sleep,
    initial_delay_seconds: float = 5,
    intraday_interval_seconds: float = 60,
    idle_interval_seconds: float = 900,
) -> None:
    await sleep(max(0.0, initial_delay_seconds))
    while True:
        try:
            await service.sync()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info("sector fund-flow sample unavailable; keeping cache", exc_info=True)
        local_now = clock().astimezone(CHINA_TZ)
        session_time = local_now.weekday() < 5 and (
            datetime_time(9, 15) <= local_now.time() <= datetime_time(11, 35)
            or datetime_time(12, 55) <= local_now.time() <= datetime_time(15, 5)
        )
        await sleep(
            intraday_interval_seconds if session_time else idle_interval_seconds
        )


async def _source_health_snapshot_loop(
    repository,
    *,
    observability=None,
    sleep=asyncio.sleep,
    interval_seconds: float = 30,
) -> None:
    """Refresh only the local read model; GET requests never probe sources."""
    while True:
        try:
            await asyncio.to_thread(repository.refresh_source_health_snapshot, 20)
        except asyncio.CancelledError:
            raise
        except Exception:
            if observability is not None:
                observability.record(
                    "source-health-snapshot",
                    status="error",
                    error_code="snapshot_refresh_failed",
                )
            logger.info(
                "source health snapshot refresh unavailable; keeping cache",
                exc_info=True,
            )
        await sleep(interval_seconds)


async def _tdx_auto_import_loop(
    monitor,
    *,
    sleep=asyncio.sleep,
    initial_delay_seconds: float = 20,
    interval_seconds: float = 30,
) -> None:
    await sleep(max(0.0, initial_delay_seconds))
    while True:
        try:
            await asyncio.to_thread(monitor.poll)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info("TDX auto-import monitor unavailable; keeping status", exc_info=True)
        await sleep(max(1.0, interval_seconds))


def _runtime_tick(scheduler, now: datetime) -> None:
    scheduler.tick(now)
    scheduler.tick_intraday(now)


def _reconcile_history_symbols(bar_repository, instrument_directory, as_of) -> None:
    try:
        for symbol in bar_repository.symbols_with_history(1, as_of):
            if instrument_directory.resolve(symbol) is None:
                instrument_directory.observe(
                    AShareInstrument(
                        symbol=symbol,
                        name=symbol,
                        exchange=market_prefix(symbol),
                        observed_at=datetime.now(timezone.utc),
                        quote_quality="unavailable",
                    )
                )
    except Exception:
        logger.warning("background history symbol reconciliation failed", exc_info=True)


def _reconcile_history_supplement(service) -> None:
    """Refresh persisted repair evidence without making desktop boot depend on DuckDB."""
    try:
        service.reconcile_current_job()
    except Exception:
        logger.warning(
            "background history supplement reconciliation failed; keeping persisted status",
            exc_info=True,
        )


async def _schedule_history_symbol_reconciliation(
    executor,
    function,
    args: tuple[object, ...],
    *,
    delay_seconds: float,
) -> None:
    await asyncio.sleep(max(0.0, delay_seconds))
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, function, *args)


def _refresh_market_sentiment(service, now: datetime) -> None:
    try:
        service.refresh(now)
    except MarketSentimentWrongPhase:
        logger.info("initial market sentiment refresh skipped outside session")
    except Exception:
        logger.info("initial market sentiment refresh deferred", exc_info=True)


def _refresh_after_tdx_import(application, latest: date | None) -> None:
    """Rebuild only evidence-backed read models after a local import commits."""
    if latest is None:
        return
    review = getattr(application.state, "local_market_review_source", None)
    if review is not None:
        try:
            review.refresh(as_of=latest)
        except Exception:
            logger.info("local market review rebuild deferred after TDX import", exc_info=True)
    now = datetime.now(timezone.utc)
    calendar = getattr(application.state, "trading_calendar", None)
    local_now = now.astimezone(CHINA_TZ)
    in_session = datetime_time(9, 30) <= local_now.time() <= datetime_time(15, 0)
    is_trading_day = calendar is None or calendar.is_trading_day(latest)
    if latest != local_now.date() or not in_session or not is_trading_day:
        return
    sentiment = getattr(application.state, "market_sentiment_service", None)
    if sentiment is not None:
        _refresh_market_sentiment(sentiment, now)
    overview = getattr(application.state, "market_overview_service", None)
    if overview is not None:
        try:
            overview.current(now)
        except Exception:
            logger.info("market overview rebuild deferred after TDX import", exc_info=True)


def _defer_initial_market_sentiment_refresh(executor, service, now: datetime) -> None:
    executor.submit(_refresh_market_sentiment, service, now)


def _should_defer_initial_market_sentiment_refresh(now: datetime) -> bool:
    """Avoid queueing a known premarket no-op behind startup disk work."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    return now.astimezone(CHINA_TZ).time() >= datetime_time(9, 30)


async def _refresh_a_share_universe(compliance, source, directory) -> None:
    try:
        compliance.require_feature_sources("a_share_universe", "a_share")
        universe = await source.fetch()
        directory.observe_many(universe)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("A-share universe sync unavailable", exc_info=True)


async def _refresh_bond_universe(service) -> None:
    try:
        await service.sync_universe()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("convertible-bond universe sync unavailable", exc_info=True)


async def _refresh_local_source_discovery(
    application: FastAPI,
    discovery: LocalTerminalDiscovery,
    settings,
    repository: LocalTerminalDiscoverySnapshotRepository,
    state: LocalTerminalDiscoveryState,
) -> None:
    try:
        result = await asyncio.to_thread(discovery.inspect, settings)
        await asyncio.to_thread(repository.save, result)
        state.update(result)
        application.state.local_source_discovery_result = result
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("local source discovery refresh unavailable", exc_info=True)


@asynccontextmanager
async def lifespan(application: FastAPI):
    startup_started = time.monotonic()

    def log_startup_stage(stage: str) -> None:
        logger.info(
            "desktop startup stage=%s elapsed_ms=%d",
            stage,
            round((time.monotonic() - startup_started) * 1000),
        )

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    write_gate = asyncio.Lock()
    application.state.write_gate = write_gate
    application.state.task_progress_registry = TaskProgressRegistry()
    shared_snapshot_registry = SharedSnapshotRegistry(
        settings.data_dir / "shared-snapshots.sqlite3"
    )
    application.state.shared_snapshot_registry = shared_snapshot_registry
    realtime_snapshot_bus = RealtimeSnapshotBus(max_queue_size=32)
    application.state.realtime_snapshot_bus = realtime_snapshot_bus
    replay_snapshot_store = ReplaySnapshotStore(
        settings.data_dir / "replay-snapshots.sqlite3"
    )
    application.state.replay_snapshot_store = replay_snapshot_store
    late_session_audit_store = LateSessionAuditStore(
        settings.data_dir / "late-session-audit.sqlite3"
    )
    application.state.late_session_audit_store = late_session_audit_store
    application.state.performance_store = PerformanceStore(
        settings.data_dir / "performance.sqlite3",
        shared_snapshot_registry=shared_snapshot_registry,
    )
    precompute_snapshot_store = PrecomputeSnapshotStore(
        settings.data_dir / "precomputed-snapshots.sqlite3"
    )
    application.state.precompute_snapshot_store = precompute_snapshot_store
    observability_store = ObservabilityStore(settings.data_dir / "observability.sqlite3")
    application.state.observability_store = observability_store
    ai_settings_repository = AISettingsRepository(settings.data_dir)
    application.state.ai_settings_repository = ai_settings_repository
    effective_ai_settings = EffectiveAISettingsResolver(
        ai_settings_repository,
        fallback=getattr(settings, "initial_ai_settings", None),
    )
    application.state.effective_ai_settings = effective_ai_settings
    speech_settings_repository = SpeechSettingsRepository(settings.data_dir)
    application.state.speech_settings_repository = speech_settings_repository
    is_portable_runtime = bool(os.environ.get("QIBAO_PORTABLE_ROOT"))
    portable_root = Path(os.environ.get("QIBAO_PORTABLE_ROOT", settings.data_dir))
    local_source_settings_repository = LocalSourceSettingsRepository(
        portable_root / "config" / "data-sources.json"
    )
    local_terminal_discovery = LocalTerminalDiscovery()
    local_source_settings_record = local_source_settings_repository.load()
    application.state.local_source_settings_repository = (
        local_source_settings_repository
    )
    application.state.local_terminal_discovery = local_terminal_discovery
    local_discovery_snapshot_repository = (
        LocalTerminalDiscoverySnapshotRepository(
            portable_root / "cache" / "local-source-discovery.json"
        )
    )
    cached_local_discovery = local_discovery_snapshot_repository.load(
        local_source_settings_record.settings
    )
    initial_local_discovery = cached_local_discovery
    if (
        initial_local_discovery is None
        and not local_source_settings_record.settings.auto_discovery
        and (
            local_source_settings_record.settings.tdx_install_paths
            or local_source_settings_record.settings.ths_install_paths
        )
    ):
        try:
            initial_local_discovery = local_terminal_discovery.inspect_configured(
                local_source_settings_record.settings
            )
        except Exception:
            logger.warning("configured local source discovery unavailable", exc_info=True)
    initial_local_discovery = initial_local_discovery or LocalTerminalDiscoveryResult(
        scanned_at=datetime.now(timezone.utc),
        terminals=(),
        active_tdx_vipdoc=None,
        settings=local_source_settings_record.settings,
    )
    local_source_discovery_state = LocalTerminalDiscoveryState(
        initial_local_discovery
    )
    application.state.local_source_discovery_result = initial_local_discovery
    application.state.local_source_discovery_state = local_source_discovery_state
    # The previous verified result is sufficient to construct local services.
    # A full Windows terminal scan is refresh work and must not gate API ready.
    local_source_discovery_task = asyncio.create_task(
        _refresh_local_source_discovery(
            application,
            local_terminal_discovery,
            local_source_settings_record.settings,
            local_discovery_snapshot_repository,
            local_source_discovery_state,
        ),
        name="local-source-discovery",
    )
    engine = await asyncio.to_thread(
        _create_database_engine, settings.database_url
    )
    # These repositories build SQLAlchemy table metadata only when the
    # lifespan has completed its parallel bootstrap.  Keeping them out of the
    # module import graph reduces cold desktop startup without changing the
    # runtime schema or repository behavior.
    from qibao_api.convertible_bonds.repository import BondClauseRepository
    from qibao_api.storage.quote_repository import QuoteRepository

    log_startup_stage("local-sources-cache-ready")
    application.state.edge_tts_service = EdgeTTSService(portable_root / "cache" / "tts")
    compliance = ComplianceRepository(settings.data_dir / "compliance.sqlite3")
    audit_repository = AuditFindingRepository(settings.data_dir / "audit.sqlite3")
    application.state.audit_repository = audit_repository
    application.state.compliance_repository = compliance
    compliance.set_feature_sources("realtime_quotes", "a_share", ("tencent",))
    compliance.set_feature_sources("a_share_finance", "a_share", ("mootdx",))
    compliance.set_feature_sources("history_sync.mootdx", "a_share", ("mootdx",))
    compliance.set_feature_sources("history_sync.baidu", "a_share", ("baidu",))
    compliance.set_feature_sources("bond_quotes", "convertible_bond", ("tencent",))
    compliance.set_feature_sources("bond_clauses", "convertible_bond", ("eastmoney",))
    compliance.set_feature_sources("bond_valuations", "convertible_bond", ("eastmoney",))
    compliance.set_feature_sources(
        "market_news", "a_share", ("tencent", "cninfo", "eastmoney")
    )
    compliance.set_feature_sources(
        "market_hotspots", "a_share", ("tonghuashun",)
    )
    compliance.set_feature_sources(
        "stock_classification", "a_share", ("eastmoney",)
    )
    compliance.set_feature_sources("stock_fund_flow", "a_share", ("eastmoney",))
    compliance.set_feature_sources("a_share_universe", "a_share", ("eastmoney",))
    for asset in ("a_share", "convertible_bond"):
        for source in {
            item.source for item in compliance.list_source_dependencies(asset)
        }:
            compliance.ensure_source_ready(source, asset)
    bond_repository = BondClauseRepository(engine)
    bond_repository.initialize()
    bond_universe_repository = BondUniverseRepository(
        settings.data_dir / "bond-universe.sqlite3"
    )
    diagnosis_repository = BondDiagnosisRepository(settings.data_dir / "bond-diagnoses.sqlite3")
    news_repository = NewsRepository(settings.data_dir / "news.sqlite3")
    application.state.news_repository = news_repository
    application.state.news_alert_service = BreakingNewsAlertService(news_repository)
    stock_classification_repository = StockClassificationRepository(
        settings.data_dir / "stock-classifications.sqlite3"
    )
    application.state.stock_classification_repository = (
        stock_classification_repository
    )
    fund_flow_repository = FundFlowRepository(
        settings.data_dir / "fund-flow.sqlite3"
    )
    application.state.fund_flow_repository = fund_flow_repository
    sector_fund_flow_repository = SectorFundFlowRepository(
        settings.data_dir / "sector-fund-flow.sqlite3"
    )
    application.state.sector_fund_flow_repository = sector_fund_flow_repository
    research_enrichment_repository = ResearchEnrichmentRepository(
        settings.data_dir / "research-enrichment.sqlite3"
    )
    application.state.research_enrichment_repository = research_enrichment_repository
    from qibao_api.a_shares.company_research_versions import CompanyResearchVersionRepository
    from qibao_api.a_shares.company_research_ai_cache import CompanyResearchAIResultRepository
    company_research_version_repository = CompanyResearchVersionRepository(
        settings.data_dir / "company-research-versions.sqlite3",
        shared_snapshot_registry=shared_snapshot_registry,
        realtime_snapshot_bus=realtime_snapshot_bus,
    )
    application.state.company_research_version_repository = company_research_version_repository
    company_research_ai_result_repository = CompanyResearchAIResultRepository(
        settings.data_dir / "company-research-ai-results.sqlite3"
    )
    application.state.company_research_ai_result_repository = (
        company_research_ai_result_repository
    )
    a_share_research_repository = AShareResearchRepository(
        settings.data_dir / "a-share-research.sqlite3"
    )
    application.state.a_share_research_repository = a_share_research_repository
    candidate_sentiment_repository = CandidateSentimentRepository(
        settings.data_dir / "candidate-sentiment.sqlite3"
    )
    application.state.candidate_sentiment_repository = (
        candidate_sentiment_repository
    )
    briefing_repository = BriefingRepository(settings.data_dir / "briefings.sqlite3")
    application.state.briefing_repository = briefing_repository
    decision_repository = DecisionRepository(
        getattr(settings, "decision_database_path", settings.data_dir / "decisions.sqlite3")
    )
    application.state.decision_repository = decision_repository
    operations_repository = OperationsRepository(
        settings.data_dir / "operations.sqlite3"
    )
    data_lineage_repository = DataLineageRepository(
        settings.data_dir / "data-lineage.sqlite3"
    )
    source_health_snapshot_task = asyncio.create_task(
        _source_health_snapshot_loop(
            operations_repository, observability=observability_store
        ),
        name="source-health-snapshot",
    )
    tdx_auto_import_task = None
    application.state.operations_repository = operations_repository
    application.state.data_lineage_repository = data_lineage_repository
    application.state.operations_read_model = OperationsReadModel(portable_root)
    log_startup_stage("repositories-ready")

    bond_universe_refresh_task = None
    sector_fund_flow_sampling_task = None
    async with httpx.AsyncClient(timeout=10) as client:
        application.state.a_share_quote_source = TencentQuoteSource(client)
        application.state.sector_fund_flow_service = SectorFundFlowService(
            EastmoneySectorFundFlowSource(client=client),
            sector_fund_flow_repository,
        )
        with httpx.Client(timeout=10) as history_client:
            history_sources = [
                AuthorizedHistorySource(
                    TdxHistorySource(
                        client_factory=create_tdx_client,
                        observer=operations_repository.append_source_attempt,
                    ),
                    compliance,
                    "history_sync.mootdx",
                    "a_share",
                )
            ]
            history_sources.append(
                AuthorizedHistorySource(
                    BaiduHistorySource(
                        history_client,
                        observer=operations_repository.append_source_attempt,
                    ),
                    compliance,
                    "history_sync.baidu",
                    "a_share",
                )
            )
            bar_repository = BarRepository(
                settings.data_dir / "market.duckdb",
                settings.data_dir / "parquet" / "a-shares",
            )
            first_limit_up_repository = FirstLimitUpRepository(
                settings.data_dir / "first-limit-up.sqlite3"
            )
            application.state.first_limit_up_repository = first_limit_up_repository
            trading_calendar = StoredTradingCalendar(
                bar_repository,
                live_signal=TencentIndexTradingDaySignal(history_client),
                schedule=ExchangeCalendarsTradingDaySchedule(),
            )
            application.state.first_limit_up_service = FirstLimitUpService(
                bar_repository=bar_repository,
                quote_source=SynchronousTencentQuoteSource(history_client, compliance),
                repository=first_limit_up_repository,
                universe_provider=lambda: (
                    application.state.a_share_instrument_directory.active_symbols()
                ),
                trading_calendar=trading_calendar,
            )
            kronos_model = getattr(settings, "kronos_model", "NeoQuasar/Kronos-mini")
            application.state.kronos_forecast_service = KronosForecastService(
                bar_repository=bar_repository,
                trading_calendar=trading_calendar,
                predictor=LazyKronosRuntime(
                    repo_path=getattr(settings, "kronos_repo_path", None),
                    tokenizer_name=getattr(
                        settings,
                        "kronos_tokenizer",
                        "NeoQuasar/Kronos-Tokenizer-2k",
                    ),
                    model_name=kronos_model,
                    device=getattr(settings, "kronos_device", None),
                ),
                enabled=getattr(settings, "kronos_enabled", False),
                model_name=kronos_model,
                lookback_bars=getattr(settings, "kronos_lookback_bars", 250),
                sample_count=getattr(settings, "kronos_sample_count", 20),
            )
            application.state.bar_repository = bar_repository
            application.state.event_impact_service = EventImpactService(
                news_repository, bar_repository
            )
            application.state.market_data_service = MarketDataService(
                FallbackHistorySource(history_sources),
                bar_repository,
            )
            application.state.pipeline = ResearchPipeline(
                AuthorizedQuoteSource(
                    TencentQuoteSource(client),
                    compliance,
                    ("realtime_quotes",),
                    "a_share",
                ),
                QuoteRepository(engine),
                RiskGate(),
            )
            application.state.a_share_diagnosis_service = AShareDiagnosisService(
                bar_repository,
                AuthorizedQuoteSource(
                    TencentQuoteSource(client),
                    compliance,
                    ("realtime_quotes",),
                    "a_share",
                ),
                AuthorizedFinanceSource(
                    TdxFinanceSource(
                        client_factory=create_tdx_client,
                        observer=operations_repository.append_source_attempt,
                        local_rpc_factory=(
                            lambda: TdxJsonRpcClient(
                                endpoint=local_source_settings_record.settings.tdx_rpc_url
                            )
                            if local_source_settings_record.settings.tdx_rpc_enabled
                            and local_source_settings_record.settings.tdx_rpc_url is not None
                            else None
                        ),
                    ),
                    compliance,
                    "a_share_finance",
                    "a_share",
                ),
                news_repository,
                a_share_research_repository,
                classification_repository=stock_classification_repository,
                fund_flow_repository=fund_flow_repository,
                trading_calendar=trading_calendar,
            )
            def create_company_research_service():
                from qibao_api.a_shares.company_research import CompanyResearchService
                from qibao_api.gongbu.sina_financials import SinaFinancialHistorySource
                from qibao_api.gongbu.tdx_company_profile import TdxCompanyProfileSource
                from qibao_api.gongbu.research_enrichment import EastmoneyResearchEnrichmentSource

                return CompanyResearchService(
                    application.state.a_share_diagnosis_service,
                    SinaFinancialHistorySource(client=history_client),
                    TdxCompanyProfileSource(client_factory=create_tdx_client),
                    enrichment_source=EastmoneyResearchEnrichmentSource(client),
                    enrichment_repository=research_enrichment_repository,
                    version_repository=company_research_version_repository,
                )

            application.state.company_research_service = AsyncLazyService(
                create_company_research_service
            )
            application.state.company_research_task_service = CompanyResearchTaskService(
                application.state.company_research_service,
                application.state.task_progress_registry,
            )
            from qibao_api.a_shares.company_research_ai import ReloadableCompanyResearchAIGateway
            from qibao_api.a_shares.company_research_ai_tasks import CompanyResearchAITaskService
            application.state.company_research_ai_task_service = CompanyResearchAITaskService(
                company_research_version_repository,
                ReloadableCompanyResearchAIGateway(effective_ai_settings, history_client),
                application.state.task_progress_registry,
                result_repository=company_research_ai_result_repository,
            )
            application.state.bond_repository = bond_repository
            application.state.bond_service = ConvertibleBondService(
                TencentBondQuoteSource(client),
                FallbackClauseSource(
                    TdxLocalClauseSource(
                        lambda: TdxJsonRpcClient(
                            endpoint=local_source_settings_record.settings.tdx_rpc_url
                        )
                        if local_source_settings_record.settings.tdx_rpc_enabled
                        and local_source_settings_record.settings.tdx_rpc_url is not None
                        else None
                    ),
                    EastmoneyClauseSource(client=client),
                ),
                TencentQuoteSource(client), bond_repository, compliance,
                diagnosis_repository,
                EastmoneyBondValuationSource(client=client),
                universe_source=EastmoneyBondUniverseSource(client=client),
                universe_repository=bond_universe_repository,
            )
            bond_universe_refresh_task = asyncio.create_task(
                _refresh_bond_universe(application.state.bond_service),
                name="bond-universe-refresh",
            )
            log_startup_stage("bond-universe-ready")
            application.state.news_service = NewsIngestionService(
                EastmoneyGlobalNewsSource(client=client),
                news_repository,
                DeterministicNewsLinker(
                    instrument_aliases=lambda: (
                        application.state.a_share_instrument_directory.alias_map()
                        if getattr(application.state, "a_share_instrument_directory", None)
                        else {}
                    ),
                    industry_keywords=DEFAULT_INDUSTRY_KEYWORDS,
                    theme_keywords=DEFAULT_THEME_KEYWORDS,
                ),
                compliance,
                ReloadableNewsAIGateway(
                    effective_ai_settings,
                    client=client,
                ),
                stock_source=CompositeStockNewsSource((
                    TencentStockNewsSource(client=client),
                    CninfoAnnouncementSource(client=client),
                    EastmoneyStockNewsSource(client=client),
                )),
            )
            application.state.hotspot_service = HotspotIngestionService(
                TonghuashunHotspotSource(history_client),
                news_repository,
                compliance,
            )
            application.state.stock_classification_service = (
                StockClassificationService(
                    AuthorizedClassificationSource(
                        EastmoneyStockClassificationSource(client=client),
                        compliance,
                        "stock_classification",
                        "a_share",
                    ),
                    stock_classification_repository,
                )
            )
            application.state.fund_flow_service = FundFlowService(
                AuthorizedFundFlowSource(
                    EastmoneyFundFlowSource(
                        client=client,
                        observer=operations_repository.append_source_attempt,
                    ),
                    compliance,
                    "stock_fund_flow",
                    "a_share",
                ),
                fund_flow_repository,
            )
            application.state.candidate_sentiment_service = (
                CandidateSentimentService(
                    research_repository=a_share_research_repository,
                    sentiment_repository=candidate_sentiment_repository,
                    news_repository=news_repository,
                    fund_flow_repository=fund_flow_repository,
                    evaluator=CandidateSentimentEvaluator(),
                    news_ingestion_service=application.state.news_service,
                    hotspot_ingestion_service=application.state.hotspot_service,
                    fund_flow_service=application.state.fund_flow_service,
                )
            )
            application.state.a_share_preparation_service = AStockPreparationService(
                bar_repository,
                application.state.market_data_service,
                application.state.a_share_diagnosis_service,
                application.state.news_service,
                news_repository,
                trading_calendar,
                classification_service=(
                    application.state.stock_classification_service
                ),
                fund_flow_service=application.state.fund_flow_service,
                lock_dir=settings.data_dir / "preparation-locks",
            )
            application.state.briefing_workflow = DailyBriefingWorkflow(
                news_repository,
                briefing_repository,
                trading_calendar,
                RepositoryPostcloseContextSource(decision_repository, audit_repository),
            )
            application.state.decision_calendar = trading_calendar
            application.state.trading_calendar = trading_calendar
            decision_candidate_source = RepositoryCandidateFactorSource(
                application.state.a_share_diagnosis_service
            )
            decision_compliance_source = RepositoryComplianceSource(compliance)
            decision_risk_source = RepositoryRiskSource(
                audit_repository, application.state.a_share_diagnosis_service,
                news_repository=news_repository,
                classification_repository=stock_classification_repository,
                fund_flow_repository=fund_flow_repository,
                trading_calendar=trading_calendar,
            )
            decision_evidence_source = RepositoryEvidenceSource(news_repository)
            decision_market_feed = TencentPollingMarketFeed(history_client, compliance)
            decision_evaluator = DeterministicIntradayEvaluator()
            poll_state_repository = PollStateRepository(
                settings.data_dir / "intraday-poll.sqlite3"
            )
            application.state.poll_state_repository = poll_state_repository
            decision_ai_gateway = ReloadableDecisionAIGateway(
                effective_ai_settings,
                client=history_client,
            )
            application.state.realtime_ai_trigger_queue = RealtimeAITriggerQueue(
                realtime_snapshot_bus,
                decision_ai_gateway,
                observability=observability_store,
                max_workers=1,
                dedupe_seconds=60,
            )
            application.state.realtime_ai_trigger_queue.start()
            premarket_decision = PremarketDecisionService(
                candidate_service=decision_candidate_source,
                news_repository=news_repository,
                compliance_checker=decision_compliance_source,
                market_risk_summary=decision_risk_source,
                ai_gateway=decision_ai_gateway,
                decision_repository=decision_repository,
                trading_calendar=application.state.decision_calendar,
                clock=lambda: datetime.now(timezone.utc),
            )
            decision_symbols = DecisionSymbolSource(
                decision_repository,
                decision_candidate_source,
            )

            intraday_monitor = IntradayMonitor(
                feed=decision_market_feed,
                calendar=application.state.decision_calendar,
                state_repository=poll_state_repository,
                focus_symbols=decision_symbols,
                universe_symbols=decision_symbols,
                decision_repository=decision_repository,
                evaluator=decision_evaluator,
                ai_gateway=decision_ai_gateway,
                candidate_factor_port=CandidateFactorInputSource(decision_candidate_source),
                risk_port=decision_risk_source,
                compliance_port=decision_compliance_source,
                evidence_port=decision_evidence_source,
            )
            decision_outcome_source = RepositoryMarketOutcomeSource(
                decision_repository, bar_repository
            )
            postclose_review = PostcloseReviewService(
                decision_repository=decision_repository,
                market_outcome_source=decision_outcome_source,
                audit_repository=audit_repository,
                ai_gateway=decision_ai_gateway,
            )
            decision_phase_runner = DecisionPhaseRunner(
                repository=decision_repository, premarket=premarket_decision,
                intraday_monitor=intraday_monitor, postclose=postclose_review,
            )
            application.state.decision_candidate_source = decision_candidate_source
            application.state.decision_compliance_source = decision_compliance_source
            application.state.decision_risk_source = decision_risk_source
            application.state.decision_evidence_source = decision_evidence_source
            application.state.decision_market_feed = decision_market_feed
            application.state.decision_evaluator = decision_evaluator
            application.state.decision_outcome_source = decision_outcome_source
            application.state.intraday_monitor = intraday_monitor
            application.state.decision_phase_runner = decision_phase_runner
            application.state.scheduler = DailyBriefingScheduler(
                application.state.briefing_workflow,
                trading_calendar,
                operations_repository,
                decision_workflow=decision_phase_runner,
                intraday_monitor=intraday_monitor,
                hotspot_service=application.state.hotspot_service,
                first_limit_up_service=application.state.first_limit_up_service,
            )
            application.state.backup_service = BackupService(
                settings.data_dir, bar_repository
            )
            scheduler_task = None
            universe_refresh_task = None
            should_refresh_universe = False
            a_share_instrument_directory = AShareInstrumentDirectory(
                settings.data_dir / "a-share-instruments.sqlite3"
            )
            log_startup_stage("services-and-instrument-directory-ready")
            history_sync_repository = HistorySyncRepository(
                settings.data_dir / "history-sync.sqlite3"
            )
            tdx_import_repository = TdxImportRepository(
                settings.data_dir / "tdx-import.sqlite3"
            )
            history_sync_executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="history-sync",
            )
            tdx_import_executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="tdx-import",
            )
            history_supplement_executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="history-supplement",
            )
            history_symbol_reconciliation_task = None
            application.state.history_sync_repository = history_sync_repository
            application.state.tdx_import_repository = tdx_import_repository
            application.state.history_sync_executor = history_sync_executor
            application.state.precompute_snapshot_service = PrecomputeSnapshotService(
                precompute_snapshot_store,
                executor=history_sync_executor,
                performance_store=application.state.performance_store,
            )
            application.state.tdx_import_executor = tdx_import_executor
            application.state.history_supplement_executor = history_supplement_executor
            application.state.tdx_import_service = TdxLocalImportService(
                bar_repository,
                job_repository=tdx_import_repository,
                clock=lambda: datetime.now(timezone.utc),
                discovery=local_source_discovery_state,
                archive_paths=local_source_settings_record.settings.tdx_archive_paths,
            )
            application.state.history_supplement_service = OfficialTdxPackageService(
                cache_dir=portable_root / "cache" / "tdx-official",
                state_path=settings.data_dir / "history-supplement.json",
                tdx_import_service=application.state.tdx_import_service,
                clock=lambda: datetime.now(timezone.utc),
            )
            application.state.history_supplement_service.recover_interrupted()
            def _tdx_auto_import_paths():
                paths = []
                active = local_source_discovery_state.active_tdx_vipdoc
                if active is not None:
                    paths.append(active)
                    if active.name.casefold() == "vipdoc":
                        archive_root = active.parent / "T0002"
                        if archive_root.is_dir():
                            paths.append(archive_root)
                paths.extend(local_source_settings_record.settings.tdx_archive_paths)
                return tuple(dict.fromkeys(paths))

            tdx_auto_import_monitor = TdxAutoImportMonitor(
                _tdx_auto_import_paths,
                service=application.state.tdx_import_service,
                executor=tdx_import_executor,
            )
            application.state.tdx_auto_import_monitor = tdx_auto_import_monitor
            full_market_history_service = None
            market_sentiment_repository = None
            local_tdx_overview_source = None
            local_market_review_source = None
            try:
                application.state.a_share_instrument_directory = a_share_instrument_directory
                application.state.watchlist_risk_service = WatchlistRiskService(
                    a_share_instrument_directory, bar_repository
                )
                application.state.a_share_universe_source = FallbackAShareUniverseSource(
                    EastmoneyAShareUniverseSource(client=client),
                    CninfoAShareUniverseSource(client=client),
                )
                latest_directory_observation = (
                    a_share_instrument_directory.latest_named_observed_at()
                    if hasattr(a_share_instrument_directory, "latest_named_observed_at")
                    else None
                )
                named_directory_count = (
                    a_share_instrument_directory.named_count()
                    if hasattr(a_share_instrument_directory, "named_count")
                    else 0
                )
                should_refresh_universe = (
                    hasattr(a_share_instrument_directory, "observe_many")
                    and (
                    named_directory_count < 1000
                    or
                    latest_directory_observation is None
                    or datetime.now(timezone.utc) - latest_directory_observation
                    > timedelta(hours=12)
                    )
                )
                log_startup_stage("a-share-universe-ready")
                full_market_history_service = FullMarketHistoryService(
                    directory=a_share_instrument_directory,
                    bar_repository=bar_repository,
                    tdx_source=history_sources[0],
                    baidu_source=history_sources[1],
                    job_repository=history_sync_repository,
                    clock=lambda: datetime.now(timezone.utc),
                    trading_calendar=trading_calendar,
                )
                application.state.full_market_history_service = (
                    full_market_history_service
                )
                application.state.history_supplement_service.history_service = (
                    full_market_history_service
                )
                history_supplement_executor.submit(
                    _reconcile_history_supplement,
                    application.state.history_supplement_service,
                )
                application.state.scheduler.full_market_history_service = (
                    full_market_history_service
                )
                application.state.scheduler.history_sync_submitter = (
                    history_sync_executor.submit
                )
                log_startup_stage("history-service-ready")
                full_market_history_service.recover_interrupted()
                tdx_import_repository.recover_interrupted()
                interrupted_job = full_market_history_service.current_job()
                log_startup_stage("history-recovery-ready")
                if interrupted_job is not None and interrupted_job.state == "pending":
                    history_sync_executor.submit(
                        full_market_history_service.run,
                        interrupted_job.job_id,
                    )
                market_sentiment_repository = MarketSentimentRepository(
                    settings.data_dir / "market-sentiment.sqlite3"
                )
                application.state.market_sentiment_repository = (
                    market_sentiment_repository
                )
                log_startup_stage("market-sentiment-repository-ready")
                vipdoc_root = local_source_discovery_state.active_tdx_vipdoc
                local_source_settings = local_source_settings_record.settings
                tdx_rpc = (
                    TdxJsonRpcClient(endpoint=local_source_settings.tdx_rpc_url)
                    if local_source_settings.tdx_rpc_enabled
                    and local_source_settings.tdx_rpc_url is not None
                    else None
                )
                def tdx_rpc_factory():
                    current = local_source_settings_record.settings
                    if not current.tdx_rpc_enabled or current.tdx_rpc_url is None:
                        return None
                    return TdxJsonRpcClient(endpoint=current.tdx_rpc_url)

                application.state.tdx_ipo_source = TdxLocalIpoSource(tdx_rpc_factory)
                application.state.tdx_formula_source = TdxLocalFormulaSource(tdx_rpc_factory)
                direct_tdx_roots = tuple(
                    terminal.install_path
                    for terminal in local_source_discovery_state.terminals
                    if (
                        terminal.vendor == "tdx"
                        and terminal.status == "ready"
                        and terminal.selection_eligible
                    )
                )
                application.state.tdx_professional_source = TdxLocalProfessionalSource(
                    tdx_rpc_factory,
                    fallback=TdxQuantPythonSource(direct_tdx_roots),
                )
                log_startup_stage("tdx-professional-ready")
                local_tdx_overview_source = LocalTdxOverviewSource(
                    cache_path=portable_root / "cache" / "tdx-market-overview.json",
                    rpc=tdx_rpc,
                    clock=lambda: datetime.now(timezone.utc),
                    refresh_seconds=5,
                    initial_delay_seconds=15 if is_portable_runtime else 0,
                    fallback=SelfContainedOverviewProvider(
                        catalog_loader=MootdxAShareCatalogSource(
                            directory=a_share_instrument_directory,
                            vipdoc_root=vipdoc_root,
                        ),
                        client=history_client,
                        clock=lambda: datetime.now(timezone.utc),
                    ),
                )
                application.state.local_tdx_overview_source = (
                    local_tdx_overview_source
                )
                log_startup_stage("tdx-overview-cache-ready")
                local_tdx_overview_source.start()
                local_market_review_source = LocalMarketReviewSource(
                    vipdoc_root=vipdoc_root,
                    cache_path=settings.data_dir / "market-review" / "latest.json",
                    bar_repository=bar_repository,
                    symbol_provider=lambda: tuple(
                        application.state.a_share_instrument_directory.active_symbols()
                    ),
                    trading_calendar=trading_calendar,
                    name_resolver=lambda symbol: (
                        instrument.name
                        if (instrument := a_share_instrument_directory.resolve(symbol))
                        else symbol
                    ),
                    dragon_tiger_source=(
                        EastmoneyDragonTigerSource(
                            cache_path=(
                                settings.data_dir
                                / "market-review"
                                / "dragon-tiger.json"
                            ),
                        )
                        if is_portable_runtime
                        else None
                    ),
                    clock=lambda: datetime.now(timezone.utc),
                    initial_delay_seconds=15 if is_portable_runtime else 0,
                    defer_cache_validation=is_portable_runtime,
                )
                application.state.local_market_review_source = (
                    local_market_review_source
                )
                application.state.tdx_import_service.after_import = (
                    lambda latest: _refresh_after_tdx_import(application, latest)
                )
                tdx_auto_import_task = asyncio.create_task(
                    _tdx_auto_import_loop(
                        tdx_auto_import_monitor,
                        initial_delay_seconds=20 if is_portable_runtime else 5,
                    ),
                    name="tdx-auto-import-monitor",
                )
                log_startup_stage("market-review-cache-ready")
                if is_portable_runtime:
                    local_market_review_source.start()
                market_sentiment_source = LocalTdxMarketSentimentSource(
                    overview_source=local_tdx_overview_source,
                )
                application.state.market_sentiment_source = market_sentiment_source
                sentiment_factor_builder = (
                    LocalTdxDailyFactorBuilder(
                        vipdoc_root=vipdoc_root,
                        overview_source=local_tdx_overview_source,
                        cache_path=(
                            portable_root / "cache" / "tdx-daily-factors.json"
                        ),
                    )
                    if vipdoc_root is not None
                    else MarketSentimentFactorBuilder(
                        bar_repository=bar_repository,
                        classification_repository=stock_classification_repository,
                    )
                )
                log_startup_stage("sentiment-factor-builder-ready")
                application.state.market_sentiment_service = MarketSentimentService(
                    repository=market_sentiment_repository,
                    source=market_sentiment_source,
                    evaluator=MarketSentimentEvaluator(),
                    trading_calendar=trading_calendar,
                    news_repository=news_repository,
                    factor_builder=sentiment_factor_builder,
                )
                application.state.scheduler.market_sentiment_service = (
                    application.state.market_sentiment_service
                )
                log_startup_stage("market-sentiment-service-ready")
                startup_now = datetime.now(timezone.utc)
                cached_market_overview = local_tdx_overview_source.current()
                log_startup_stage("market-overview-cache-check-ready")
                if (
                    is_portable_runtime
                    and cached_market_overview is not None
                    and _should_defer_initial_market_sentiment_refresh(startup_now)
                ):
                    _defer_initial_market_sentiment_refresh(
                        history_sync_executor,
                        application.state.market_sentiment_service,
                        startup_now,
                    )
                log_startup_stage("market-sentiment-ready")
                application.state.market_overview_service = MarketOverviewService(
                    sentiment_repository=market_sentiment_repository,
                    news_repository=news_repository,
                    first_limit_up_repository=first_limit_up_repository,
                    source=TencentOverviewSource(history_client),
                    clock=lambda: datetime.now(timezone.utc),
                    local_market_source=local_tdx_overview_source,
                    market_review_source=local_market_review_source,
                    fund_flow_repository=fund_flow_repository,
                    sector_fund_flow_repository=sector_fund_flow_repository,
                    official_calendar_source=application.state.tdx_ipo_source,
                    trading_calendar=trading_calendar,
                    cache_path=portable_root / "cache" / "market-overview.json",
                    defer_initial_refresh=is_portable_runtime,
                    initial_refresh_delay_seconds=1 if is_portable_runtime else 0,
                    shared_snapshot_registry=shared_snapshot_registry,
                    realtime_snapshot_bus=realtime_snapshot_bus,
                )
                sector_fund_flow_sampling_task = asyncio.create_task(
                    _sector_fund_flow_sampling_loop(
                        application.state.sector_fund_flow_service,
                        initial_delay_seconds=30 if is_portable_runtime else 5,
                    ),
                    name="sector-fund-flow-sampling",
                )
                quant_shadow_ledger = QuantShadowLedgerStore(
                    settings.data_dir / "quant-shadow-ledger.sqlite3"
                )
                application.state.quant_shadow_ledger = quant_shadow_ledger
                application.state.decision_journal = DecisionJournalStore(
                    settings.data_dir / "decision-journal.sqlite3"
                )
                application.state.portfolio_risk_service = PortfolioRiskService(
                    bar_repository,
                    research_enrichment_repository,
                )
                application.state.portfolio_risk_store = PortfolioRiskStore(
                    settings.data_dir / "portfolio-risk.sqlite3"
                )
                application.state.quant_strategy_service = QuantStrategyService(
                    application.state.market_overview_service,
                    application.state.a_share_diagnosis_service,
                    a_share_instrument_directory,
                    ArchivedTriggerEvidenceSource(
                        poll_state_repository,
                        fund_flow_repository,
                    ),
                    defer_initial_scan=is_portable_runtime,
                    defer_initial_overview=is_portable_runtime,
                    defer_trigger_evidence=is_portable_runtime,
                    snapshot_store=QuantStrategySnapshotStore(
                        portable_root / "cache" / "quant-strategy.json"
                    ),
                    shadow_ledger=quant_shadow_ledger,
                    shared_snapshot_registry=shared_snapshot_registry,
                    realtime_snapshot_bus=realtime_snapshot_bus,
                )
                application.state.factor_hypothesis_store = FactorHypothesisStore(
                    settings.data_dir / "factor-hypotheses.sqlite3"
                )
                application.state.quant_research_service = (
                    QuantResearchIntelligenceService(
                        application.state.quant_strategy_service,
                        quant_shadow_ledger,
                        QuantResearchSnapshotStore(
                            portable_root / "cache" / "quant-research.json"
                        ),
                    )
                )
                application.state.late_session_selection_service = LateSessionSelectionService(
                    local_market_source=local_tdx_overview_source,
                    bar_repository=bar_repository,
                    instrument_directory=a_share_instrument_directory,
                    tencent_source=application.state.market_overview_service.source,
                    market_overview_service=application.state.market_overview_service,
                    realtime_snapshot_bus=realtime_snapshot_bus,
                    audit_store=late_session_audit_store,
                    clock=lambda: datetime.now(timezone.utc),
                )
                application.state.stock_timeline_service = StockTimelineService(
                    bar_repository,
                    news_repository,
                )
                application.state.a_share_cockpit_service = StockDecisionCockpitService(
                    a_share_instrument_directory,
                    application.state.a_share_diagnosis_service,
                    decision_repository,
                    preparation_service=application.state.a_share_preparation_service,
                    trading_calendar=trading_calendar,
                    operations_repository=operations_repository,
                    assessor_ai=ReloadableAssessmentGateway(
                        effective_ai_settings,
                        client=client,
                    ),
                )
                if is_portable_runtime:
                    history_symbol_reconciliation_task = asyncio.create_task(
                        _schedule_history_symbol_reconciliation(
                            history_sync_executor,
                            _reconcile_history_symbols,
                            (
                                bar_repository,
                                a_share_instrument_directory,
                                datetime.now(timezone.utc).date(),
                            ),
                            delay_seconds=PORTABLE_HISTORY_RECONCILIATION_DELAY_SECONDS,
                        ),
                        name="portable-history-symbol-reconciliation",
                    )
                else:
                    history_sync_executor.submit(
                        _reconcile_history_symbols,
                        bar_repository,
                        a_share_instrument_directory,
                        datetime.now(timezone.utc).date(),
                    )
                log_startup_stage("history-symbol-reconciliation-scheduled")
                if should_refresh_universe:
                    universe_refresh_task = asyncio.create_task(
                        _refresh_a_share_universe(
                            compliance,
                            application.state.a_share_universe_source,
                            a_share_instrument_directory,
                        ),
                        name="a-share-universe-refresh",
                    )
                    log_startup_stage("a-share-universe-refresh-scheduled")
                scheduler_task = (
                    asyncio.create_task(_scheduler_loop(
                        application.state.scheduler,
                        write_gate,
                        settings.scheduler_interval_seconds,
                    ))
                    if getattr(settings, "scheduler_enabled", False) else None
                )
                log_startup_stage("lifespan-ready")
                yield
            finally:
                if local_source_discovery_task is not None:
                    local_source_discovery_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await local_source_discovery_task
                if universe_refresh_task is not None:
                    universe_refresh_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await universe_refresh_task
                if bond_universe_refresh_task is not None:
                    bond_universe_refresh_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await bond_universe_refresh_task
                if scheduler_task is not None:
                    scheduler_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await scheduler_task
                if sector_fund_flow_sampling_task is not None:
                    sector_fund_flow_sampling_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await sector_fund_flow_sampling_task
                if source_health_snapshot_task is not None:
                    source_health_snapshot_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await source_health_snapshot_task
                realtime_ai_trigger_queue = getattr(
                    application.state, "realtime_ai_trigger_queue", None
                )
                if realtime_ai_trigger_queue is not None:
                    realtime_ai_trigger_queue.close()
                if tdx_auto_import_task is not None:
                    tdx_auto_import_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await tdx_auto_import_task
                if full_market_history_service is not None:
                    full_market_history_service.request_shutdown()
                if local_tdx_overview_source is not None:
                    local_tdx_overview_source.close()
                quant_strategy_service = getattr(
                    application.state, "quant_strategy_service", None
                )
                if quant_strategy_service is not None:
                    quant_strategy_service.close()
                market_overview_service = getattr(
                    application.state, "market_overview_service", None
                )
                if market_overview_service is not None:
                    market_overview_service.close()
                company_research_service = getattr(
                    application.state, "company_research_service", None
                )
                if company_research_service is not None:
                    company_research_service.close()
                company_research_task_service = getattr(
                    application.state, "company_research_task_service", None
                )
                if company_research_task_service is not None:
                    company_research_task_service.close()
                company_research_ai_task_service = getattr(
                    application.state, "company_research_ai_task_service", None
                )
                if company_research_ai_task_service is not None:
                    company_research_ai_task_service.close()
                if local_market_review_source is not None:
                    local_market_review_source.close()
                if history_symbol_reconciliation_task is not None:
                    history_symbol_reconciliation_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await history_symbol_reconciliation_task
                history_supplement_executor.shutdown(wait=True, cancel_futures=True)
                tdx_import_executor.shutdown(wait=True, cancel_futures=True)
                history_sync_executor.shutdown(wait=True, cancel_futures=True)
                application.state.history_supplement_service.close()
                history_sync_repository.close()
                tdx_import_repository.close()
                bond_repository.close()
                bond_universe_repository.close()
                diagnosis_repository.close()
                news_repository.close()
                stock_classification_repository.close()
                fund_flow_repository.close()
                sector_fund_flow_repository.close()
                research_enrichment_repository.close()
                company_research_version_repository.close()
                company_research_ai_result_repository.close()
                briefing_repository.close()
                compliance.close()
                audit_repository.close()
                operations_repository.close()
                data_lineage_repository.close()
                replay_snapshot_store.close()
                late_session_audit_store.close()
                observability_store.close()
                candidate_sentiment_repository.close()
                a_share_research_repository.close()
                if market_sentiment_repository is not None:
                    market_sentiment_repository.close()
                a_share_instrument_directory.close()
                poll_state_repository.close()
                decision_repository.close()
    engine.dispose()


app = FastAPI(title="一树电子商务-A股观测台", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def serialize_runtime_access(request: Request, call_next):
    request_started = time.perf_counter()
    write_gate = getattr(request.app.state, "write_gate", None)
    path = request.url.path
    response = None
    try:
        if (
            write_gate is None
            or request.method in {"GET", "HEAD", "OPTIONS"}
            or path == "/health"
            or path.startswith("/api/v1/settings/")
        ):
            response = await call_next(request)
        else:
            async with write_gate:
                response = await call_next(request)
        return response
    finally:
        store = getattr(request.app.state, "performance_store", None)
        if store is not None and path.startswith("/api/") and path != "/api/v1/operations/performance":
            latency_ms = round((time.perf_counter() - request_started) * 1000)
            success = response is not None and response.status_code < 500
            async def persist_performance_sample() -> None:
                try:
                    await asyncio.to_thread(
                        store.record,
                        "api",
                        path,
                        latency_ms=latency_ms,
                        success=success,
                        cache_hit=(response.headers.get("X-Qibao-Cache") == "hit") if response is not None else None,
                    )
                except Exception:
                    logger.debug("performance sample write failed", exc_info=True)

            asyncio.create_task(persist_performance_sample())
app.include_router(health_router)
app.include_router(research_router)
app.include_router(data_router)
app.include_router(backtest_router)
app.include_router(xingbu_router)
app.include_router(libu_router)
app.include_router(dongchang_router)
app.include_router(convertible_bonds_router)
app.include_router(news_router)
app.include_router(event_impact_router)
app.include_router(briefings_router)
app.include_router(operations_router)
app.include_router(decisions_router)
app.include_router(settings_router)
app.include_router(market_sentiment_router)
app.include_router(market_overview_router)
app.include_router(quant_strategy_router)
app.include_router(quant_research_router)
app.include_router(late_session_selection_router)
app.include_router(walk_forward_router)
app.include_router(portfolio_risk_router)
app.include_router(watchlist_risk_router)
app.include_router(first_limit_up_router)
app.include_router(tdx_local_router)
app.include_router(speech_router)
install_static_frontend(app, Settings().web_dir)
