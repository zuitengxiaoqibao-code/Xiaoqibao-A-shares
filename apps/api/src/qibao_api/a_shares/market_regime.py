from decimal import Decimal, ROUND_HALF_UP

from qibao_api.contracts.market_overview import (
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
)


HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")
REGIME_FORMULA_VERSION = "a-share-short-regime-v2.0"


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal(), min(HUNDRED, value))


def _score_ratio(value: Decimal | None, high_anchor: Decimal) -> Decimal | None:
    if value is None:
        return None
    return _clamp(value / high_anchor * HUNDRED)


def _heat_standard(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    anchors = (
        (Decimal("0.60"), Decimal("0")),
        (Decimal("0.85"), Decimal("30")),
        (Decimal("1.00"), Decimal("50")),
        (Decimal("1.20"), Decimal("70")),
        (Decimal("1.60"), Decimal("100")),
    )
    if value <= anchors[0][0]:
        return Decimal()
    if value >= anchors[-1][0]:
        return HUNDRED
    for (left_x, left_y), (right_x, right_y) in zip(anchors, anchors[1:]):
        if left_x <= value <= right_x:
            progress = (value - left_x) / (right_x - left_x)
            return left_y + progress * (right_y - left_y)
    return None


def _weighted_score(
    values: tuple[tuple[Decimal | None, Decimal, str], ...],
) -> tuple[Decimal | None, Decimal, tuple[str, ...]]:
    available_weight = sum(
        (weight for value, weight, _name in values if value is not None),
        Decimal(),
    )
    missing = tuple(name for value, _weight, name in values if value is None)
    if available_weight <= 0:
        return None, Decimal(), missing
    weighted = sum(
        (value * weight for value, weight, _name in values if value is not None),
        Decimal(),
    )
    score = (weighted / available_weight).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    coverage = (available_weight * HUNDRED).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return score, coverage, missing


STRATEGIES = {
    "情绪主升": (
        Decimal("1"), ("0轴低吸模型", "分歧转一致模型"),
        ("后排追涨", "一致加速追高"),
    ),
    "指数权重进攻": (
        Decimal("0.8"), ("权重容量低吸模型",),
        ("无成交小票接力", "缩量突破追高"),
    ),
    "轮动震荡": (
        Decimal("0.5"), ("0轴低吸模型",),
        ("高开追涨", "下午临时冲高"),
    ),
    "冰点修复": (
        Decimal("0.4"), ("恐慌低吸模型", "反核修复模型"),
        ("主跌初期抄底", "未打开跌停板"),
    ),
    "高位退潮": (
        Decimal("0.2"), ("空仓防守模型",),
        ("高位接力", "一致加速", "无确认反核"),
    ),
    "缩量混沌": (
        Decimal("0.1"), ("空仓防守模型",),
        ("追连板", "趋势突破", "高位加速"),
    ),
}


def assess_market_regime(
    metrics: OverviewRegimeMetrics,
    *,
    max_index_change_percent: Decimal | None = None,
    previous_risk_score: Decimal | None = None,
) -> OverviewRegimeAssessment:
    zt_score = _score_ratio(metrics.zt_ratio, Decimal("2.00"))
    dt_score = _score_ratio(metrics.dt_ratio, Decimal("1.50"))
    heat_standard = _heat_standard(metrics.amt_heat)
    emotion, coverage, emotion_missing = _weighted_score((
        (metrics.up_ratio, Decimal("0.25"), "up_ratio"),
        (zt_score, Decimal("0.20"), "zt_ratio_standard"),
        (metrics.strong_close_ratio, Decimal("0.20"), "strong_close_ratio"),
        (metrics.net_positive_ratio, Decimal("0.15"), "net_positive_ratio"),
        (
            HUNDRED - dt_score if dt_score is not None else None,
            Decimal("0.20"), "dt_ratio_standard",
        ),
    ))
    risk, _risk_coverage, risk_missing = _weighted_score((
        (dt_score, Decimal("0.30"), "dt_ratio_standard"),
        (metrics.panic_ratio, Decimal("0.25"), "panic_ratio"),
        (metrics.limit_fail_ratio, Decimal("0.25"), "limit_fail_ratio"),
        (metrics.weak_close_ratio, Decimal("0.20"), "weak_close_ratio"),
    ))
    heat, _heat_coverage, heat_missing = _weighted_score((
        (heat_standard, Decimal("0.40"), "amt_heat_standard"),
        (metrics.amp_ratio, Decimal("0.30"), "amp_ratio"),
        (zt_score, Decimal("0.30"), "zt_ratio_standard"),
    ))
    rotation, _rotation_coverage, rotation_missing = _weighted_score((
        (metrics.amp_ratio, Decimal("0.40"), "amp_ratio"),
        (metrics.limit_fail_ratio, Decimal("0.30"), "limit_fail_ratio"),
        (
            abs(metrics.up_ratio - Decimal("50"))
            if metrics.up_ratio is not None else None,
            Decimal("0.30"), "up_ratio",
        ),
    ))
    missing = tuple(dict.fromkeys((
        *emotion_missing, *risk_missing, *heat_missing, *rotation_missing,
        *(("previous_risk_score",) if previous_risk_score is None else ()),
    )))

    reasons = []
    rule_matched = True
    if risk is not None and (
        risk >= Decimal("65")
        or (metrics.limit_fail_ratio or Decimal()) >= Decimal("40")
    ):
        regime = "高位退潮"
        reasons.append("风险分或实时触板弱收率达到退潮阈值")
    elif (
        previous_risk_score is not None
        and previous_risk_score >= Decimal("65")
        and risk is not None and risk <= Decimal("55")
        and (metrics.up_ratio or Decimal()) >= Decimal("50")
    ):
        regime = "冰点修复"
        reasons.append("昨日高风险，今日风险回落且上涨率恢复到50%以上")
    elif (
        metrics.amt_heat is not None and metrics.amt_heat >= Decimal("1.2")
        and (metrics.up_ratio or Decimal()) >= Decimal("55")
        and (metrics.zt_ratio or Decimal()) <= Decimal("1.5")
        and (metrics.large_amount_strong_close_ratio or Decimal()) >= Decimal("60")
        and (max_index_change_percent or Decimal()) >= Decimal("0.5")
    ):
        regime = "指数权重进攻"
        reasons.append("成交放大、指数走强且大成交股票强收比例较高")
    elif emotion is not None and emotion >= Decimal("70") and (risk or HUNDRED) < Decimal("45"):
        regime = "情绪主升"
        reasons.append("情绪分达到70且风险分低于45")
    elif (
        metrics.amt_heat is not None and metrics.amt_heat < Decimal("0.85")
        and (metrics.zt_ratio or Decimal()) < Decimal("0.5")
        and Decimal("45") <= (metrics.up_ratio or Decimal()) <= Decimal("55")
    ):
        regime = "缩量混沌"
        reasons.append("成交热度低、涨停率低且上涨率接近均衡")
    elif (
        emotion is not None and Decimal("45") <= emotion < Decimal("70")
        and (risk or HUNDRED) < Decimal("60")
        and (rotation or Decimal()) >= Decimal("60")
    ):
        regime = "轮动震荡"
        reasons.append("情绪中性、风险可控且轮动分达到阈值")
    elif metrics.amt_heat is not None and metrics.amt_heat < Decimal("0.85"):
        regime = "缩量混沌"
        rule_matched = False
        reasons.append("低成交热度近似缩量混沌，但未完整满足涨停率和上涨率条件")
    else:
        regime = "轮动震荡"
        rule_matched = False
        reasons.append("低置信近似分类：未完整命中六类风格的任一阈值组合")

    market_coef, suitable, avoid = STRATEGIES[regime]
    return OverviewRegimeAssessment(
        regime=regime,
        emotion_score=emotion,
        risk_score=risk,
        previous_risk_score=previous_risk_score,
        heat_score=heat,
        rotation_score=rotation,
        coverage_percent=coverage,
        market_coef=market_coef,
        suitable_strategies=suitable,
        avoid_strategies=avoid,
        reasons=tuple(reasons),
        missing_factors=missing,
        rule_matched=rule_matched,
        quality="ready" if not missing else "partial",
    )
