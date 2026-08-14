from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class AlertInboxItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_id: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    priority: Literal["high", "medium", "low"]
    status: Literal["new", "cooldown", "silent", "acknowledged"] = "new"
    occurred_at: AwareDatetime
    affected_symbols: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    source_count: int = Field(ge=1)
    voice_eligible: bool = False
