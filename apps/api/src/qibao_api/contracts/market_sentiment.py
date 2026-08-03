from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


SentimentPhase = Literal["intraday", "postclose"]
SentimentQuality = Literal["ready", "partial", "unavailable"]
SentimentFreshness = Literal["current", "stale"]
SentimentBand = Literal[
    "panic", "cold", "neutral", "active", "overheated", "unavailable"
]
SentimentComponentName = Literal[
    "volatility", "activity", "price_strength", "risk_appetite", "breadth",
    "limit_ecology", "money_making", "sector_diffusion", "style_risk_preference",
    "liquidity", "hotspot",
]
SentimentMetric = Decimal | int | str | None


class MarketBreadthObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_count: int = Field(ge=1)
    valid_count: int = Field(ge=0)
    rising_count: int = Field(ge=0)
    falling_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    median_change_percent: Decimal | None = None
    total_amount_wan: Decimal | None = Field(default=None, ge=0)
    limit_up_count: int = Field(ge=0)
    limit_down_count: int = Field(ge=0)
    broken_limit_up_count: int = Field(ge=0)
    max_limit_streak: int | None = Field(default=None, ge=1)
    observed_at: AwareDatetime
    fetched_at: AwareDatetime
    source_snapshot_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_counts_and_times(self) -> "MarketBreadthObservation":
        if self.valid_count > self.requested_count:
            raise ValueError("valid count cannot exceed requested count")
        if self.rising_count + self.falling_count + self.flat_count != self.valid_count:
            raise ValueError("breadth counts must equal valid count")
        if self.valid_count and (
            self.median_change_percent is None or self.total_amount_wan is None
        ):
            raise ValueError("valid breadth requires median change and total amount")
        if self.observed_at > self.fetched_at:
            raise ValueError("observation cannot be after fetch time")
        if len(self.source_snapshot_ids) != len(set(self.source_snapshot_ids)):
            raise ValueError("source snapshot ids must be unique")
        return self


class LiquidityBaseline(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount_wan: Decimal = Field(gt=0)
    quality: Literal["ready", "partial"]
    sample_size: int = Field(ge=1)
    evidence_ids: tuple[str, ...]


class HotspotSentimentInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    unique_theme_count: int = Field(ge=0)
    affected_symbol_count: int = Field(ge=0)
    persistent_theme_count: int = Field(ge=0)
    largest_theme_share_percent: Decimal = Field(ge=0, le=100)
    evidence_ids: tuple[str, ...]


class MarketFactorObservation(BaseModel):
    """Raw evidence used to calculate the nine-factor market sentiment score."""

    model_config = ConfigDict(frozen=True)

    volatility_current_percent: Decimal | None = Field(default=None, ge=0)
    volatility_baseline_percent: Decimal | None = Field(default=None, gt=0)
    relative_amount: Decimal | None = Field(default=None, ge=0)
    new_high_252_count: int | None = Field(default=None, ge=0)
    effective_count: int | None = Field(default=None, ge=1)
    benchmark_return_20d_percent: Decimal | None = None
    bond_etf_return_20d_percent: Decimal | None = None
    ma20_above_count: int | None = Field(default=None, ge=0)
    ma60_above_count: int | None = Field(default=None, ge=0)
    five_day_rising_count: int | None = Field(default=None, ge=0)
    sixty_day_new_low_count: int | None = Field(default=None, ge=0)
    rising_industry_count: int | None = Field(default=None, ge=0)
    effective_industry_count: int | None = Field(default=None, ge=1)
    small_cap_return_5d_percent: Decimal | None = None
    large_cap_return_5d_percent: Decimal | None = None
    yesterday_limit_up_return_percent: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> "MarketFactorObservation":
        for numerator, denominator, label in (
            (self.new_high_252_count, self.effective_count, "252-day highs"),
            (self.ma20_above_count, self.effective_count, "MA20 counts"),
            (self.ma60_above_count, self.effective_count, "MA60 counts"),
            (self.five_day_rising_count, self.effective_count, "five-day counts"),
            (self.sixty_day_new_low_count, self.effective_count, "60-day lows"),
            (self.rising_industry_count, self.effective_industry_count, "industry counts"),
        ):
            if numerator is not None and denominator is not None and numerator > denominator:
                raise ValueError(f"{label} cannot exceed its denominator")
        return self


class SentimentComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: SentimentComponentName
    score: Decimal | None = Field(default=None, ge=0, le=100)
    weight: Decimal = Field(gt=0, le=100)
    coverage_percent: Decimal = Field(ge=0, le=100)
    metrics: dict[str, SentimentMetric]
    evidence_ids: tuple[str, ...]


class MarketSentimentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    previous_snapshot_id: str | None = None
    trading_date: date
    phase: SentimentPhase
    quality: SentimentQuality
    freshness: SentimentFreshness
    score: Decimal | None = Field(default=None, ge=0, le=100)
    band: SentimentBand
    coverage_percent: Decimal = Field(ge=0, le=100)
    components: tuple[SentimentComponent, ...]
    drivers: tuple[str, ...]
    risks: tuple[str, ...]
    beginner_guidance: str = Field(min_length=1)
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    source_snapshot_ids: tuple[str, ...]
    formula_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_score_state(self) -> "MarketSentimentSnapshot":
        if (self.score is None) != (self.band == "unavailable"):
            raise ValueError("unavailable band and missing score must agree")
        if self.quality == "ready" and self.coverage_percent != Decimal("100"):
            raise ValueError("ready sentiment requires complete coverage")
        if self.observed_at > self.generated_at:
            raise ValueError("sentiment observation cannot be after generation")
        return self
