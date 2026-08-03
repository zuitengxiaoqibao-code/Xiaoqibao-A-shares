from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FIRST_LIMIT_UP_RULE_VERSION = "first-limit-up-v1"


class FirstLimitUpEntryReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    buy_steps_pct: tuple[Decimal, Decimal, Decimal] = (
        Decimal("-0.02"), Decimal("-0.05"), Decimal("-0.08")
    )
    sell_steps_pct: tuple[Decimal, Decimal, Decimal] = (
        Decimal("0.03"), Decimal("0.06"), Decimal("0.10")
    )
    note: str = "仅在回撤窗口且通过风控后观察，不是自动下单价格"


class FirstLimitUpCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str
    as_of: date
    limit_up_date: date
    limit_up_close: Decimal = Field(gt=0)
    current_close: Decimal = Field(gt=0)
    pe_ttm: Decimal | None = None
    limit_rate: Decimal = Field(gt=0)
    weekly_distance_to_low: Decimal | None = None
    monthly_distance_to_low: Decimal | None = None
    weekly_bottom: bool | None = None
    monthly_bottom: bool | None = None
    pullback_pct: Decimal = Field(ge=0)
    consolidation_days: int = Field(ge=0)
    selection_status: Literal["qualified", "excluded", "data_insufficient"]
    stage: Literal[
        "limit_up_day", "waiting_pullback", "pullback_window",
        "risk_expanded", "data_insufficient",
    ]
    action: Literal[
        "no_buy", "observe", "staged_entry_reference", "avoid", "data_insufficient",
    ]
    score: Decimal = Field(ge=0, le=100)
    reasons: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    entry_reference: FirstLimitUpEntryReference = FirstLimitUpEntryReference()


class FirstLimitUpBoard(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset: Literal["a_share"] = "a_share"
    status: Literal["ready", "partial", "empty"]
    as_of: date
    rule_version: Literal["first-limit-up-v1"] = FIRST_LIMIT_UP_RULE_VERSION
    universe_count: int = Field(default=0, ge=0)
    history_eligible_count: int = Field(default=0, ge=0)
    scan_coverage_count: int = Field(default=0, ge=0)
    coverage_complete: bool = False
    scanned_count: int = Field(ge=0)
    qualified_count: int = Field(ge=0)
    pullback_window_count: int = Field(ge=0)
    no_buy_count: int = Field(ge=0)
    today: tuple[FirstLimitUpCandidate, ...] = ()
    pool: tuple[FirstLimitUpCandidate, ...] = ()
    priority_symbol: str | None = None
    missing_data: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
