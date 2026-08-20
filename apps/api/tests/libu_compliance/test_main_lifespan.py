import asyncio
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

import qibao_api.main as main_module
from qibao_api.a_shares.market_sentiment import (
    MarketSentimentService,
    MarketSentimentWrongPhase,
)
from qibao_api.a_shares.market_sentiment_repository import MarketSentimentRepository
from qibao_api.a_shares.candidate_sentiment import CandidateSentimentEvaluator
from qibao_api.a_shares.candidate_sentiment_repository import (
    CandidateSentimentRepository,
    CandidateSentimentStoreError,
)
from qibao_api.a_shares.candidate_sentiment_service import CandidateSentimentService
from qibao_api.a_shares.company_research_ai_cache import (
    CompanyResearchAIResultRepository,
    CompanyResearchAIResultStoreError,
)
from qibao_api.a_shares.company_research_ai_tasks import CompanyResearchAITaskService
from qibao_api.a_shares.company_research_versions import (
    CompanyResearchVersionRepository,
    CompanyResearchVersionStoreError,
)
from qibao_api.operations.shared_snapshots import SharedSnapshotRegistry
from qibao_api.gongbu.fund_flow import FundFlowRepository
from qibao_api.gongbu.stock_news_sources import CompositeStockNewsSource
from qibao_api.gongbu.tdx_local_daily import LocalTdxMarketSentimentSource
from qibao_api.libu_compliance.guard import (
    AuthorizedFundFlowSource,
    AuthorizedHistorySource,
    AuthorizedQuoteSource,
)
from qibao_api.libu_compliance.repository import ComplianceRepository
from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.local_sources.discovery import LocalTerminalDiscoveryResult
from qibao_api.local_sources.repository import LocalSourceSettingsRepository
from qibao_api.shangshu.decision_repository import DecisionRepository
from qibao_api.shangshu.decision_runtime import (
    DecisionPhaseRunner,
    DeterministicIntradayEvaluator,
    RepositoryCandidateFactorSource,
    RepositoryComplianceSource,
    RepositoryEvidenceSource,
    RepositoryMarketOutcomeSource,
    RepositoryRiskSource,
    TencentPollingMarketFeed,
)
from qibao_api.zhongshu.news_ai import ReloadableNewsAIGateway
from qibao_api.zhongshu.decision_ai import ReloadableDecisionAIGateway


class FakeSettings:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'qibao.db').as_posix()}"


def test_runtime_tick_runs_fixed_slots_and_layered_intraday_once_serially() -> None:
    calls = []
    scheduler = type("Scheduler", (), {
        "tick": lambda _self, now: calls.append(("fixed", now)),
        "tick_intraday": lambda _self, now: calls.append(("layered", now)),
    })()
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)

    main_module._runtime_tick(scheduler, now)

    assert calls == [("fixed", now), ("layered", now)]


def test_initial_market_sentiment_refresh_is_submitted_to_background() -> None:
    calls = []

    class Executor:
        def submit(self, function, *args):
            calls.append((function, args))

    service = object()
    now = datetime(2026, 7, 30, tzinfo=timezone.utc)

    main_module._defer_initial_market_sentiment_refresh(Executor(), service, now)

    assert calls == [(main_module._refresh_market_sentiment, (service, now))]


def test_initial_market_sentiment_refresh_is_not_submitted_before_session() -> None:
    assert not main_module._should_defer_initial_market_sentiment_refresh(
        datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
    )
    assert main_module._should_defer_initial_market_sentiment_refresh(
        datetime(2026, 8, 7, 2, 0, tzinfo=timezone.utc)
    )


def test_initial_market_sentiment_refresh_skips_expected_premarket_phase_without_traceback(caplog) -> None:
    class Service:
        def refresh(self, _now):
            raise MarketSentimentWrongPhase("before session")

    caplog.set_level("INFO", logger="qibao_api.main")

    main_module._refresh_market_sentiment(
        Service(), datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
    )

    record = next(item for item in caplog.records if item.message == "initial market sentiment refresh skipped outside session")
    assert record.exc_info is None


@pytest.mark.asyncio
async def test_lifespan_uses_cached_local_discovery_without_waiting_for_rescan(
    tmp_path, monkeypatch
) -> None:
    scan_started = threading.Event()
    release_scan = threading.Event()
    cached = LocalTerminalDiscoveryResult(
        scanned_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
        terminals=(),
        active_tdx_vipdoc=None,
        settings=LocalSourceSettings(auto_discovery=True),
    )

    class SlowDiscovery:
        def inspect(self, settings):
            scan_started.set()
            release_scan.wait(timeout=5)
            return LocalTerminalDiscoveryResult(
                scanned_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
                terminals=(),
                active_tdx_vipdoc=None,
                settings=settings,
            )

    class SnapshotRepository:
        def __init__(self, _path) -> None:
            pass

        def load(self, settings):
            assert settings == cached.settings
            return cached

        def save(self, _snapshot) -> None:
            pass

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(main_module, "LocalTerminalDiscovery", SlowDiscovery)
    monkeypatch.setattr(
        main_module,
        "LocalTerminalDiscoverySnapshotRepository",
        SnapshotRepository,
    )
    monkeypatch.setattr(
        main_module,
        "create_tdx_client",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    application = FastAPI()
    manager = main_module.lifespan(application)
    entering = asyncio.create_task(manager.__aenter__())
    await asyncio.wait_for(asyncio.to_thread(scan_started.wait, 1), timeout=2)

    try:
        await asyncio.wait_for(asyncio.shield(entering), timeout=2)
        assert application.state.local_source_discovery_result == cached
    finally:
        release_scan.set()
        await entering
        await manager.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_history_symbol_reconciliation_can_be_deferred_and_cancelled() -> None:
    started = threading.Event()
    executor = ThreadPoolExecutor(max_workers=1)

    def reconcile(*_args) -> None:
        started.set()

    task = asyncio.create_task(
        main_module._schedule_history_symbol_reconciliation(
            executor,
            reconcile,
            (object(), object(), object(), object()),
            delay_seconds=0.05,
        )
    )
    try:
        assert not started.wait(0.01)
        await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=2)
        await task
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        executor.shutdown(wait=True, cancel_futures=True)


@pytest.mark.asyncio
async def test_sector_fund_flow_sampling_runs_off_request_path_and_uses_session_interval() -> None:
    delays: list[float] = []
    calls = 0

    class Service:
        async def sync(self):
            nonlocal calls
            calls += 1

    async def controlled_sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) >= 2:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await main_module._sector_fund_flow_sampling_loop(
            Service(),
            clock=lambda: datetime(2026, 8, 10, 2, 30, tzinfo=timezone.utc),
            sleep=controlled_sleep,
            initial_delay_seconds=5,
            intraday_interval_seconds=60,
            idle_interval_seconds=900,
        )

    assert calls == 1
    assert delays == [5, 60]


@pytest.mark.asyncio
async def test_lifespan_does_not_wait_for_remote_universe_refresh(
    tmp_path, monkeypatch
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    cancelled = asyncio.Event()

    class SlowUniverseSource:
        def __init__(self, *_sources) -> None:
            pass

        async def fetch(self):
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return ()

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(main_module, "FallbackAShareUniverseSource", SlowUniverseSource)
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    application = FastAPI()
    manager = main_module.lifespan(application)
    entering = asyncio.create_task(manager.__aenter__())
    await asyncio.wait_for(started.wait(), timeout=2)
    try:
        await asyncio.sleep(0)
        assert entering.done()
    finally:
        if not entering.done():
            release.set()
        await entering
        await manager.__aexit__(None, None, None)

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_lifespan_does_not_wait_for_remote_bond_universe_refresh(
    tmp_path, monkeypatch
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_sync_universe(_service):
        started.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(
        main_module.ConvertibleBondService,
        "sync_universe",
        slow_sync_universe,
    )
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    application = FastAPI()
    manager = main_module.lifespan(application)
    entering = asyncio.create_task(manager.__aenter__())
    await asyncio.wait_for(started.wait(), timeout=2)
    try:
        await asyncio.sleep(0)
        assert entering.done()
    finally:
        if not entering.done():
            release.set()
        await entering
        await manager.__aexit__(None, None, None)

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_lifespan_injects_guarded_production_sources_and_closes_compliance(
    tmp_path, monkeypatch
) -> None:
    tdx_overview_calls = []
    market_review_calls = []
    sector_sampling_calls = []

    class LocalOverviewSource:
        def __init__(self, **kwargs) -> None:
            tdx_overview_calls.append(("init", kwargs))

        def refresh(self):
            tdx_overview_calls.append(("refresh",))
            return None

        def start(self) -> None:
            tdx_overview_calls.append(("start",))

        def current(self):
            return None

        def close(self) -> None:
            tdx_overview_calls.append(("close",))

    class MarketReviewSource:
        def __init__(self, **kwargs) -> None:
            market_review_calls.append(("init", kwargs))

        def refresh(self, **kwargs):
            market_review_calls.append(("refresh", kwargs))
            return None

        def start(self) -> None:
            market_review_calls.append(("start",))

        def current(self):
            return None

        def close(self) -> None:
            market_review_calls.append(("close",))

    async def sector_sampling_loop(_service, **kwargs) -> None:
        sector_sampling_calls.append(kwargs)
        await asyncio.Event().wait()

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setenv("QIBAO_PORTABLE_ROOT", str(tmp_path))
    tdx_home = tmp_path / "preferred-tdx"
    (tdx_home / "vipdoc" / "sh" / "lday").mkdir(parents=True)
    (tdx_home / "vipdoc" / "sz" / "lday").mkdir(parents=True)
    LocalSourceSettingsRepository(
        tmp_path / "config" / "data-sources.json"
    ).save(LocalSourceSettings(
        auto_discovery=False,
        tdx_install_paths=(tdx_home,),
    ))
    monkeypatch.setattr(main_module, "LocalTdxOverviewSource", LocalOverviewSource)
    monkeypatch.setattr(main_module, "LocalMarketReviewSource", MarketReviewSource)
    monkeypatch.setattr(
        main_module,
        "_sector_fund_flow_sampling_loop",
        sector_sampling_loop,
    )
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    application = FastAPI()

    async with main_module.lifespan(application):
        compliance = application.state.compliance_repository
        assert isinstance(compliance, ComplianceRepository)
        assert isinstance(application.state.pipeline.quote_source, AuthorizedQuoteSource)
        fallback = application.state.market_data_service.source
        assert len(fallback.sources) == 2
        assert all(isinstance(source, AuthorizedHistorySource) for source in fallback.sources)
        assert fallback.sources[0]._source.client_factory is main_module.create_tdx_client
        assert len(compliance.list_feature_source_history("realtime_quotes", "a_share")) == 1
        assert compliance.list_feature_source_history("paper_orders", "a_share") == []
        assert len(compliance.list_feature_source_history("history_sync.baidu", "a_share")) == 1
        market_news_sources = compliance.list_feature_source_history(
            "market_news", "a_share"
        )
        assert {item.source for item in market_news_sources} == {
            "cninfo",
            "eastmoney",
            "tencent",
        }
        assert len(
            compliance.list_feature_source_history("market_hotspots", "a_share")
        ) == 1
        assert len(
            compliance.list_feature_source_history("stock_classification", "a_share")
        ) == 1
        assert len(
            compliance.list_feature_source_history("stock_fund_flow", "a_share")
        ) == 1
        assert compliance.check_feature_sources("realtime_quotes", "a_share").allowed
        assert compliance.check_feature_sources("market_news", "a_share").allowed
        assert compliance.check_feature_sources("market_hotspots", "a_share").allowed
        assert compliance.check_feature_sources(
            "bond_quotes", "convertible_bond"
        ).allowed
        assert compliance.check_feature_sources(
            "bond_clauses", "convertible_bond"
        ).allowed
        news_repository = application.state.news_repository
        assert application.state.news_service.repository is news_repository
        assert application.state.hotspot_service.repository is news_repository
        assert (
            application.state.hotspot_service.source.client
            is application.state.decision_market_feed.client
        )
        assert isinstance(
            application.state.news_service.stock_source,
            CompositeStockNewsSource,
        )
        assert tuple(
            source.source_name
            for source in application.state.news_service.stock_source.sources
        ) == (
            "tencent-stock-news",
            "cninfo-announcements",
            "eastmoney-stock-news",
        )
        assert isinstance(
            application.state.news_service.ai_gateway, ReloadableNewsAIGateway
        )
        assert (
            application.state.news_service.ai_gateway._settings
            is application.state.effective_ai_settings
        )
        assert "银行" in application.state.news_service.linker.industry_keywords
        assert "人工智能" in application.state.news_service.linker.theme_keywords
        classification_repository = application.state.stock_classification_repository
        assert (
            application.state.a_share_diagnosis_service.classification_repository
            is classification_repository
        )
        assert (
            application.state.a_share_preparation_service.classification_service.repository
            is classification_repository
        )
        fund_flow_repository = application.state.fund_flow_repository
        assert isinstance(fund_flow_repository, FundFlowRepository)
        assert (
            application.state.a_share_diagnosis_service.fund_flow_repository
            is fund_flow_repository
        )
        assert (
            application.state.a_share_preparation_service.fund_flow_service.repository
            is fund_flow_repository
        )
        assert isinstance(
            application.state.fund_flow_service.source,
            AuthorizedFundFlowSource,
        )
        briefing_repository = application.state.briefing_repository
        assert application.state.briefing_workflow.briefing_repository is briefing_repository
        decision_repository = application.state.decision_repository
        assert isinstance(decision_repository, DecisionRepository)
        assert application.state.decision_phase_runner.repository is decision_repository
        assert isinstance(application.state.decision_phase_runner, DecisionPhaseRunner)
        assert isinstance(application.state.decision_candidate_source, RepositoryCandidateFactorSource)
        assert isinstance(application.state.decision_compliance_source, RepositoryComplianceSource)
        assert isinstance(application.state.decision_risk_source, RepositoryRiskSource)
        assert isinstance(application.state.decision_evidence_source, RepositoryEvidenceSource)
        assert isinstance(application.state.decision_market_feed, TencentPollingMarketFeed)
        assert isinstance(application.state.decision_evaluator, DeterministicIntradayEvaluator)
        assert isinstance(application.state.decision_outcome_source, RepositoryMarketOutcomeSource)
        assert application.state.scheduler.decision_workflow is application.state.decision_phase_runner
        assert application.state.scheduler.intraday_monitor is application.state.intraday_monitor
        assert isinstance(
            application.state.market_sentiment_service, MarketSentimentService
        )
        assert isinstance(
            application.state.market_sentiment_repository,
            MarketSentimentRepository,
        )
        assert isinstance(
            application.state.market_sentiment_service.source,
            LocalTdxMarketSentimentSource,
        )
        assert (
            application.state.scheduler.market_sentiment_service
            is application.state.market_sentiment_service
        )
        assert application.state.local_tdx_overview_source is not None
        assert application.state.local_source_discovery_result.active_tdx_vipdoc == (
            tdx_home / "vipdoc"
        )
        assert application.state.market_overview_service.local_market_source is (
            application.state.local_tdx_overview_source
        )
        assert application.state.market_overview_service.initial_refresh_delay_seconds == 1
        assert (
            application.state.late_session_selection_service.audit_store
            is application.state.late_session_audit_store
        )
        assert isinstance(
            application.state.candidate_sentiment_service,
            CandidateSentimentService,
        )
        assert isinstance(
            application.state.candidate_sentiment_repository,
            CandidateSentimentRepository,
        )
        assert isinstance(
            application.state.candidate_sentiment_service.evaluator,
            CandidateSentimentEvaluator,
        )
        assert (
            application.state.candidate_sentiment_service.research_repository
            is application.state.a_share_research_repository
        )
        assert (
            application.state.candidate_sentiment_service.news_ingestion_service
            is application.state.news_service
        )
        assert (
            application.state.candidate_sentiment_service.hotspot_ingestion_service
            is application.state.hotspot_service
        )
        assert (
            application.state.candidate_sentiment_service.fund_flow_service
            is application.state.fund_flow_service
        )
        candidate_sentiment_repository = (
            application.state.candidate_sentiment_repository
        )
        sentiment_repository = application.state.market_sentiment_repository
        premarket_ai = application.state.decision_phase_runner.premarket.ai_gateway
        assert isinstance(premarket_ai, ReloadableDecisionAIGateway)
        assert premarket_ai._settings is application.state.effective_ai_settings
        assert premarket_ai._client is application.state.decision_market_feed.client
        assert application.state.intraday_monitor.ai_gateway is premarket_ai
        assert application.state.decision_phase_runner.postclose.ai_gateway is premarket_ai
        company_research_version_repository = (
            application.state.company_research_version_repository
        )
        company_research_ai_result_repository = (
            application.state.company_research_ai_result_repository
        )
        company_research_ai_task_service = (
            application.state.company_research_ai_task_service
        )
        shared_snapshot_registry = application.state.shared_snapshot_registry
        assert isinstance(shared_snapshot_registry, SharedSnapshotRegistry)
        assert (
            application.state.performance_store.shared_snapshot_registry
            is shared_snapshot_registry
        )
        assert (
            application.state.market_overview_service.shared_snapshot_registry
            is shared_snapshot_registry
        )
        assert (
            company_research_version_repository.shared_snapshot_registry
            is shared_snapshot_registry
        )
        assert (
            application.state.quant_strategy_service.shared_snapshot_registry
            is shared_snapshot_registry
        )
        assert isinstance(
            company_research_version_repository,
            CompanyResearchVersionRepository,
        )
        assert isinstance(
            company_research_ai_result_repository,
            CompanyResearchAIResultRepository,
        )
        assert isinstance(
            company_research_ai_task_service,
            CompanyResearchAITaskService,
        )
        assert (
            company_research_ai_task_service.result_repository
            is company_research_ai_result_repository
        )

    assert [call[0] for call in tdx_overview_calls] == ["init", "start", "close"]
    assert tdx_overview_calls[0][1]["fallback"] is not None
    assert tdx_overview_calls[0][1]["rpc"] is None
    assert tdx_overview_calls[0][1]["initial_delay_seconds"] == 15
    assert [call[0] for call in market_review_calls] == ["init", "start", "close"]
    assert market_review_calls[0][1]["initial_delay_seconds"] == 15
    assert market_review_calls[0][1]["defer_cache_validation"] is True
    assert sector_sampling_calls == [{"initial_delay_seconds": 30}]

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        compliance.list_feature_source_history("realtime_quotes", "a_share")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        news_repository.events()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        classification_repository.count()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        fund_flow_repository.count()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        briefing_repository.reports()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        decision_repository.cycles()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        sentiment_repository.latest()
    with pytest.raises(CandidateSentimentStoreError, match="read failed") as caught:
        candidate_sentiment_repository.latest("a" * 64)
    assert isinstance(caught.value.__cause__, sqlite3.ProgrammingError)
    with pytest.raises(CompanyResearchVersionStoreError, match="read failed") as caught:
        company_research_version_repository.latest("600519")
    assert isinstance(caught.value.__cause__, sqlite3.ProgrammingError)
    with pytest.raises(CompanyResearchAIResultStoreError, match="read failed") as caught:
        company_research_ai_result_repository.get("research-v1", ("configured", "model"))
    assert isinstance(caught.value.__cause__, sqlite3.ProgrammingError)


@pytest.mark.asyncio
async def test_lifespan_dependency_registration_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )

    async with main_module.lifespan(FastAPI()):
        pass
    async with main_module.lifespan(FastAPI()):
        pass

    repository = ComplianceRepository(tmp_path / "compliance.sqlite3")
    assert len(repository.list_feature_source_history("realtime_quotes", "a_share")) == 1
    assert len(repository.list_feature_source_history("history_sync.baidu", "a_share")) == 1
    assert len(repository.list_feature_source_history("stock_fund_flow", "a_share")) == 1
    assert len(repository.list_feature_source_history("market_hotspots", "a_share")) == 1


@pytest.mark.asyncio
async def test_lifespan_does_not_block_when_history_symbol_reconciliation_fails(
    tmp_path, monkeypatch
) -> None:
    closed = []

    class Directory:
        def __init__(self, _path) -> None:
            pass

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(main_module, "AShareInstrumentDirectory", Directory)
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    monkeypatch.setattr(
        main_module.BarRepository,
        "symbols_with_history",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("seed failed")),
    )

    async with main_module.lifespan(FastAPI()):
        pass

    assert closed == [True]


@pytest.mark.asyncio
async def test_lifespan_recovers_and_stops_full_market_history_worker(
    tmp_path, monkeypatch
) -> None:
    calls = []

    class Repository:
        def __init__(self, path) -> None:
            calls.append(("repository", path))

        def close(self) -> None:
            calls.append(("repository-close",))

    class Service:
        def __init__(self, **kwargs) -> None:
            self.jobs = kwargs["job_repository"]
            calls.append(("service", kwargs))

        def recover_interrupted(self) -> None:
            calls.append(("recover",))

        def current_job(self):
            return SimpleNamespace(job_id="history-sync-resume", state="pending")

        def run(self, job_id):
            calls.append(("run", job_id))

        def request_shutdown(self) -> None:
            calls.append(("request-shutdown",))

    class TdxRepository:
        def __init__(self, path) -> None:
            calls.append(("tdx-repository", path))

        def recover_interrupted(self) -> None:
            calls.append(("tdx-recover",))

        def current(self):
            return SimpleNamespace(job_id="tdx-import-resume", state="paused")

        def close(self) -> None:
            calls.append(("tdx-repository-close",))

    class TdxService:
        def __init__(self, _bar_repository, **kwargs) -> None:
            self.jobs = kwargs["job_repository"]
            self.after_import = None

        def current_job(self):
            return self.jobs.current()

        def run(self, job_id):
            calls.append(("tdx-run", job_id))

    class Executor:
        def __init__(self, **kwargs) -> None:
            calls.append(("executor", kwargs))

        def submit(self, function, *args):
            calls.append(("submit", function, args))

        def shutdown(self, *, wait, cancel_futures) -> None:
            calls.append(("executor-shutdown", wait, cancel_futures))

    monkeypatch.setattr(main_module, "Settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(main_module, "HistorySyncRepository", Repository)
    monkeypatch.setattr(main_module, "FullMarketHistoryService", Service)
    monkeypatch.setattr(main_module, "TdxImportRepository", TdxRepository)
    monkeypatch.setattr(main_module, "TdxLocalImportService", TdxService)
    monkeypatch.setattr(main_module, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(
        main_module, "create_tdx_client", lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    application = FastAPI()

    async with main_module.lifespan(application):
        assert application.state.full_market_history_service.current_job().job_id == (
            "history-sync-resume"
        )
        assert application.state.history_sync_executor is not None

    names = [call[0] for call in calls]
    resume_submit = (
        "submit",
        application.state.full_market_history_service.run,
        ("history-sync-resume",),
    )
    assert names.index("recover") < calls.index(resume_submit)
    assert resume_submit in calls
    assert ("submit", application.state.tdx_import_service.run, ("tdx-import-resume",)) not in calls
    assert len([call for call in calls if call[0] == "executor"]) == 3
    assert application.state.history_sync_executor is not application.state.tdx_import_executor
    assert application.state.history_sync_executor is not application.state.history_supplement_executor
    assert application.state.tdx_import_executor is not application.state.history_supplement_executor
    assert names.index("request-shutdown") < names.index("executor-shutdown")
    assert calls.count(("executor-shutdown", True, True)) == 3
    assert names.index("executor-shutdown") < names.index("repository-close")


def test_history_supplement_reconciliation_does_not_block_startup() -> None:
    calls: list[str] = []

    class Service:
        def reconcile_current_job(self) -> None:
            calls.append("reconcile")
            raise UnicodeDecodeError("utf-8", b"\xc1", 0, 1, "invalid start byte")

    main_module._reconcile_history_supplement(Service())

    assert calls == ["reconcile"]


def test_history_supplement_reconciliation_still_runs_when_available() -> None:
    calls: list[str] = []

    class Service:
        def reconcile_current_job(self) -> None:
            calls.append("reconcile")

    main_module._reconcile_history_supplement(Service())

    assert calls == ["reconcile"]
