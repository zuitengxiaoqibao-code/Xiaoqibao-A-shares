from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry


ImpactStatus = Literal["ready", "partial", "unavailable"]


class EventImpactWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    horizon_days: Literal[1, 3, 5, 20]
    status: Literal["ready", "unavailable"]
    baseline_trade_date: date | None = None
    end_trade_date: date | None = None
    baseline_close: Decimal | None = Field(default=None, gt=0)
    end_close: Decimal | None = Field(default=None, gt=0)
    return_percent: Decimal | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_window_state(self) -> "EventImpactWindow":
        values = (
            self.baseline_trade_date,
            self.end_trade_date,
            self.baseline_close,
            self.end_close,
            self.return_percent,
        )
        if self.status == "unavailable":
            if any(item is not None for item in values):
                raise ValueError("unavailable window cannot claim prices or return")
            if not self.reason:
                raise ValueError("unavailable window requires an explicit reason")
        elif any(item is None for item in values):
            raise ValueError("ready window requires complete market prices and dates")
        return self


class EventImpactTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_type: Literal["stock", "sector"]
    target_id: str = Field(min_length=1)
    status: ImpactStatus
    windows: tuple[EventImpactWindow, ...]
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_windows(self) -> "EventImpactTarget":
        if tuple(item.horizon_days for item in self.windows) != (1, 3, 5, 20):
            raise ValueError("impact target must contain ordered 1/3/5/20 day windows")
        ready_count = sum(item.status == "ready" for item in self.windows)
        expected = "ready" if ready_count == 4 else "partial" if ready_count else "unavailable"
        if self.status != expected:
            raise ValueError("impact target status must match available market windows")
        if self.status != "ready" and not self.limitations:
            raise ValueError("incomplete impact target requires explicit limitations")
        return self


class EventImpactReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ImpactStatus
    event_id: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    first_published_at: AwareDatetime
    affected_symbols: tuple[str, ...] = ()
    related_sectors: tuple[str, ...] = ()
    association_confidence: Decimal = Field(ge=0, le=1)
    association_status: Literal["verified", "low_confidence", "rejected", "unavailable"]
    duplicate_status: Literal["unique", "duplicate_cluster"]
    duplicate_article_count: int = Field(ge=1)
    targets: tuple[EventImpactTarget, ...] = ()
    evidence_ledger: tuple[EvidenceLedgerEntry, ...] = ()
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_report_state(self) -> "EventImpactReport":
        if self.duplicate_status == "unique" and self.duplicate_article_count != 1:
            raise ValueError("unique event impact must have one primary article")
        if self.duplicate_status == "duplicate_cluster" and self.duplicate_article_count < 2:
            raise ValueError("duplicate cluster requires at least two articles")
        if self.status != "ready" and not self.limitations:
            raise ValueError("incomplete event impact requires explicit limitations")
        return self


# Backward-compatible descriptive aliases for API consumers.
NewsEventImpactReport = EventImpactReport
NewsEventImpactWindow = EventImpactWindow
EventImpact = EventImpactReport
