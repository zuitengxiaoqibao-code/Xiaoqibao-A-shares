from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


LateSessionPhase = Literal["pre_screen", "live_monitor", "post_close"]
RuleStatus = Literal["passed", "failed", "unavailable", "disabled"]
LateSessionDataState = Literal["ready", "partial", "no_candidates", "no_market_data"]
LateSessionAIStatus = Literal["ready", "unconfigured", "no_candidates", "error"]
LateSessionAIMode = Literal["ai", "rule_interpretation", "unavailable"]


class LateSessionRuleSettings(BaseModel):
    """User-editable thresholds; defaults mirror the original screenshot rules."""

    model_config = ConfigDict(frozen=True)

    time_enabled: bool = True
    start_time: time = time(14, 30)
    end_time: time = time(15, 0)
    change_enabled: bool = True
    change_min: Decimal = Field(default=Decimal("3"), ge=-100, le=100)
    change_max: Decimal = Field(default=Decimal("6"), ge=-100, le=100)
    volume_ratio_enabled: bool = True
    volume_ratio_min: Decimal = Field(default=Decimal("2"), ge=0)
    volume_ratio_max: Decimal = Field(default=Decimal("5"), ge=0)
    turnover_rate_enabled: bool = True
    turnover_rate_min: Decimal = Field(default=Decimal("6"), ge=0)
    turnover_rate_max: Decimal = Field(default=Decimal("15"), ge=0)
    market_cap_enabled: bool = True
    market_cap_min: Decimal = Field(default=Decimal("60"), ge=0)
    market_cap_max: Decimal = Field(default=Decimal("300"), ge=0)
    twenty_day_limit_up_enabled: bool = True
    twenty_day_limit_up_min: int = Field(default=1, ge=0)
    twenty_day_limit_up_max: int | None = Field(default=None, ge=0)
    intraday_average_enabled: bool = True
    intraday_relation: Literal["above", "below", "any"] = "above"

    @model_validator(mode="after")
    def validate_ranges(self) -> "LateSessionRuleSettings":
        pairs = (
            ("change_min", self.change_min, "change_max", self.change_max),
            ("volume_ratio_min", self.volume_ratio_min, "volume_ratio_max", self.volume_ratio_max),
            ("turnover_rate_min", self.turnover_rate_min, "turnover_rate_max", self.turnover_rate_max),
            ("market_cap_min", self.market_cap_min, "market_cap_max", self.market_cap_max),
        )
        for minimum_name, minimum, maximum_name, maximum in pairs:
            if minimum > maximum:
                raise ValueError(f"{minimum_name} cannot exceed {maximum_name}")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        if self.twenty_day_limit_up_max is not None and self.twenty_day_limit_up_min > self.twenty_day_limit_up_max:
            raise ValueError("twenty_day_limit_up_min cannot exceed twenty_day_limit_up_max")
        return self


DEFAULT_LATE_SESSION_RULE_SETTINGS = LateSessionRuleSettings()


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


class LateSessionAIAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: LateSessionAIStatus
    mode: LateSessionAIMode
    title: str
    summary: str
    key_points: tuple[str, ...] = ()
    risk_points: tuple[str, ...] = ()
    data_gaps: tuple[str, ...] = ()
    candidate_count: int = Field(ge=0)
    source_evidence: tuple[str, ...] = ()
    observed_at: AwareDatetime
    reason: str | None = None


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
    data_state: LateSessionDataState = "ready"
    no_data_reason: str | None = None
    settings: LateSessionRuleSettings = DEFAULT_LATE_SESSION_RULE_SETTINGS
    default_settings: LateSessionRuleSettings = DEFAULT_LATE_SESSION_RULE_SETTINGS
    candidates: tuple[LateSessionCandidateResult, ...] = ()
    behaviors: tuple[LateSessionBehavior, ...] = ()
    source_evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
