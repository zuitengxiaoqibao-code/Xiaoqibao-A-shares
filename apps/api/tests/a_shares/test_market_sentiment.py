from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.market_sentiment import (
    MarketSentimentEvaluator,
    sentiment_band,
)
from qibao_api.contracts.market_sentiment import (
    HotspotSentimentInput,
    LiquidityBaseline,
    MarketFactorObservation,
    MarketBreadthObservation,
)


CHINA_TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 7, 18, 10, 30, tzinfo=CHINA_TZ)


def breadth(**changes) -> MarketBreadthObservation:
    values = {
        "requested_count": 100,
        "valid_count": 100,
        "rising_count": 75,
        "falling_count": 20,
        "flat_count": 5,
        "median_change_percent": Decimal("2"),
        "total_amount_wan": Decimal("15000"),
        "limit_up_count": 50,
        "limit_down_count": 2,
        "broken_limit_up_count": 10,
        "max_limit_streak": 4,
        "observed_at": NOW,
        "fetched_at": NOW,
        "source_snapshot_ids": ("tencent-batch-a", "tencent-batch-b"),
    }
    values.update(changes)
    return MarketBreadthObservation(**values)


def liquidity(*, quality: str = "ready") -> LiquidityBaseline:
    return LiquidityBaseline(
        amount_wan=Decimal("10000"),
        quality=quality,
        sample_size=20 if quality == "ready" else 5,
        evidence_ids=("liquidity-baseline",),
    )


def hotspot() -> HotspotSentimentInput:
    return HotspotSentimentInput(
        unique_theme_count=8,
        affected_symbol_count=50,
        persistent_theme_count=4,
        largest_theme_share_percent=Decimal("35"),
        evidence_ids=("hotspot-a", "hotspot-b"),
    )


def factors() -> MarketFactorObservation:
    return MarketFactorObservation(
        volatility_current_percent=Decimal("1.0"),
        volatility_baseline_percent=Decimal("1.0"),
        relative_amount=Decimal("1.0"),
        new_high_252_count=40,
        effective_count=100,
        benchmark_return_20d_percent=Decimal("5"),
        bond_etf_return_20d_percent=Decimal("1"),
        ma20_above_count=50,
        ma60_above_count=40,
        five_day_rising_count=60,
        sixty_day_new_low_count=20,
        rising_industry_count=12,
        effective_industry_count=20,
        small_cap_return_5d_percent=Decimal("4"),
        large_cap_return_5d_percent=Decimal("2"),
        yesterday_limit_up_return_percent=Decimal("2"),
        evidence_ids=("factor-fixture",),
    )


def evaluate(
    *,
    observation: MarketBreadthObservation | None = None,
    baseline: LiquidityBaseline | None = None,
    themes: HotspotSentimentInput | None = None,
    factor_values: MarketFactorObservation | None = None,
    previous_snapshot_id: str | None = None,
):
    return MarketSentimentEvaluator().evaluate(
        observation=observation or breadth(),
        liquidity_baseline=baseline,
        hotspot=themes,
        factors=factor_values,
        trading_date=date(2026, 7, 18),
        phase="intraday",
        generated_at=NOW,
        previous_snapshot_id=previous_snapshot_id,
    )


def test_formula_uses_the_nine_requested_components_and_weights() -> None:
    result = evaluate(
        baseline=liquidity(), themes=hotspot(), factor_values=factors(),
    )

    assert [item.name for item in result.components] == [
        "volatility", "activity", "price_strength", "risk_appetite",
        "breadth", "limit_ecology", "money_making", "sector_diffusion",
        "style_risk_preference",
    ]
    assert [item.weight for item in result.components] == [
        Decimal("15"), Decimal("15"), Decimal("10"), Decimal("10"),
        Decimal("15"), Decimal("15"), Decimal("10"), Decimal("5"),
        Decimal("5"),
    ]
    assert result.coverage_percent == Decimal("100.00")
    assert result.score == sum(
        (item.score or Decimal("0")) * item.weight / Decimal("100")
        for item in result.components
    ).quantize(Decimal("0.01"))
    assert result.formula_version == "a-share-sentiment-v2"


def test_sentiment_band_uses_frozen_boundaries() -> None:
    assert sentiment_band(None) == "unavailable"
    assert sentiment_band(Decimal("0")) == "panic"
    assert sentiment_band(Decimal("19.99")) == "panic"
    assert sentiment_band(Decimal("20")) == "cold"
    assert sentiment_band(Decimal("39.99")) == "cold"
    assert sentiment_band(Decimal("40")) == "neutral"
    assert sentiment_band(Decimal("59.99")) == "neutral"
    assert sentiment_band(Decimal("60")) == "active"
    assert sentiment_band(Decimal("79.99")) == "active"
    assert sentiment_band(Decimal("80")) == "overheated"
    assert sentiment_band(Decimal("100")) == "overheated"


def test_full_evidence_produces_a_ready_nine_factor_snapshot() -> None:
    result = evaluate(
        baseline=liquidity(), themes=hotspot(), factor_values=factors(),
    )

    assert result.quality == "ready"
    assert result.freshness == "current"
    assert result.coverage_percent == Decimal("100.00")
    assert result.score == Decimal("60.08")
    assert result.band == "active"
    assert result.formula_version == "a-share-sentiment-v2"
    assert {item.name for item in result.components} == {
        "volatility", "activity", "price_strength", "risk_appetite", "breadth",
        "limit_ecology", "money_making", "sector_diffusion", "style_risk_preference",
    }


def test_score_is_absent_below_required_coverage() -> None:
    result = evaluate(
        observation=breadth(max_limit_streak=None),
        baseline=None,
        themes=None,
    )

    assert result.coverage_percent < Decimal("70")
    assert result.quality == "unavailable"
    assert result.score is None
    assert result.band == "unavailable"
    assert "有效数据覆盖不足 70%" in result.risks


def test_partial_liquidity_baseline_can_cross_the_score_gate_without_hotspots() -> None:
    result = evaluate(
        observation=breadth(max_limit_streak=None),
        baseline=liquidity(quality="partial"),
        themes=None,
    )

    assert result.coverage_percent < Decimal("70")
    assert result.quality == "unavailable"
    assert result.score is None
    assert result.band == "unavailable"


def test_missing_market_breadth_never_falls_back_to_a_neutral_score() -> None:
    result = evaluate(
        observation=breadth(
            valid_count=0,
            rising_count=0,
            falling_count=0,
            flat_count=0,
            median_change_percent=None,
            total_amount_wan=None,
            limit_up_count=0,
            limit_down_count=0,
            broken_limit_up_count=0,
            max_limit_streak=None,
            source_snapshot_ids=(),
        ),
        baseline=liquidity(),
        themes=hotspot(),
    )

    assert result.score is None
    assert result.band == "unavailable"
    assert result.quality == "unavailable"
    assert "市场宽度不可用" in result.risks


def test_content_addressed_snapshot_id_is_stable_and_tracks_previous_snapshot() -> None:
    first = evaluate(
        baseline=liquidity(), themes=hotspot(), previous_snapshot_id="sentiment-old",
    )
    replay = evaluate(
        baseline=liquidity(), themes=hotspot(), previous_snapshot_id="sentiment-old",
    )
    changed = evaluate(
        observation=breadth(rising_count=74, falling_count=21),
        baseline=liquidity(), themes=hotspot(), previous_snapshot_id="sentiment-old",
    )

    assert first.snapshot_id == replay.snapshot_id
    assert first.snapshot_id != changed.snapshot_id
    assert first.previous_snapshot_id == "sentiment-old"
