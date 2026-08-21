from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Sequence

from qibao_api.contracts.quant_research import (
    FactorDefinition,
    FactorHealth,
    FactorObservation,
)


MIN_CROSS_SECTION = 30
MIN_VALID_DAYS = 20
STALE_AFTER_CALENDAR_DAYS = 7
FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")


def evaluate_factor_health(
    definition: FactorDefinition,
    observations: Sequence[FactorObservation],
    *,
    generated_at: datetime,
    expected_sample_count: int | None = None,
) -> FactorHealth:
    selected = tuple(item for item in observations if item.factor_id == definition.factor_id)
    valid = tuple(
        item for item in selected
        if item.value is not None and item.forward_return is not None
    )
    expected = max(expected_sample_count or len(selected), len(valid))
    coverage = _percent(len(valid), expected)
    grouped: dict[object, list[FactorObservation]] = defaultdict(list)
    for item in valid:
        grouped[item.trade_date].append(item)

    daily_ics: list[tuple[object, Decimal]] = []
    undersized_days = 0
    for trade_date in sorted(grouped):
        cross_section = grouped[trade_date]
        if len(cross_section) < MIN_CROSS_SECTION:
            undersized_days += 1
            continue
        raw_ic = _spearman(
            tuple(item.value for item in cross_section if item.value is not None),
            tuple(
                item.forward_return for item in cross_section
                if item.forward_return is not None
            ),
        )
        if raw_ic is not None:
            daily_ics.append((trade_date, _apply_direction(raw_ic, definition.direction)))

    ic_values = tuple(item[1] for item in daily_ics)
    ic_mean = _mean(ic_values)
    ic_std = _standard_deviation(ic_values)
    icir = (
        (ic_mean / ic_std).quantize(FOUR_PLACES)
        if ic_mean is not None and ic_std not in {None, Decimal("0")}
        else None
    )
    latest_valid_date = daily_ics[-1][0] if daily_ics else None
    limitations: list[str] = []
    if undersized_days:
        limitations.append(
            f"{undersized_days} 个交易日横截面不足；每日横截面至少需要 30 只股票"
        )
    if len(daily_ics) < MIN_VALID_DAYS:
        limitations.append(
            f"有效交易日少于 20 日，当前 {len(daily_ics)} 日，不输出可靠 ICIR"
        )
        icir = None
    if ic_std == 0 and len(daily_ics) >= MIN_VALID_DAYS:
        limitations.append("日度 RankIC 没有离散度，ICIR 不可计算")
    is_stale = (
        latest_valid_date is not None
        and (generated_at.date() - latest_valid_date).days > STALE_AFTER_CALENDAR_DAYS
    )
    if is_stale:
        limitations.append("最近有效数据已陈旧")

    if is_stale:
        status = "stale"
    elif len(daily_ics) < MIN_VALID_DAYS:
        status = "insufficient"
    elif ic_mean is not None and ic_mean > 0:
        status = "healthy"
    else:
        status = "watch"

    snapshot_ids = tuple(dict.fromkeys(
        snapshot_id
        for item in valid
        for snapshot_id in item.source_snapshot_ids
    ))
    return FactorHealth(
        factor_id=definition.factor_id,
        name=definition.name,
        family=definition.family,
        status=status,
        sample_count=len(valid),
        valid_day_count=len(daily_ics),
        coverage_percent=coverage,
        missing_rate_percent=(Decimal("100") - coverage).quantize(TWO_PLACES),
        rank_ic_20=_window_mean(ic_values, 20),
        rank_ic_60=_window_mean(ic_values, 60),
        rank_ic_120=_window_mean(ic_values, 120),
        ic_mean=ic_mean,
        ic_std=ic_std,
        icir=icir,
        direction_accuracy_percent=_direction_accuracy(ic_values),
        latest_valid_date=latest_valid_date,
        generated_at=generated_at,
        source_snapshot_ids=snapshot_ids,
        limitations=tuple(limitations),
    )


def _apply_direction(value: Decimal, direction: str) -> Decimal:
    if direction == "negative":
        return -value
    if direction == "bidirectional":
        return abs(value)
    return value


def _spearman(values: Sequence[Decimal], returns: Sequence[Decimal]) -> Decimal | None:
    if len(values) != len(returns) or len(values) < 2:
        return None
    return _pearson(_average_ranks(values), _average_ranks(returns))


def _average_ranks(values: Sequence[Decimal]) -> tuple[Decimal, ...]:
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    result = [Decimal("0")] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average_rank = (Decimal(start + 1) + Decimal(end)) / Decimal("2")
        for position in range(start, end):
            result[ordered[position]] = average_rank
        start = end
    return tuple(result)


def _pearson(left: Sequence[Decimal], right: Sequence[Decimal]) -> Decimal | None:
    left_mean = sum(left, Decimal("0")) / Decimal(len(left))
    right_mean = sum(right, Decimal("0")) / Decimal(len(right))
    left_delta = tuple(item - left_mean for item in left)
    right_delta = tuple(item - right_mean for item in right)
    covariance = sum(
        (first * second for first, second in zip(left_delta, right_delta, strict=True)),
        Decimal("0"),
    )
    left_variance = sum((item * item for item in left_delta), Decimal("0"))
    right_variance = sum((item * item for item in right_delta), Decimal("0"))
    if left_variance == 0 or right_variance == 0:
        return None
    with localcontext() as context:
        context.prec = 28
        denominator = (left_variance * right_variance).sqrt()
        return (covariance / denominator).quantize(FOUR_PLACES)


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(FOUR_PLACES)


def _window_mean(values: Sequence[Decimal], size: int) -> Decimal | None:
    return _mean(values[-size:]) if values else None


def _standard_deviation(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum(((item - mean) ** 2 for item in values), Decimal("0")) / Decimal(
        len(values)
    )
    with localcontext() as context:
        context.prec = 28
        return variance.sqrt().quantize(FOUR_PLACES)


def _direction_accuracy(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    correct = sum(1 for item in values if item > 0)
    return _percent(correct, len(values))


def _percent(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0.00")
    return (
        Decimal(numerator) / Decimal(denominator) * Decimal("100")
    ).quantize(TWO_PLACES)
