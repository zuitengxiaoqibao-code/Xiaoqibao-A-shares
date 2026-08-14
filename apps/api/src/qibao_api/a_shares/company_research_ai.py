from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

import httpx
from pydantic import ValidationError

from qibao_api.contracts.company_research import (
    CompanyResearchAIAnalysis,
    CompanyResearchAIRequest,
    CompanyResearchAIResult,
)
from qibao_api.settings_repository import AISettings, EffectiveAISettingsResolver


class CompanyResearchAIProvider(Protocol):
    def complete(self, payload: dict[str, object]) -> str: ...


_TRADING_INSTRUCTION = re.compile(
    r"(?:建议|应该|应当|可以|可考虑|立即|现在).{0,8}(?:买入|卖出|加仓|减仓)|"
    r"(?:止损|止盈|仓位|买入价|卖出价).{0,12}\d|\b(?:buy|sell|position|stop[- ]?loss)\b",
    re.IGNORECASE,
)


class CompanyResearchAIGateway:
    def __init__(
        self,
        provider: CompanyResearchAIProvider,
        *,
        provider_name: str,
        model: str,
        prompt_version: str = "company-research-ai-v1",
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model = model
        self.prompt_version = prompt_version
        self.clock = clock

    def analyze(self, request: CompanyResearchAIRequest) -> CompanyResearchAIResult:
        try:
            raw = self.provider.complete(self._payload(request))
        except httpx.TimeoutException:
            return self._result("timeout", request)
        except Exception:
            return self._result("http_error", request)
        try:
            analysis = CompanyResearchAIAnalysis.model_validate_json(raw)
            allowed = {item.evidence_id for item in request.evidence}
            referenced = {
                evidence_id
                for item in analysis.contrary_risks
                for evidence_id in item.evidence_ids
            }
            if not referenced.issubset(allowed):
                raise ValueError("AI referenced evidence outside the frozen research version")
            text = " ".join((
                analysis.executive_summary,
                *(item.title for item in analysis.contrary_risks),
                *(item.detail for item in analysis.contrary_risks),
                *analysis.verification_questions,
            ))
            if _TRADING_INSTRUCTION.search(text):
                raise ValueError("AI generated a trading instruction")
        except (ValidationError, ValueError, TypeError):
            return self._result("invalid", request)
        return CompanyResearchAIResult(
            status="ready", snapshot_id=request.snapshot_id, analysis=analysis,
            provider=self.provider_name, model=self.model,
            prompt_version=self.prompt_version, generated_at=self.clock(),
        )

    def _payload(self, request: CompanyResearchAIRequest) -> dict[str, object]:
        return {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON. Summarize and challenge only the frozen evidence. "
                        "Do not add facts, prices, forecasts, scores, positions, or trade instructions."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "snapshot_id": request.snapshot_id,
                        "symbol": request.symbol,
                        "evidence": [item.model_dump(mode="json") for item in request.evidence],
                        "deterministic_conclusions": list(request.deterministic_conclusions),
                        "allowed_evidence_ids": [item.evidence_id for item in request.evidence],
                        "response_schema": CompanyResearchAIAnalysis.model_json_schema(),
                    }, ensure_ascii=False),
                },
            ],
        }

    def _result(self, status, request):
        return CompanyResearchAIResult(
            status=status, snapshot_id=request.snapshot_id, analysis=None,
            provider=self.provider_name, model=self.model,
            prompt_version=self.prompt_version, generated_at=self.clock(),
        )


class OpenAICompatibleCompanyResearchProvider:
    def __init__(self, settings: AISettings, client: httpx.Client, *, timeout: float = 30) -> None:
        self.settings = settings
        self.client = client
        self.timeout = timeout

    def complete(self, payload: dict[str, object]) -> str:
        response = self.client.post(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("AI content must be text")
        return content


class ReloadableCompanyResearchAIGateway:
    def __init__(self, settings: EffectiveAISettingsResolver, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client

    def configuration_identity(self) -> tuple[str, ...]:
        current = self.settings.resolve()
        if not isinstance(current, AISettings):
            return ("unconfigured", "company-research-ai-v1")
        revision = self.settings.repository.revision() or "fallback-or-legacy"
        return (
            "configured", current.base_url.rstrip("/"), current.model,
            "company-research-ai-v1", revision,
        )

    def analyze(self, request: CompanyResearchAIRequest) -> CompanyResearchAIResult:
        current = self.settings.resolve()
        if not isinstance(current, AISettings):
            return CompanyResearchAIResult(
                status="unconfigured", snapshot_id=request.snapshot_id, analysis=None,
                provider="unconfigured", model="none", generated_at=request.generated_at,
            )
        return CompanyResearchAIGateway(
            OpenAICompatibleCompanyResearchProvider(current, self.client),
            provider_name="openai-compatible", model=current.model,
            clock=lambda: request.generated_at,
        ).analyze(request)
