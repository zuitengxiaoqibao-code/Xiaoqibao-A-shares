from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from qibao_api.contracts.quant_calibration import (
    CalibrationIntegrity,
    CalibrationSplit,
    QuantCalibrationReport,
)


def _rate(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return (Decimal(sum(value > 0 for value in values)) / Decimal(len(values)) * 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _avg(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def build_calibration_report(ledger, *, horizon: int, generated_at: datetime) -> QuantCalibrationReport:
    records = sorted(ledger.recent(limit=500), key=lambda item: (item.as_of, item.symbol))
    rows = []
    for record in records:
        outcome = next((item for item in record.outcomes if item.horizon == horizon and item.status == "ready"), None)
        if outcome is not None and outcome.return_percent is not None:
            rows.append((record.as_of, record.formula_version, outcome.return_percent))
    total = len(records)
    mature = len(rows)
    if not rows:
        return QuantCalibrationReport(
            status="unavailable", horizon=horizon,
            total_sample_count=total, mature_sample_count=0,
            splits=tuple(CalibrationSplit(name=name, sample_count=0) for name in ("train", "validation", "test")),
            integrity=CalibrationIntegrity(
                future_function_check="unavailable", survivorship_check="unavailable",
                duplicate_decision_check="passed",
                limitations=("没有成熟的真实影子结果，无法进行走样校准",),
            ),
            generated_at=generated_at,
            limitations=("没有成熟的真实影子结果，无法进行走样校准",),
        )
    split_bounds = (0, int(mature * 0.6), int(mature * 0.8), mature)
    splits = []
    for name, start, end in zip(("train", "validation", "test"), split_bounds, split_bounds[1:]):
        values = [row[2] for row in rows[start:end]]
        dates = [row[0] for row in rows[start:end]]
        splits.append(CalibrationSplit(
            name=name,
            start_date=min(dates) if dates else None,
            end_date=max(dates) if dates else None,
            sample_count=len(values),
            hit_rate_percent=_rate(values),
            average_return_percent=_avg(values),
        ))
    duplicate_check = len({(row[0], row[1]) for row in rows}) == len(rows)
    limitations = ["影子结果记录的是毛收益，成本与滑点尚未在该账本冻结"]
    if mature < 30:
        limitations.append("成熟样本少于 30 条，仅作观察，不作为可靠性结论")
    return QuantCalibrationReport(
        status="ready" if mature >= 30 else "partial",
        horizon=horizon,
        formula_versions=tuple(sorted({row[1] for row in rows})),
        total_sample_count=total,
        mature_sample_count=mature,
        splits=tuple(splits),
        integrity=CalibrationIntegrity(
            future_function_check="passed" if all(row[0] <= generated_at.date() for row in rows) else "failed",
            survivorship_check="unavailable",
            duplicate_decision_check="passed" if duplicate_check else "failed",
            limitations=("幸存者偏差需要冻结历史证券目录后才能验证",),
        ),
        gross_hit_rate_percent=_rate([row[2] for row in rows]),
        gross_average_return_percent=_avg([row[2] for row in rows]),
        generated_at=generated_at,
        limitations=tuple(limitations),
    )
