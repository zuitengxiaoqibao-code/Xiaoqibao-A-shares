from datetime import date
from decimal import Decimal

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class TdxIpoEventView(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    subscription_date: date
    listing_date: date | None = None
    allotment_date: date | None = None
    fetched_at: AwareDatetime
    source: str = "tdx-local-rpc"


class TdxIpoCalendarResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    events: tuple[TdxIpoEventView, ...] = ()
    fetched_at: AwareDatetime | None = None
    source: str = "tdx-local-rpc"
    detail: str | None = None


class TdxFormulaPointView(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str | None = None
    formula_name: str = Field(pattern=r"^formula_process_mul_[A-Za-z0-9_]+$")
    values: dict[str, Decimal] = Field(default_factory=dict)
    fetched_at: AwareDatetime
    source: str = "tdx-local-rpc"


class TdxFormulaResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    points: tuple[TdxFormulaPointView, ...] = ()
    fetched_at: AwareDatetime | None = None
    source: str = "tdx-local-rpc"
    detail: str | None = None


class TdxProfessionalRowView(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: str
    symbol: str | None = Field(default=None, pattern=r"^\d{6}$")
    values: dict[str, Decimal | str] = Field(default_factory=dict)
    fetched_at: AwareDatetime
    source: str = "tdx-local-rpc-professional"
    semantic_status: Literal["semantic_unmapped", "verified"] = "semantic_unmapped"


class TdxProfessionalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    semantic_status: Literal["not_applicable", "detected_only", "verified"] = "not_applicable"
    rows: tuple[TdxProfessionalRowView, ...] = ()
    fetched_at: AwareDatetime | None = None
    source: str = "tdx-local-rpc-professional"
    detail: str | None = None
