from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class CalibrationSplit(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: Literal["train", "validation", "test"]
    start_date: date | None = None
    end_date: date | None = None
    sample_count: int = Field(ge=0)
    hit_rate_percent: Decimal | None = None
    average_return_percent: Decimal | None = None


class CalibrationIntegrity(BaseModel):
    model_config = ConfigDict(frozen=True)

    future_function_check: Literal["passed", "failed", "unavailable"]
    survivorship_check: Literal["passed", "failed", "unavailable"]
    duplicate_decision_check: Literal["passed", "failed"]
    limitations: tuple[str, ...] = ()


class QuantCalibrationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "unavailable"]
    horizon: int = Field(ge=1)
    formula_versions: tuple[str, ...] = ()
    total_sample_count: int = Field(ge=0)
    mature_sample_count: int = Field(ge=0)
    splits: tuple[CalibrationSplit, ...]
    integrity: CalibrationIntegrity
    gross_hit_rate_percent: Decimal | None = None
    gross_average_return_percent: Decimal | None = None
    fee_bps: Decimal | None = None
    slippage_bps: Decimal | None = None
    generated_at: AwareDatetime
    limitations: tuple[str, ...] = ()

