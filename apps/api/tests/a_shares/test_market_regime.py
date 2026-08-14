from decimal import Decimal

from qibao_api.a_shares.market_regime import assess_market_regime
from qibao_api.contracts.market_overview import OverviewRegimeMetrics


def metrics(**updates) -> OverviewRegimeMetrics:
    values = {
        "up_ratio": Decimal("66"), "zt_ratio": Decimal("1.4"),
        "dt_ratio": Decimal("0.1"), "median_ret": Decimal("1.2"),
        "amt_heat": Decimal("1.15"), "strong_close_ratio": Decimal("72"),
        "weak_close_ratio": Decimal("12"), "limit_fail_ratio": Decimal("18"),
        "panic_ratio": Decimal("2"), "amp_ratio": Decimal("18"),
        "net_positive_ratio": None, "large_amount_strong_close_ratio": Decimal("70"),
        "factor_coverage_percent": Decimal("90.91"),
    }
    values.update(updates)
    return OverviewRegimeMetrics(**values)


def test_regime_engine_marks_missing_net_flow_and_selects_emotion_advance() -> None:
    result = assess_market_regime(metrics(), max_index_change_percent=Decimal("0.6"))

    assert result.regime == "情绪主升"
    assert result.emotion_score >= Decimal("70")
    assert result.market_coef == Decimal("1")
    assert result.coverage_percent == Decimal("85.00")
    assert result.missing_factors == ("net_positive_ratio", "previous_risk_score")
    assert result.rule_matched is True
    assert "0轴低吸模型" in result.suitable_strategies


def test_regime_engine_prioritizes_high_level_retreat_risk() -> None:
    result = assess_market_regime(metrics(
        dt_ratio=Decimal("1.3"), weak_close_ratio=Decimal("62"),
        limit_fail_ratio=Decimal("55"), panic_ratio=Decimal("60"),
    ))

    assert result.regime == "高位退潮"
    assert result.risk_score >= Decimal("65")
    assert result.market_coef == Decimal("0.2")
    assert "空仓防守模型" in result.suitable_strategies


def test_regime_engine_exposes_previous_risk_only_when_verified() -> None:
    result = assess_market_regime(
        metrics(net_positive_ratio=Decimal("52")),
        previous_risk_score=Decimal("68"),
    )

    assert result.previous_risk_score == Decimal("68")
    assert "previous_risk_score" not in result.missing_factors
