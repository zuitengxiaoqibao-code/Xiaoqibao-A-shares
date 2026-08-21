from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.factor_health import evaluate_factor_health
from qibao_api.contracts.quant_research import FactorDefinition, FactorObservation


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def definition(*, direction: str = "positive") -> FactorDefinition:
    return FactorDefinition(
        factor_id="return_5d",
        name="5日涨跌幅",
        family="momentum",
        direction=direction,
        required_fields=("close",),
        minimum_history=6,
        formula_version="a-share-factors-v1",
        owner="system",
        lifecycle="active",
        registered_at=NOW,
    )


def observations(
    day_count: int,
    stock_count: int,
    *,
    reverse_return: bool = False,
) -> tuple[FactorObservation, ...]:
    start = date(2026, 8, 21) - timedelta(days=day_count - 1)
    result = []
    for day_index in range(day_count):
        trade_date = start + timedelta(days=day_index)
        for stock_index in range(stock_count):
            value = Decimal(stock_index)
            forward_return = Decimal(stock_count - stock_index if reverse_return else stock_index)
            result.append(FactorObservation(
                factor_id="return_5d",
                trade_date=trade_date,
                symbol=f"{600000 + stock_index:06d}",
                value=value,
                forward_return=forward_return,
                source_snapshot_ids=(f"bars-{trade_date.isoformat()}",),
            ))
    return tuple(result)


def test_factor_health_uses_daily_spearman_rank_ic() -> None:
    result = evaluate_factor_health(
        definition(), observations(20, 30), generated_at=NOW,
    )

    assert result.status == "healthy"
    assert result.rank_ic_20 == Decimal("1.0000")
    assert result.ic_mean == Decimal("1.0000")
    assert result.valid_day_count == 20
    assert result.sample_count == 600
    assert result.direction_accuracy_percent == Decimal("100.00")


def test_factor_health_does_not_invent_icir_for_short_history() -> None:
    result = evaluate_factor_health(
        definition(), observations(5, 30), generated_at=NOW,
    )

    assert result.status == "insufficient"
    assert result.icir is None
    assert any("有效交易日少于 20 日" in item for item in result.limitations)


def test_negative_factor_direction_is_applied_before_health_judgement() -> None:
    result = evaluate_factor_health(
        definition(direction="negative"),
        observations(20, 30, reverse_return=True),
        generated_at=NOW,
    )

    assert result.status == "healthy"
    assert result.rank_ic_20 == Decimal("1.0000")


def test_cross_sections_smaller_than_thirty_stay_insufficient() -> None:
    result = evaluate_factor_health(
        definition(), observations(20, 29), generated_at=NOW,
    )

    assert result.status == "insufficient"
    assert result.valid_day_count == 0
    assert any("每日横截面至少需要 30 只股票" in item for item in result.limitations)


def test_health_reports_real_coverage_and_stale_latest_date() -> None:
    old_now = datetime(2026, 7, 1, 7, 0, tzinfo=timezone.utc)
    old = tuple(
        item.model_copy(update={"trade_date": item.trade_date - timedelta(days=60)})
        for item in observations(20, 30)
    )

    result = evaluate_factor_health(
        definition(), old, generated_at=old_now, expected_sample_count=1_200,
    )

    assert result.status == "stale"
    assert result.coverage_percent == Decimal("50.00")
    assert result.missing_rate_percent == Decimal("50.00")
    assert "最近有效数据已陈旧" in result.limitations
