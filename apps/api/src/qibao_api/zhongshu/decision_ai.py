import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, Protocol

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from qibao_api.settings_repository import AISettings, EffectiveAISettingsResolver


class DecisionAIProvider(Protocol):
    def complete(self, request: dict[str, object]) -> str: ...


class UnavailableDecisionAIProvider:
    def complete(self, _request: dict[str, object]) -> str:
        raise OSError("decision AI provider is not configured")


class OpenAICompatibleDecisionProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.Client,
        timeout: float = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self._client = client
        self.timeout = timeout

    def __repr__(self) -> str:
        return (
            "OpenAICompatibleDecisionProvider("
            f"base_url={self.base_url!r}, model={self.model!r})"
        )

    def complete(self, request: dict[str, object]) -> str:
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return one strict JSON object matching the supplied schema. "
                            "Explain only the frozen evidence and deterministic conclusions. "
                            "Never add numbers, prices, scores, positions, or trade plans."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(request, ensure_ascii=False),
                    },
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        envelope = response.json()
        content = envelope["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("chat completion content must be a JSON string")
        return content


class DecisionAIEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class DecisionAIRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: AwareDatetime
    evidence: tuple[DecisionAIEvidence, ...]
    deterministic_conclusions: tuple[str, ...]

    @model_validator(mode="after")
    def unique_evidence(self) -> "DecisionAIRequest":
        ids = [item.evidence_id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence IDs must be unique")
        return self


class DecisionAIStatement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["fact", "interpretation"]
    text: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def facts_require_evidence(self) -> "DecisionAIStatement":
        if self.kind == "fact" and not self.evidence_ids:
            raise ValueError("fact statements require evidence")
        return self


class _ProviderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    statements: tuple[DecisionAIStatement, ...]


class DecisionAIResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "unavailable"]
    explanation: str | None
    statements: tuple[DecisionAIStatement, ...]
    provider: str
    model: str
    prompt_version: str
    generated_at: AwareDatetime
    evidence_ids: tuple[str, ...]
    invalid_output_count: int = Field(ge=0)
    provider_error_count: int = Field(ge=0)


_PLAN_LANGUAGE = re.compile(
    r"(?:buy|sell|entry|exit|price|target|weight|allocation|stop[- ]?loss|"
    r"take[- ]?profit|position|score|买入|卖出|价格|目标|止损|止盈|仓位|"
    r"权重|分配资金|评分|点位)", re.IGNORECASE,
)
_NUMBER = re.compile(r"[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?%?")


class DecisionAIGateway:
    def __init__(
        self, provider: DecisionAIProvider, *, provider_name: str, model: str,
        prompt_version: str, clock=lambda: datetime.now(timezone.utc), api_key: str | None = None,
    ) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model = model
        self.prompt_version = prompt_version
        self.clock = clock
        self._api_key = api_key

    def __repr__(self) -> str:
        return (
            f"DecisionAIGateway(provider_name={self.provider_name!r}, "
            f"model={self.model!r}, prompt_version={self.prompt_version!r})"
        )

    def explain(self, request: DecisionAIRequest) -> DecisionAIResult:
        evidence_ids = tuple(item.evidence_id for item in request.evidence)
        try:
            raw = self.provider.complete(self._request(request))
        except Exception:
            return self._unavailable(request, provider_errors=1)
        try:
            payload = _ProviderOutput.model_validate_json(raw)
            self._validate(payload, request)
        except (ValidationError, ValueError, TypeError):
            return self._unavailable(request, invalid=1)
        return DecisionAIResult(
            status="ready", explanation=payload.summary, statements=payload.statements,
            provider=self.provider_name, model=self.model, prompt_version=self.prompt_version,
            generated_at=self.clock(), evidence_ids=evidence_ids,
            invalid_output_count=0, provider_error_count=0,
        )

    def _request(self, request: DecisionAIRequest) -> dict[str, object]:
        return {
            "prompt_version": self.prompt_version,
            "evidence": [item.model_dump(mode="json") for item in request.evidence],
            "deterministic_conclusions": list(request.deterministic_conclusions),
            "allowed_evidence_ids": [item.evidence_id for item in request.evidence],
            "response_schema": _ProviderOutput.model_json_schema(),
            "instructions": (
                "Return JSON only. Explain frozen conclusions without adding or changing numbers, "
                "prices, scores, positions, or trade plans. Facts require evidence_ids."
            ),
        }

    @staticmethod
    def _validate(payload: _ProviderOutput, request: DecisionAIRequest) -> None:
        allowed = {item.evidence_id for item in request.evidence}
        referenced = {item for statement in payload.statements for item in statement.evidence_ids}
        if not referenced.issubset(allowed):
            raise ValueError("evidence outside frozen request")
        text = " ".join([payload.summary, *(item.text for item in payload.statements)])
        if _PLAN_LANGUAGE.search(text):
            raise ValueError("provider attempted to create a numeric decision")
        if _NUMBER.search(text):
            raise ValueError("provider introduced a numeric fact")

    def _unavailable(
        self, request: DecisionAIRequest, *, invalid: int = 0, provider_errors: int = 0,
    ) -> DecisionAIResult:
        return DecisionAIResult(
            status="unavailable", explanation=None, statements=(), provider=self.provider_name,
            model=self.model, prompt_version=self.prompt_version, generated_at=self.clock(),
            evidence_ids=tuple(item.evidence_id for item in request.evidence),
            invalid_output_count=invalid, provider_error_count=provider_errors,
        )


class ReloadableDecisionAIGateway:
    provider_name = "openai-compatible"

    def __init__(
        self,
        settings: EffectiveAISettingsResolver,
        *,
        client: httpx.Client | None = None,
        client_factory: Callable[[], httpx.Client] | None = None,
        timeout: float = 10,
        prompt_version: str = "decision-v1",
    ) -> None:
        self._settings = settings
        self._client = client
        self._client_factory = client_factory or (
            lambda: httpx.Client(timeout=timeout)
        )
        self._owns_client = client is None
        self._timeout = timeout
        self.prompt_version = prompt_version

    def __repr__(self) -> str:
        return (
            "ReloadableDecisionAIGateway("
            f"provider_name={self.provider_name!r}, "
            f"prompt_version={self.prompt_version!r})"
        )

    def _client_or_create(self) -> httpx.Client:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def configuration_identity(self) -> tuple[str, ...]:
        current = self._settings.resolve()
        if not isinstance(current, AISettings):
            return ("unconfigured", current.reason, self.prompt_version)
        revision = self._settings.repository.revision() or "fallback-or-legacy"
        return (
            "configured",
            self.provider_name,
            current.base_url.rstrip("/"),
            current.model,
            self.prompt_version,
            revision,
        )

    def explain(self, request: DecisionAIRequest) -> DecisionAIResult:
        current = self._settings.resolve()
        provider: DecisionAIProvider
        if not isinstance(current, AISettings):
            provider = UnavailableDecisionAIProvider()
            provider_name = "unconfigured"
            model = "none"
            api_key = None
        else:
            provider = OpenAICompatibleDecisionProvider(
                base_url=current.base_url,
                api_key=current.api_key,
                model=current.model,
                client=self._client_or_create(),
                timeout=self._timeout,
            )
            provider_name = self.provider_name
            model = current.model
            api_key = current.api_key
        gateway = DecisionAIGateway(
            provider,
            provider_name=provider_name,
            model=model,
            prompt_version=self.prompt_version,
            clock=lambda: request.generated_at,
            api_key=api_key,
        )
        return gateway.explain(request)
