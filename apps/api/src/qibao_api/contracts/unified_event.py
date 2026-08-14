from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


UnifiedEventCategory = Literal[
    "policy_macro",
    "industry_sector",
    "company_announcement",
    "earnings_financial",
    "capital_dragon_tiger",
    "price_volume_anomaly",
    "risk_event",
    "rumor_unverified",
]
ImpactDirection = Literal["positive", "negative", "neutral", "uncertain"]
ImpactStrength = Literal["high", "medium", "low", "unknown"]
EventCredibility = Literal[
    "multi_source_verified", "verified", "pending", "rejected"
]
EventDuration = Literal["intraday", "multi_day", "long_term", "unknown"]
PriceReflection = Literal[
    "not_reflected", "partially_reflected", "fully_reflected", "unknown"
]


class UnifiedDecisionEvent(BaseModel):
    """Decision projection over an append-only verified source event."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(min_length=1)
    source_event_type: str = Field(min_length=1)
    category: UnifiedEventCategory
    category_reason: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    occurred_at: AwareDatetime
    affected_symbols: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()
    direction: ImpactDirection = "uncertain"
    direction_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    strength: ImpactStrength = "unknown"
    credibility: EventCredibility
    source_count: int = Field(ge=1)
    duration: EventDuration = "unknown"
    price_reflection: PriceReflection = "unknown"
    follow_up_indicators: tuple[str, ...] = Field(min_length=1)
    interpretation_id: str | None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_evidence_for_direction(self) -> "UnifiedDecisionEvent":
        if self.direction != "uncertain" and self.direction_confidence is None:
            raise ValueError("claimed direction requires direction confidence")
        if self.direction == "uncertain" and self.strength != "unknown":
            raise ValueError("uncertain direction cannot claim impact strength")
        if self.interpretation_id is None and self.direction != "uncertain":
            raise ValueError("claimed direction requires an interpretation id")
        return self
