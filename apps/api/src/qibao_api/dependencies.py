from datetime import datetime, timezone

from fastapi import Request

from qibao_api.gongbu.data_service import MarketDataService
from qibao_api.shangshu.pipeline import ResearchPipeline
from qibao_api.libu_compliance.repository import ComplianceRepository
from qibao_api.dongchang.repository import AuditFindingRepository


def get_pipeline(request: Request) -> ResearchPipeline:
    return request.app.state.pipeline


def get_market_data_service(request: Request) -> MarketDataService:
    return request.app.state.market_data_service


def get_full_market_history_service(request: Request):
    return request.app.state.full_market_history_service


def get_history_sync_executor(request: Request):
    return request.app.state.history_sync_executor


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


def get_a_share_diagnosis_service(request: Request):
    return request.app.state.a_share_diagnosis_service


def get_a_share_cockpit_service(request: Request):
    return request.app.state.a_share_cockpit_service


def get_company_research_service(request: Request):
    return request.app.state.company_research_service


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
