from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.instruments import AShareCode
from qibao_api.contracts.news import AssociationKind
from qibao_api.contracts.news_alerts import Urgency, VerificationState


ImpactDirection = Literal["positive", "negative", "neutral", "uncertain"]


class StockTimelineEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(min_length=1)
    event_type: Literal["market_news"] = "market_news"
    occurred_at: AwareDatetime
    mapped_trade_date: date | None
    label: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    direction: ImpactDirection
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    themes: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    publisher: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https?://[^\s]+$")
    association_confidence: Decimal = Field(ge=0, le=1)
    association_kind: AssociationKind
    association_reasons: tuple[str, ...]
    verification_state: VerificationState
    source_count: int = Field(ge=1)
    urgency: Urgency
    review_state: Literal["verified"] = "verified"


class StockTimelineResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: AShareCode
    as_of: date
    cutoff: AwareDatetime
    status: Literal["ready", "unavailable"]
    bars: tuple[DailyBar, ...]
    events: tuple[StockTimelineEvent, ...]
    sources: tuple[str, ...]
    warnings: tuple[str, ...] = ()
