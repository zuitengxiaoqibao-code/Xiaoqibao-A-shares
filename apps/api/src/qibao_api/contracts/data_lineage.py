from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


DataLineageStatus = Literal["ready", "partial", "stale", "unavailable", "error"]


class DataLineageRecord(BaseModel):
    """Immutable provenance for one observed field or dataset slice."""

    model_config = ConfigDict(frozen=True)

    domain: str = Field(min_length=1, max_length=128)
    field: str = Field(min_length=1, max_length=128)
    symbol: str | None = Field(default=None, min_length=1, max_length=32)
    trade_date: date | None = None
    observed_at: AwareDatetime | None = None
    source: str = Field(min_length=1, max_length=128)
    source_version: str = Field(min_length=1, max_length=128)
    content_hash: str
    status: DataLineageStatus
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    limitations: tuple[str, ...] = ()

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
            raise ValueError("content_hash must be SHA-256")
        return value.lower()

    def validate_truthful_state(self) -> "DataLineageRecord":
        if self.status == "ready" and self.observed_at is None:
            raise ValueError("ready lineage requires observed_at")
        if self.status in {"unavailable", "error"} and not self.limitations:
            raise ValueError(f"{self.status} lineage requires limitations")
        return self

    def model_post_init(self, __context: object) -> None:
        self.validate_truthful_state()


class DataLineageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: AwareDatetime
    count: int = Field(ge=0)
    records: tuple[dict, ...] = ()
