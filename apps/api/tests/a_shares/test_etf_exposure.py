from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.etf_exposure import ETFReturnCandidate, map_etf_exposures


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def returns(count: int, *, multiplier: str = "1") -> dict[date, Decimal]:
    start = date(2026, 5, 1)
    return {
        start + timedelta(days=index): Decimal(index) * Decimal(multiplier)
        for index in range(count)
    }


def etf(count: int, *, amount: str = "200000000") -> ETFReturnCandidate:
    return ETFReturnCandidate(
        symbol="510300",
        name="沪深300ETF",
        mapping_basis="correlation",
        returns=returns(count, multiplier="2"),
        average_amount_20d=Decimal(amount),
        source_snapshot_ids=("etf-bars-1",),
    )


def test_etf_correlation_requires_sixty_common_trade_days() -> None:
    result = map_etf_exposures(
        returns(59),
        (etf(59),),
        exposure_weights={"510300": Decimal("100")},
        generated_at=NOW,
    )

    assert result.status == "insufficient"
    assert result.exposures == ()
    assert "共同交易日少于 60 日" in result.limitations[0]


def test_etf_mapping_keeps_real_correlation_liquidity_and_lineage() -> None:
    result = map_etf_exposures(
        returns(60),
        (etf(60),),
        exposure_weights={"510300": Decimal("75")},
        generated_at=NOW,
    )

    assert result.status == "ready"
    assert result.exposures[0].correlation == Decimal("1.0000")
    assert result.exposures[0].common_sample_count == 60
    assert result.exposures[0].exposure_weight_percent == Decimal("75")
    assert result.exposures[0].source_snapshot_ids == ("etf-bars-1",)


def test_low_liquidity_etf_is_not_presented_as_actionable_mapping() -> None:
    result = map_etf_exposures(
        returns(60),
        (etf(60, amount="10000000"),),
        exposure_weights={"510300": Decimal("100")},
        generated_at=NOW,
    )

    assert result.status == "unavailable"
    assert result.exposures == ()
    assert any("流动性" in item for item in result.limitations)

