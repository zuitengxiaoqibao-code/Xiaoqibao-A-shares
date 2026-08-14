from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


DecisionAction = Literal["observe", "no_trade", "buy", "sell"]


class DecisionJournalCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str | None = Field(default=None, max_length=80)
    symbol: str = Field(pattern=r"^\d{6}$")
    action: DecisionAction
    recorded_at: AwareDatetime
    actual_price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    note: str = Field(min_length=1, max_length=1000)
    market_regime: str | None = Field(default=None, max_length=80)
    screener_session_id: str | None = Field(default=None, max_length=120)
    snapshot_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    observation_reason: str | None = Field(default=None, max_length=1000)
    risks: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()


class DecisionJournalEntry(DecisionJournalCreate):
    entry_id: str
    created_at: AwareDatetime
