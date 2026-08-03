from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from qibao_api.contracts.instruments import AShareCode
from qibao_api.contracts.news import AssociationKind, NonBlank, WebUrl


VerificationState = Literal["verified", "multi_source_confirmed", "pending", "unverified"]
Urgency = Literal["breaking", "tracking", "normal"]


class BreakingNewsAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: NonBlank
    headline: NonBlank
    occurred_at: AwareDatetime
    verification_state: VerificationState
    urgency: Urgency
    association_kind: AssociationKind
    association_reasons: tuple[NonBlank, ...]
    affected_symbols: tuple[AShareCode, ...]
    themes: tuple[NonBlank, ...] = ()
    publishers: tuple[NonBlank, ...]
    source_urls: tuple[WebUrl, ...]
    source_count: int = Field(ge=1)
    impact_direction: Literal["positive", "negative", "neutral", "uncertain"]
    impact_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    ai_degraded: bool


class BreakingNewsAlertResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "empty"]
    observed_at: AwareDatetime
    alerts: tuple[BreakingNewsAlert, ...]
    sources: tuple[NonBlank, ...] = ()
    warnings: tuple[NonBlank, ...] = ()
