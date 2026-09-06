import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from qibao_api.contracts.news import EvidenceCitation, NormalizedNewsEvent
from qibao_api.settings_repository import (
    AISettings,
    AISettingsRepository,
    EffectiveAISettingsResolver,
)
from qibao_api.zhongshu.news_ai import NEWS_AI_TIMEOUT_SECONDS, NewsAIGateway, ReloadableNewsAIGateway


NOW = datetime(2026, 7, 14, 1, 0, tzinfo=UTC)
SECRET = "sk-secret-must-never-leak"


def test_news_ai_default_timeout_allows_slow_model_responses() -> None:
    assert NEWS_AI_TIMEOUT_SECONDS == 60


def event() -> NormalizedNewsEvent:
    return NormalizedNewsEvent(
        event_id="event-1", event_type="market_news", headline="政策支持先进制造",
        occurred_at=NOW, normalized_at=NOW,
        affected_instruments=(), industries=("高端制造",), themes=("政策支持",),
        citations=(EvidenceCitation(
            citation_id="citation-1", article_id="news-1",
            canonical_url="https://news.example/1", publisher="测试来源",
            published_at=NOW, quoted_text="政策支持先进制造", content_hash="a" * 64,
        ),),
        association_confidence=Decimal("0.60"), review_state="pending",
    )


class Provider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, _request: dict) -> str:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_gateway_accepts_schema_valid_evidence_bound_json() -> None:
    provider = Provider([json.dumps({"statements": [
        {"statement_id": "s1", "kind": "fact", "text": "政策已经发布。",
         "citation_ids": ["citation-1"]},
        {"statement_id": "s2", "kind": "interpretation",
         "text": "可能改善行业预期，但不是买入信号。", "citation_ids": []},
    ]}, ensure_ascii=False)])
    gateway = NewsAIGateway(
        provider, provider_name="cloud", model="model-1", prompt_version="news-v1",
        clock=lambda: NOW, monotonic=iter([1.0, 1.125]).__next__,
    )

    result = await gateway.interpret(event())

    assert result.provider == "cloud"
    assert result.model == "model-1"
    assert result.latency_ms == 125
    assert result.degraded is False
    assert result.statements[0].citation_ids == ("citation-1",)
    assert result.provider_attempts == 1
    assert result.invalid_output_count == 0


@pytest.mark.asyncio
async def test_gateway_retries_invalid_json_once_then_accepts_valid_output() -> None:
    provider = Provider(["not-json", json.dumps({"statements": [{
        "statement_id": "s1", "kind": "fact", "text": "政策已经发布。",
        "citation_ids": ["citation-1"],
    }]}, ensure_ascii=False)])
    gateway = NewsAIGateway(provider, provider_name="local", model="model-2",
                            prompt_version="news-v1", clock=lambda: NOW)

    result = await gateway.interpret(event())

    assert provider.calls == 2
    assert result.degraded is False
    assert result.provider_attempts == 2
    assert result.invalid_output_count == 1


@pytest.mark.asyncio
async def test_gateway_degrades_deterministically_without_leaking_provider_errors() -> None:
    provider = Provider([RuntimeError(f"authorization failed: {SECRET}"), "still invalid"])
    gateway = NewsAIGateway(
        provider, provider_name="cloud", model="model-1", prompt_version="news-v1",
        clock=lambda: NOW, api_key=SECRET,
    )

    result = await gateway.interpret(event())
    serialized = result.model_dump_json()

    assert provider.calls == 2
    assert result.provider == "deterministic"
    assert result.model == "evidence-summary-v1"
    assert result.degraded is True
    assert result.statements[0].citation_ids == ("citation-1",)
    assert SECRET not in serialized
    assert SECRET not in repr(gateway)
    assert result.provider_attempts == 2
    assert result.provider_error_count == 1
    assert result.invalid_output_count == 1


@pytest.mark.asyncio
async def test_reloadable_gateway_uses_saved_settings_without_restart(tmp_path) -> None:
    repository = AISettingsRepository(tmp_path)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][1]["content"])
        requests.append((str(request.url), request.headers["authorization"], body))
        assert prompt["event"]["event_id"] == "event-1"
        assert prompt["allowed_citation_ids"] == ["citation-1"]
        assert SECRET not in body["messages"][1]["content"]
        content = json.dumps({
            "statements": [{
                "statement_id": "s-ready",
                "kind": "fact",
                "text": "政策已经发布。",
                "citation_ids": ["citation-1"],
            }],
            "impact_direction": "positive",
            "confidence": "0.75",
            "contrary_citation_ids": [],
        }, ensure_ascii=False)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content}}],
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = ReloadableNewsAIGateway(
        EffectiveAISettingsResolver(repository),
        client=client,
        clock=lambda: NOW,
    )

    degraded = await gateway.interpret(event())
    assert degraded.degraded is True
    assert requests == []
    assert gateway.needs_interpretation("event-1", (degraded,)) is False

    repository.save(AISettings(
        base_url="https://provider.example/v1",
        model="model-first",
        api_key=SECRET,
    ))
    assert gateway.needs_interpretation("event-1", (degraded,)) is True
    ready = await gateway.interpret(event())

    assert ready.degraded is False
    assert ready.provider == "openai-compatible"
    assert ready.model == "model-first"
    assert gateway.needs_interpretation("event-1", (degraded, ready)) is False
    assert requests[0][0] == "https://provider.example/v1/chat/completions"
    assert requests[0][1] == f"Bearer {SECRET}"
    assert requests[0][2]["model"] == "model-first"
    assert requests[0][2]["temperature"] == 0
    assert requests[0][2]["response_format"] == {"type": "json_object"}
    assert SECRET not in repr(gateway)

    repository.save(AISettings(
        base_url="https://provider.example/v1",
        model="model-second",
        api_key=SECRET,
    ))
    assert gateway.needs_interpretation("event-1", (degraded, ready)) is True
    changed = await gateway.interpret(event())
    assert changed.model == "model-second"
    assert requests[-1][2]["model"] == "model-second"
    await client.aclose()
