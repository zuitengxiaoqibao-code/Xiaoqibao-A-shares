from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FACTOR_VERSION = "a-share-factors-v1"


class FactorSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    as_of: date
    latest_trade_date: date | None = None
    close: Decimal = Field(gt=0)
    return_5d: Decimal
    return_20d: Decimal
    distance_ma20: Decimal
    volume_ratio_5_20: Decimal = Field(ge=0)
    volatility_20d: Decimal = Field(ge=0)
    drawdown_60d: Decimal = Field(le=0)
    liquidity_amount_20d: Decimal = Field(ge=0)
    factor_version: Literal["a-share-factors-v1"] = FACTOR_VERSION
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_trade_date_at_or_before_cutoff(self) -> "FactorSnapshot":
        if self.latest_trade_date is not None and self.latest_trade_date > self.as_of:
            raise ValueError("latest_trade_date must not be after as_of")
        return self


class CandidateEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    horizon: Literal["short_term", "swing"]
    score: Decimal = Field(ge=-30, le=90)
    score_breakdown: dict[str, Decimal]
    factor_snapshot: FactorSnapshot


class CandidateExclusion(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    reason_code: Literal[
        "insufficient_history", "insufficient_liquidity", "invalid_history", "stale_history"
    ]
    observed_value: Decimal | None = None
    threshold: Decimal | None = None
    detail: str | None = None


class CandidateFunnel(BaseModel):
    """Counts for each deterministic stage of the local candidate scan."""

    model_config = ConfigDict(frozen=True)

    history_ready_size: int = Field(default=0, ge=0)
    factor_ready_size: int = Field(default=0, ge=0)
    liquidity_ready_size: int = Field(default=0, ge=0)
    ranked_size: int = Field(default=0, ge=0)
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    completeness: Literal["complete", "partial", "unavailable"] = "unavailable"
    blockers: tuple[str, ...] = ()

    def stage_counts(self) -> list[int]:
        return [
            self.history_ready_size,
            self.factor_ready_size,
            self.liquidity_ready_size,
            self.ranked_size,
        ]


class CandidateBoard(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset: Literal["a_share"] = "a_share"
    universe_status: Literal["ready", "empty"] = "ready"
    snapshot_id: str | None = None
    input_snapshot_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    as_of: date
    factor_version: Literal["a-share-factors-v1"] = FACTOR_VERSION
    universe_size: int = Field(default=0, ge=0)
    eligible_size: int = Field(default=0, ge=0)
    funnel: CandidateFunnel = Field(default_factory=CandidateFunnel)
    latest_trade_date: date | None = None
    sources: tuple[str, ...] = ()
    refresh_policy: Literal["after_close"] = "after_close"
    short_term: list[CandidateEntry]
    swing: list[CandidateEntry]
    exclusions: list[CandidateExclusion] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def derive_empty_universe(cls, value):
        if isinstance(value, dict) and "universe_status" not in value:
            value = dict(value)
            value["universe_status"] = (
                "empty" if not value.get("short_term") and not value.get("swing") else "ready"
            )
        return value

    @model_validator(mode="after")
    def require_one_frozen_factor_date(self) -> "CandidateBoard":
        entries = [*self.short_term, *self.swing]
        if any(item.factor_snapshot.as_of != self.as_of for item in entries):
            raise ValueError("candidate snapshots must match board as_of")
        return self


class CandidateScoreItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    status: Literal[
        "ready", "insufficient_history", "insufficient_liquidity",
        "invalid_history", "stale_history",
    ]
    score: Decimal | None = Field(default=None, ge=-30, le=90)
    latest_trade_date: date | None = None
    reason: Literal[
        "history_requires_60_bars", "liquidity_below_threshold",
        "history_invalid", "history_not_through_confirmed_day",
    ] | None = None


class CandidateScoreBoard(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    horizon: Literal["short_term", "swing"]
    factor_version: Literal["a-share-factors-v1"] = FACTOR_VERSION
    universe_size: int = Field(ge=0)
    eligible_size: int = Field(ge=0)
    latest_trade_date: date | None = None
    sources: tuple[str, ...] = ()
    items: tuple[CandidateScoreItem, ...]
