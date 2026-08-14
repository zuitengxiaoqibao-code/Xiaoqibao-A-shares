from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


ShadowOutcomeStatus = Literal["pending", "ready", "unavailable"]
AnalyticsStatus = Literal["ready", "partial", "insufficient"]
CalibrationStatus = Literal["ready", "insufficient"]
DriftStatus = Literal["stable", "warning", "drift", "insufficient"]


class ShadowOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    horizon: int = Field(ge=1)
    status: ShadowOutcomeStatus
    evaluated_trade_date: date | None = None
    return_percent: Decimal | None = None
    mfe_percent: Decimal | None = None
    mae_percent: Decimal | None = None
    invalidation_state: Literal["not_observed", "observed", "unavailable"] = "unavailable"
    evaluated_at: AwareDatetime | None = None
    limitation: str | None = None


class ShadowDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    as_of: date
    symbol: str = Field(pattern=r"^\d{6}$")
    formula_version: str
    candidate_status: str
    market_regime: str | None = None
    strategy_score: Decimal
    reference_price: Decimal | None = None
    frozen_at: AwareDatetime
    outcomes: tuple[ShadowOutcome, ...] = ()
    lifecycle: tuple[str, ...] = ()
    input_snapshot_ids: tuple[str, ...] = ()


class CalibrationBucket(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    score_min: int = Field(ge=0, le=100)
    score_max: int = Field(ge=0, le=100)
    sample_count: int = Field(ge=0)
    average_score: Decimal | None = None
    hit_rate_percent: Decimal | None = None
    average_return_percent: Decimal | None = None
    average_mfe_percent: Decimal | None = None
    average_mae_percent: Decimal | None = None
    calibration_gap_percent: Decimal | None = None
    status: CalibrationStatus


class StrategyDriftAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DriftStatus
    recent_sample_count: int = Field(ge=0)
    baseline_sample_count: int = Field(ge=0)
    recent_hit_rate_percent: Decimal | None = None
    baseline_hit_rate_percent: Decimal | None = None
    recent_average_return_percent: Decimal | None = None
    baseline_average_return_percent: Decimal | None = None
    reasons: tuple[str, ...] = ()


class RegimePerformance(BaseModel):
    model_config = ConfigDict(frozen=True)

    regime: Literal["情绪主升", "指数权重进攻", "轮动震荡", "冰点修复", "高位退潮", "缩量混沌"]
    sample_count: int = Field(ge=0)
    hit_rate_percent: Decimal | None = None
    average_return_percent: Decimal | None = None
    expected_value_percent: Decimal | None = None
    profit_loss_ratio: Decimal | None = Field(default=None, ge=0)
    max_consecutive_losses: int = Field(default=0, ge=0)
    max_drawdown_percent: Decimal | None = Field(default=None, ge=0)
    sharpe_ratio: Decimal | None = None


class QuantShadowAnalytics(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AnalyticsStatus
    horizon: Literal[1, 3, 5, 10, 20]
    mature_sample_count: int = Field(ge=0)
    pending_sample_count: int = Field(ge=0)
    hit_rate_percent: Decimal | None = None
    average_return_percent: Decimal | None = None
    average_mfe_percent: Decimal | None = None
    average_mae_percent: Decimal | None = None
    brier_score: Decimal | None = None
    buckets: tuple[CalibrationBucket, ...] = ()
    regime_performance: tuple[RegimePerformance, ...] = ()
    drift: StrategyDriftAssessment
    generated_at: AwareDatetime
    limitations: tuple[str, ...] = ()
