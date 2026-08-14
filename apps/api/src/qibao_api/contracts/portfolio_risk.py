from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class PortfolioPositionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    shares: Decimal = Field(gt=0)
    cost_price: Decimal = Field(gt=0)


class PortfolioPositionUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    shares: Decimal = Field(gt=0)
    cost_price: Decimal = Field(gt=0)


class PortfolioRiskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    positions: tuple[PortfolioPositionInput, ...] = Field(min_length=1, max_length=30)
    as_of: date | None = None


class PortfolioPositionRisk(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    shares: Decimal
    cost_price: Decimal
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    pnl: Decimal | None = None
    pnl_percent: Decimal | None = None
    weight_percent: Decimal | None = None
    industry: str | None = None
    status: Literal["ready", "unavailable"]
    limitations: tuple[str, ...] = ()


class IndustryConcentration(BaseModel):
    model_config = ConfigDict(frozen=True)

    industry: str
    market_value: Decimal
    weight_percent: Decimal
    symbols: tuple[str, ...]


class CorrelationPair(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_symbol: str
    right_symbol: str
    correlation: Decimal
    overlap_days: int = Field(ge=20)


class PortfolioStressScenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: Literal["market_down_2", "largest_industry_down_5", "correlated_pair_down_7"]
    label: str
    shock_percent: Decimal
    estimated_loss: Decimal | None = None
    status: Literal["ready", "unavailable"]
    detail: str


class PortfolioRiskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "partial", "unavailable"]
    as_of: date
    observed_at: AwareDatetime
    total_market_value: Decimal | None = None
    total_cost: Decimal | None = None
    total_pnl: Decimal | None = None
    total_pnl_percent: Decimal | None = None
    hhi: Decimal | None = None
    average_correlation: Decimal | None = None
    market_regime: str | None = None
    market_position_cap_percent: Decimal | None = None
    positions: tuple[PortfolioPositionRisk, ...] = ()
    industries: tuple[IndustryConcentration, ...] = ()
    high_correlation_pairs: tuple[CorrelationPair, ...] = ()
    stress_scenarios: tuple[PortfolioStressScenario, ...] = ()
    warnings: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
