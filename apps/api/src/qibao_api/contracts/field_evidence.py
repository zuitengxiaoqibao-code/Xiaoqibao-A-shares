from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


FieldEvidenceStatus = Literal[
    "live", "cached", "postclose", "stale", "missing", "conflict", "derived"
]


class FieldEvidenceAlternative(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: Decimal | bool | str
    source: str = Field(min_length=1)
    source_field: str | None = None
    observed_at: AwareDatetime

    @field_validator("value", mode="before")
    @classmethod
    def preserve_numeric_round_trip(cls, value):
        if isinstance(value, str):
            try:
                return Decimal(value)
            except (ArithmeticError, ValueError):
                return value
        return value


class FieldEvidence(BaseModel):
    """Field-level provenance for decision-critical values."""

    model_config = ConfigDict(frozen=True)

    field_path: str = Field(min_length=1)
    value: Decimal | bool | str | None = None
    source: str = Field(min_length=1)
    source_field: str | None = None
    status: FieldEvidenceStatus
    trade_date: date | None = None
    observed_at: AwareDatetime | None = None
    coverage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    derived: bool = False
    formula: str | None = None
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    alternatives: tuple[FieldEvidenceAlternative, ...] = ()
    difference: str | None = None
    selection_reason: str | None = None
    affects_conclusion: bool | None = None

    @field_validator("value", mode="before")
    @classmethod
    def preserve_numeric_round_trip(cls, value):
        if isinstance(value, str):
            try:
                return Decimal(value)
            except (ArithmeticError, ValueError):
                return value
        return value

    @model_validator(mode="after")
    def validate_truthfulness(self) -> "FieldEvidence":
        if self.status in {"missing", "conflict"} and not self.limitations:
            raise ValueError("missing or conflicting field evidence requires explicit limitations")
        if self.status == "conflict" and not self.alternatives:
            raise ValueError("conflicting field evidence requires alternatives")
        if self.status == "conflict" and (
            not self.difference or not self.selection_reason
            or self.affects_conclusion is None
        ):
            raise ValueError("conflicting field evidence requires resolution details")
        if self.status in {"live", "cached", "postclose", "stale", "derived", "conflict"} and self.observed_at is None:
            raise ValueError("observed field evidence requires observed_at")
        if self.derived and not self.formula:
            raise ValueError("derived field evidence requires formula")
        if self.status == "missing" and self.value is not None:
            raise ValueError("missing field evidence cannot contain a value")
        return self
