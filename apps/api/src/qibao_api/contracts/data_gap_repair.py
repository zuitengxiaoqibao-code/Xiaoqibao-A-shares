from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from qibao_api.contracts.instruments import validate_a_share_code


class DataGapItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    trade_date: date
    fields: tuple[str, ...] = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return validate_a_share_code(value)

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not normalized:
            raise ValueError("gap fields must not be empty")
        return normalized


class DataGapRepairRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_date: date
    source: Literal["mootdx", "baidu"] = "mootdx"
    gaps: tuple[DataGapItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_gap_batch(self) -> "DataGapRepairRequest":
        keys = [(item.symbol, item.trade_date, item.fields) for item in self.gaps]
        if len(keys) != len(set(keys)):
            raise ValueError("gap batch contains duplicate items")
        if any(item.trade_date > self.target_date for item in self.gaps):
            raise ValueError("gap trade date cannot be later than target_date")
        return self


class DataGapRepairResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    state: Literal["pending", "running", "paused", "completed", "failed"]
    target_date: date
    source: Literal["mootdx", "baidu"]
    symbols: tuple[str, ...]
    gap_count: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    written_rows: int = Field(ge=0)
    failure_reasons: tuple[str, ...] = ()
    submitted_at: AwareDatetime
