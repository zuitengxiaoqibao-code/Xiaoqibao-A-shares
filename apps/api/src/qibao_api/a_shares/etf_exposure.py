from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, localcontext
from typing import Literal, Mapping, Sequence

from qibao_api.contracts.quant_research import ETFExposure, ETFExposureResult


MIN_COMMON_DAYS = 60
MIN_AVERAGE_AMOUNT = Decimal("50000000")


@dataclass(frozen=True)
class ETFReturnCandidate:
    symbol: str
    name: str
    mapping_basis: Literal["industry", "theme", "correlation"]
    returns: Mapping[date, Decimal]
    average_amount_20d: Decimal | None
    source_snapshot_ids: tuple[str, ...] = ()


def map_etf_exposures(
    basket_returns: Mapping[date, Decimal],
    candidates: Sequence[ETFReturnCandidate],
    *,
    exposure_weights: Mapping[str, Decimal],
    generated_at: datetime,
) -> ETFExposureResult:
    exposures: list[ETFExposure] = []
    limitations: list[str] = []
    insufficient_samples = False
    low_liquidity = False
    for candidate in candidates:
        common_dates = tuple(sorted(set(basket_returns) & set(candidate.returns)))
        if len(common_dates) < MIN_COMMON_DAYS:
            insufficient_samples = True
            continue
        if (
            candidate.average_amount_20d is None
            or candidate.average_amount_20d < MIN_AVERAGE_AMOUNT
        ):
            low_liquidity = True
            continue
        correlation = _pearson(
            tuple(basket_returns[item] for item in common_dates),
            tuple(candidate.returns[item] for item in common_dates),
        )
        if correlation is None:
            limitations.append(f"{candidate.symbol} 收益序列没有足够离散度")
            continue
        exposures.append(ETFExposure(
            etf_symbol=candidate.symbol,
            etf_name=candidate.name,
            mapping_basis=candidate.mapping_basis,
            exposure_weight_percent=exposure_weights.get(candidate.symbol, Decimal("0")),
            common_sample_count=len(common_dates),
            correlation=correlation,
            average_amount_20d=candidate.average_amount_20d,
            status="ready",
            source_snapshot_ids=candidate.source_snapshot_ids,
        ))
    if insufficient_samples:
        limitations.append("ETF 与候选篮子的共同交易日少于 60 日")
    if low_liquidity:
        limitations.append("ETF 20日平均成交额未达到流动性门槛")
    if exposures:
        status = "partial" if limitations else "ready"
    elif insufficient_samples:
        status = "insufficient"
    else:
        status = "unavailable"
    if not candidates:
        limitations.append("当前没有可核验的 ETF 基础目录")
    return ETFExposureResult(
        status=status,
        exposures=tuple(sorted(exposures, key=lambda item: item.correlation or 0, reverse=True)),
        generated_at=generated_at,
        limitations=tuple(limitations),
    )


def _pearson(left: Sequence[Decimal], right: Sequence[Decimal]) -> Decimal | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left, Decimal("0")) / Decimal(len(left))
    right_mean = sum(right, Decimal("0")) / Decimal(len(right))
    left_delta = tuple(item - left_mean for item in left)
    right_delta = tuple(item - right_mean for item in right)
    left_variance = sum((item * item for item in left_delta), Decimal("0"))
    right_variance = sum((item * item for item in right_delta), Decimal("0"))
    if left_variance == 0 or right_variance == 0:
        return None
    covariance = sum(
        (first * second for first, second in zip(left_delta, right_delta, strict=True)),
        Decimal("0"),
    )
    with localcontext() as context:
        context.prec = 28
        return (covariance / (left_variance * right_variance).sqrt()).quantize(
            Decimal("0.0001")
        )
