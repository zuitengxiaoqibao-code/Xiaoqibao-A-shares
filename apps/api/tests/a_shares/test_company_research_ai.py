import json
from datetime import datetime, timezone

import httpx

from qibao_api.a_shares.company_research_ai import CompanyResearchAIGateway, ReloadableCompanyResearchAIGateway
from qibao_api.contracts.company_research import CompanyResearchAIRequest, CompanyResearchAIEvidence
from qibao_api.settings_repository import AISettings, AISettingsRepository, EffectiveAISettingsResolver


NOW = datetime(2026, 8, 12, 15, tzinfo=timezone.utc)


def request() -> CompanyResearchAIRequest:
    return CompanyResearchAIRequest(
        snapshot_id="research-v2",
        symbol="600519",
        generated_at=NOW,
        evidence=(
            CompanyResearchAIEvidence(evidence_id="cash-1", section="利润质量", summary="经营现金流覆盖净利润"),
            CompanyResearchAIEvidence(evidence_id="risk-1", section="反方风险", summary="估值处于高风险阈值"),
        ),
        deterministic_conclusions=("利润质量证据已核验", "估值风险规则已触发"),
    )


def test_company_research_ai_accepts_only_frozen_evidence_and_returns_structured_counter_case() -> None:
    class Provider:
        def complete(self, _payload):
            return json.dumps({
                "executive_summary": "现金流证据支持利润质量，但估值风险仍需核验。",
                "contrary_risks": [
                    {"title": "估值压力", "detail": "当前规则已触发估值风险。", "evidence_ids": ["risk-1"]},
                ],
                "verification_questions": ["后续现金流能否继续覆盖利润？"],
            }, ensure_ascii=False)

    result = CompanyResearchAIGateway(Provider(), provider_name="test", model="model").analyze(request())

    assert result.status == "ready"
    assert result.snapshot_id == "research-v2"
    assert result.analysis is not None
    assert result.analysis.contrary_risks[0].evidence_ids == ("risk-1",)


def test_company_research_ai_rejects_unfrozen_evidence_or_trade_instructions() -> None:
    class Provider:
        def complete(self, _payload):
            return json.dumps({
                "executive_summary": "建议买入并设置止损。",
                "contrary_risks": [
                    {"title": "未知风险", "detail": "新增事实", "evidence_ids": ["outside"]},
                ],
                "verification_questions": [],
            }, ensure_ascii=False)

    result = CompanyResearchAIGateway(Provider(), provider_name="test", model="model").analyze(request())

    assert result.status == "invalid"
    assert result.analysis is None


def test_company_research_ai_exposes_rate_limit_without_hiding_frozen_research() -> None:
    http_request = httpx.Request("POST", "https://provider.example/v1/chat/completions")

    class Provider:
        def complete(self, _payload):
            raise httpx.HTTPStatusError(
                "limited", request=http_request,
                response=httpx.Response(429, request=http_request),
            )

    result = CompanyResearchAIGateway(
        Provider(), provider_name="openai-compatible", model="model",
    ).analyze(request())

    assert result.status == "http_error"
    assert result.ai_state == "rate_limited"
    assert result.ai_message == "AI 接口触发限流，稍后将自动重试"


def test_company_research_gateway_uses_long_read_timeout_for_real_model_latency(tmp_path) -> None:
    repository = AISettingsRepository(tmp_path)
    repository.save(AISettings(
        base_url="https://provider.example/v1",
        model="model-first",
        api_key="top-secret",
    ))
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200,
        json={"choices": [{"message": {"content": "{}"}}]},
    )))
    subject = ReloadableCompanyResearchAIGateway(
        EffectiveAISettingsResolver(repository), client,
    )

    assert subject._timeout >= 45
    client.close()
