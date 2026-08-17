from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


LateSessionPhase = Literal["pre_screen", "live_monitor", "post_close"]
RuleStatus = Literal["passed", "failed", "unavailable"]


class LateSessionQuote(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    previous_close: Decimal = Field(gt=0)
    change_percent: Decimal
    volume_ratio: Decimal | None = Field(default=None, ge=0)
    turnover_rate: Decimal | None = Field(default=None, ge=0)
    market_cap_yi: Decimal | None = Field(default=None, ge=0)
    twenty_day_limit_up_count: int | None = Field(default=None, ge=0)
    intraday_average_price: Decimal | None = Field(default=None, gt=0)
    observed_at: AwareDatetime
    source: str = Field(min_length=1)


class LateSessionRuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal[
        "time_window", "change_percent", "volume_ratio", "turnover_rate",
        "market_cap", "twenty_day_limit_up", "above_intraday_average",
    ]
    label: str
    actual: Decimal | int | str | None = None
    target: str
    status: RuleStatus
    detail: str


class LateSessionCandidateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    quote: LateSessionQuote
    passed: bool
    rules: tuple[LateSessionRuleResult, ...]
    behavior_tags: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()


class LateSessionBehavior(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal[
        "weak_rally", "heavy_selloff", "steady_rise", "flat_lag", "index_resilience", "pressure_breakout",
    ]
    title: str
    level: Literal["observe", "risk", "pending"]
    description: str
    evidence: tuple[str, ...] = ()


class LateSessionSelectionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "unavailable"]
    trading_date: date
    server_time: AwareDatetime
    phase: LateSessionPhase
    refresh_interval_ms: int = Field(ge=0)
    next_refresh_ms: int = Field(ge=0)
    source_quality: Literal["ready", "partial", "stale", "unavailable"]
    universe_count: int = Field(ge=0)
    quote_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    rules: tuple[LateSessionRuleResult, ...]
    candidates: tuple[LateSessionCandidateResult, ...] = ()
    behaviors: tuple[LateSessionBehavior, ...] = ()
    source_evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
