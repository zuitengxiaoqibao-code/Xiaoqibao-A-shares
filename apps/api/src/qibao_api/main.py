import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from sqlalchemy import create_engine

from qibao_api.a_shares.diagnosis import AShareDiagnosisService
from qibao_api.a_shares.company_research import CompanyResearchService
from qibao_api.a_shares.cockpit import StockDecisionCockpitService
from qibao_api.a_shares.assessment_ai import ReloadableAssessmentGateway
from qibao_api.a_shares.fundamentals import TdxFinanceSource
from qibao_api.a_shares.instrument_directory import AShareInstrument, AShareInstrumentDirectory
from qibao_api.a_shares.market_sentiment import (
    MarketSentimentFactorBuilder,
    MarketSentimentEvaluator,
    MarketSentimentService,
)
from qibao_api.a_shares.market_sentiment_repository import (
    MarketSentimentRepository,
)
from qibao_api.a_shares.market_overview import MarketOverviewService
from qibao_api.a_shares.quant_strategy import (
    ArchivedTriggerEvidenceSource,
    QuantStrategyService,
)
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
from qibao_api.gongbu.baidu_history import BaiduHistorySource
from qibao_api.gongbu.sina_financials import SinaFinancialHistorySource
from qibao_api.gongbu.tdx_company_profile import TdxCompanyProfileSource
from qibao_api.gongbu.data_service import FallbackHistorySource, MarketDataService
from qibao_api.gongbu.full_market_history import FullMarketHistoryService
from qibao_api.gongbu.history_sync_repository import HistorySyncRepository
from qibao_api.gongbu.tdx_client import create_tdx_client
from qibao_api.gongbu.tdx_history import TdxHistorySource
from qibao_api.gongbu.tdx_local_overview import (
    LocalTdxOverviewSource,
    TdxJsonRpcClient,
)
from qibao_api.gongbu.tdx_local_calendar import TdxLocalIpoSource
from qibao_api.gongbu.tdx_formula import TdxLocalFormulaSource
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
from qibao_api.local_sources.discovery import LocalTerminalDiscovery
from qibao_api.local_sources.repository import LocalSourceSettingsRepository
from qibao_api.gongbu.tencent_quotes import TencentQuoteSource, market_prefix
from qibao_api.gongbu.tencent_overview import TencentOverviewSource
from qibao_api.convertible_bonds.adapters import (
    EastmoneyBondUniverseSource,
    EastmoneyBondValuationSource,
    EastmoneyClauseSource,
    TencentBondQuoteSource,
)
from qibao_api.convertible_bonds.tdx_local import FallbackClauseSource, TdxLocalClauseSource
from qibao_api.convertible_bonds.repository import BondClauseRepository
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
from qibao_api.routes.first_limit_up import router as first_limit_up_router
from qibao_api.routes.tdx_local import router as tdx_local_router
from qibao_api.routes.speech import router as speech_router
from qibao_api.settings import Settings
from qibao_api.static_frontend import install_static_frontend
from qibao_api.settings_repository import AISettingsRepository, EffectiveAISettingsResolver
from qibao_api.speech.edge_tts_service import EdgeTTSService
from qibao_api.speech.settings_repository import SpeechSettingsRepository
from qibao_api.shangshu.pipeline import ResearchPipeline
from qibao_api.storage.database import create_schema
from qibao_api.storage.bar_repository import BarRepository
from qibao_api.storage.quote_repository import QuoteRepository
from qibao_api.xingbu.gate import RiskGate
from qibao_api.dongchang.repository import AuditFindingRepository
from qibao_api.routes.xingbu import router as xingbu_router
from qibao_api.routes.libu import router as libu_router
from qibao_api.routes.dongchang import router as dongchang_router
from qibao_api.routes.convertible_bonds import router as convertible_bonds_router
from qibao_api.routes.news import router as news_router
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
from qibao_api.shangshu.scheduler import DailyBriefingScheduler
from qibao_api.gongbu.backup_service import BackupService
from qibao_api.routes.operations import router as operations_router
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


def _refresh_market_sentiment(service, now: datetime) -> None:
    try:
        service.refresh(now)
    except Exception:
        logger.info("initial market sentiment refresh deferred", exc_info=True)


def _defer_initial_market_sentiment_refresh(executor, service, now: datetime) -> None:
    executor.submit(_refresh_market_sentiment, service, now)


async def _refresh_a_share_universe(compliance, source, directory) -> None:
    try:
        compliance.require_feature_sources("a_share_universe", "a_share")
        universe = await source.fetch()
        directory.observe_many(universe)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("A-share universe sync unavailable", exc_info=True)


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
    local_source_discovery_result = local_terminal_discovery.inspect(
        local_source_settings_record.settings
    )
    application.state.local_source_settings_repository = (
        local_source_settings_repository
    )
    application.state.local_terminal_discovery = local_terminal_discovery
    application.state.local_source_discovery_result = (
        local_source_discovery_result
    )
    log_startup_stage("local-sources-ready")
    application.state.edge_tts_service = EdgeTTSService(portable_root / "cache" / "tts")
    engine = create_engine(settings.database_url)
    create_schema(engine)
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
    application.state.operations_repository = operations_repository
    log_startup_stage("repositories-ready")

    async with httpx.AsyncClient(timeout=10) as client:
        application.state.a_share_quote_source = TencentQuoteSource(client)
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
            application.state.first_limit_up_service = FirstLimitUpService(
                bar_repository=bar_repository,
                quote_source=SynchronousTencentQuoteSource(history_client, compliance),
                repository=first_limit_up_repository,
                universe_provider=lambda: (
                    application.state.a_share_instrument_directory.active_symbols()
                ),
            )
            trading_calendar = StoredTradingCalendar(
                bar_repository,
                live_signal=TencentIndexTradingDaySignal(history_client),
                schedule=ExchangeCalendarsTradingDaySchedule(),
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
            application.state.company_research_service = CompanyResearchService(
                application.state.a_share_diagnosis_service,
                SinaFinancialHistorySource(client=history_client),
                TdxCompanyProfileSource(client_factory=create_tdx_client),
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
            try:
                await application.state.bond_service.sync_universe()
            except Exception:
                logger.warning("convertible-bond universe sync unavailable", exc_info=True)
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
            history_sync_executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="history-sync",
            )
            application.state.history_sync_repository = history_sync_repository
            application.state.history_sync_executor = history_sync_executor
            full_market_history_service = None
            market_sentiment_repository = None
            local_tdx_overview_source = None
            local_market_review_source = None
            try:
                application.state.a_share_instrument_directory = a_share_instrument_directory
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
                )
                application.state.full_market_history_service = (
                    full_market_history_service
                )
                application.state.scheduler.full_market_history_service = (
                    full_market_history_service
                )
                application.state.scheduler.history_sync_submitter = (
                    history_sync_executor.submit
                )
                full_market_history_service.recover_interrupted()
                interrupted_job = full_market_history_service.current_job()
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
                vipdoc_root = local_source_discovery_result.active_tdx_vipdoc
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
                local_tdx_overview_source = LocalTdxOverviewSource(
                    cache_path=portable_root / "cache" / "tdx-market-overview.json",
                    rpc=tdx_rpc,
                    clock=lambda: datetime.now(timezone.utc),
                    refresh_seconds=5,
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
                local_tdx_overview_source.start()
                local_market_review_source = LocalMarketReviewSource(
                    vipdoc_root=vipdoc_root,
                    cache_path=settings.data_dir / "market-review" / "latest.json",
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
                )
                application.state.local_market_review_source = (
                    local_market_review_source
                )
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
                if (
                    is_portable_runtime
                    and local_tdx_overview_source.current() is not None
                ):
                    _defer_initial_market_sentiment_refresh(
                        history_sync_executor,
                        application.state.market_sentiment_service,
                        datetime.now(timezone.utc),
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
                )
                application.state.quant_strategy_service = QuantStrategyService(
                    application.state.market_overview_service,
                    application.state.a_share_diagnosis_service,
                    a_share_instrument_directory,
                    ArchivedTriggerEvidenceSource(
                        poll_state_repository,
                        fund_flow_repository,
                    ),
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
                if universe_refresh_task is not None:
                    universe_refresh_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await universe_refresh_task
                if scheduler_task is not None:
                    scheduler_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await scheduler_task
                if full_market_history_service is not None:
                    full_market_history_service.request_shutdown()
                if local_tdx_overview_source is not None:
                    local_tdx_overview_source.close()
                if local_market_review_source is not None:
                    local_market_review_source.close()
                history_sync_executor.shutdown(wait=True, cancel_futures=True)
                history_sync_repository.close()
                bond_repository.close()
                bond_universe_repository.close()
                diagnosis_repository.close()
                news_repository.close()
                stock_classification_repository.close()
                fund_flow_repository.close()
                briefing_repository.close()
                compliance.close()
                audit_repository.close()
                operations_repository.close()
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
    write_gate = getattr(request.app.state, "write_gate", None)
    if write_gate is None:
        return await call_next(request)
    path = request.url.path
    if path == "/health":
        return await call_next(request)
    if path.startswith("/api/v1/settings/"):
        return await call_next(request)
    if request.method == "GET" and (
        path == "/api/v1/a-shares/candidates"
        or (
            path.startswith("/api/v1/a-shares/")
            and path.endswith(("/diagnosis", "/cockpit", "/timeline"))
        )
    ):
        return await call_next(request)
    async with write_gate:
        return await call_next(request)
app.include_router(health_router)
app.include_router(research_router)
app.include_router(data_router)
app.include_router(backtest_router)
app.include_router(xingbu_router)
app.include_router(libu_router)
app.include_router(dongchang_router)
app.include_router(convertible_bonds_router)
app.include_router(news_router)
app.include_router(briefings_router)
app.include_router(operations_router)
app.include_router(decisions_router)
app.include_router(settings_router)
app.include_router(market_sentiment_router)
app.include_router(market_overview_router)
app.include_router(quant_strategy_router)
app.include_router(first_limit_up_router)
app.include_router(tdx_local_router)
app.include_router(speech_router)
install_static_frontend(app, Settings().web_dir)
