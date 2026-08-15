from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import Request

from qibao_api.gongbu.data_service import MarketDataService
from qibao_api.shangshu.pipeline import ResearchPipeline
from qibao_api.libu_compliance.repository import ComplianceRepository
from qibao_api.dongchang.repository import AuditFindingRepository
from qibao_api.operations.read_model import OperationsReadModel
from qibao_api.tasks.progress import TaskProgressRegistry


_fallback_task_progress_registry = TaskProgressRegistry()


class _DisabledTdxAutoImportMonitor:
    def status(self):
        return {
            "state": "disabled",
            "last_poll_at": None,
            "last_change_at": None,
            "last_submitted_at": None,
            "submitted_job_id": None,
            "skip_reason": "not_initialized",
            "error": None,
            "file_count": 0,
        }


_disabled_tdx_auto_import_monitor = _DisabledTdxAutoImportMonitor()


def get_pipeline(request: Request) -> ResearchPipeline:
    return request.app.state.pipeline


def get_market_data_service(request: Request) -> MarketDataService:
    return request.app.state.market_data_service


def get_full_market_history_service(request: Request):
    return request.app.state.full_market_history_service


def get_history_sync_executor(request: Request):
    return request.app.state.history_sync_executor


def get_tdx_import_service(request: Request):
    return request.app.state.tdx_import_service


def get_tdx_import_executor(request: Request):
    return request.app.state.tdx_import_executor


def get_compliance_repository(request: Request) -> ComplianceRepository:
    return request.app.state.compliance_repository


def get_audit_repository(request: Request) -> AuditFindingRepository:
    return request.app.state.audit_repository


def get_bond_service(request: Request):
    return request.app.state.bond_service


def get_news_service(request: Request):
    return request.app.state.news_service


def get_hotspot_service(request: Request):
    return request.app.state.hotspot_service


def get_news_repository(request: Request):
    return request.app.state.news_repository


def get_event_impact_service(request: Request):
    return request.app.state.event_impact_service


def get_news_alert_service(request: Request):
    return request.app.state.news_alert_service


def get_briefing_workflow(request: Request):
    return request.app.state.briefing_workflow


def get_briefing_repository(request: Request):
    return request.app.state.briefing_repository


def get_scheduler(request: Request):
    return request.app.state.scheduler


def get_backup_service(request: Request):
    return request.app.state.backup_service


def get_operations_repository(request: Request):
    return request.app.state.operations_repository


def get_data_lineage_repository(request: Request):
    return request.app.state.data_lineage_repository


def get_operations_read_model(request: Request):
    configured = getattr(request.app.state, "operations_read_model", None)
    if configured is not None:
        return configured
    portable_root = os.environ.get("QIBAO_PORTABLE_ROOT")
    if portable_root:
        return OperationsReadModel(Path(portable_root))
    data_dir = Path(os.environ.get("QIBAO_DATA_DIR", "data")).resolve()
    return OperationsReadModel(data_dir.parent)


def get_tdx_auto_import_monitor(request: Request):
    return getattr(request.app.state, "tdx_auto_import_monitor", _disabled_tdx_auto_import_monitor)


def get_task_progress_registry(request: Request) -> TaskProgressRegistry:
    return getattr(
        request.app.state,
        "task_progress_registry",
        _fallback_task_progress_registry,
    )


def get_performance_store(request: Request):
    return request.app.state.performance_store


def get_observability_store(request: Request):
    return request.app.state.observability_store


def get_shared_snapshot_registry(request: Request):
    return getattr(request.app.state, "shared_snapshot_registry", None)


def get_replay_snapshot_store(request: Request):
    return request.app.state.replay_snapshot_store


def get_a_share_diagnosis_service(request: Request):
    return request.app.state.a_share_diagnosis_service


def get_a_share_cockpit_service(request: Request):
    return request.app.state.a_share_cockpit_service


def get_company_research_service(request: Request):
    return request.app.state.company_research_service


def get_company_research_task_service(request: Request):
    return request.app.state.company_research_task_service


def get_company_research_ai_task_service(request: Request):
    return request.app.state.company_research_ai_task_service


def get_company_research_version_repository(request: Request):
    return request.app.state.company_research_version_repository


def get_a_share_preparation_service(request: Request):
    return request.app.state.a_share_preparation_service


def get_stock_timeline_service(request: Request):
    return request.app.state.stock_timeline_service


def get_a_share_instrument_directory(request: Request):
    return request.app.state.a_share_instrument_directory


def get_a_share_quote_source(request: Request):
    return request.app.state.a_share_quote_source


def get_a_share_universe_source(request: Request):
    return request.app.state.a_share_universe_source


def get_market_sentiment_service(request: Request):
    return request.app.state.market_sentiment_service


def get_market_sentiment_repository(request: Request):
    return request.app.state.market_sentiment_repository


def get_market_overview_service(request: Request):
    return request.app.state.market_overview_service


def get_local_market_review_source(request: Request):
    return request.app.state.local_market_review_source


def get_quant_strategy_service(request: Request):
    return request.app.state.quant_strategy_service


def get_quant_shadow_ledger(request: Request):
    return request.app.state.quant_shadow_ledger


def get_decision_journal(request: Request):
    return request.app.state.decision_journal


def get_portfolio_risk_service(request: Request):
    return request.app.state.portfolio_risk_service


def get_portfolio_risk_store(request: Request):
    return request.app.state.portfolio_risk_store


def get_watchlist_risk_service(request: Request):
    return request.app.state.watchlist_risk_service


def get_candidate_sentiment_service(request: Request):
    return request.app.state.candidate_sentiment_service


def get_first_limit_up_service(request: Request):
    return request.app.state.first_limit_up_service


def get_kronos_forecast_service(request: Request):
    return request.app.state.kronos_forecast_service


def get_tdx_ipo_source(request: Request):
    return request.app.state.tdx_ipo_source


def get_tdx_formula_source(request: Request):
    return request.app.state.tdx_formula_source


def get_tdx_professional_source(request: Request):
    return request.app.state.tdx_professional_source


def get_decision_repository(request: Request):
    return request.app.state.decision_repository


def get_decision_calendar(request: Request):
    return request.app.state.decision_calendar


def get_decision_poll_state(request: Request):
    repository = getattr(request.app.state, "poll_state_repository", None)
    return repository.latest() if repository is not None else None


def get_poll_state_repository(request: Request):
    return getattr(request.app.state, "poll_state_repository", None)


def get_server_time() -> datetime:
    return datetime.now(timezone.utc)
