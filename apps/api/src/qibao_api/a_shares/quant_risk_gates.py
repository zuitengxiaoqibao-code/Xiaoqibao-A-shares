from __future__ import annotations

from decimal import Decimal

from qibao_api.contracts.quant_research import (
    QuantRiskContext,
    QuantRiskGateSummary,
    RiskGateCheck,
)
from qibao_api.contracts.quant_strategy import QuantStrategyCandidate


BENEISH_KEYS = ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata")
BENEISH_WARNING = Decimal("-1.78")
MIN_LIQUIDITY_AMOUNT = Decimal("50000000")


def evaluate_risk_gates(
    candidate: QuantStrategyCandidate,
    context: QuantRiskContext,
) -> QuantRiskGateSummary:
    checks = (
        _evidence_gate(candidate),
        _tradability_gate(context),
        _financial_anomaly_gate(context),
        _signal_conflict_gate(candidate),
        _concentration_gate(context),
    )
    blockers = tuple(item.reason for item in checks if item.status == "block")
    if blockers:
        overall_status = "block"
    elif any(item.status in {"warn", "unavailable"} for item in checks):
        overall_status = "warn"
    else:
        overall_status = "pass"
    return QuantRiskGateSummary(
        symbol=candidate.symbol,
        overall_status=overall_status,
        checks=checks,
        blockers=blockers,
    )


def _evidence_gate(candidate: QuantStrategyCandidate) -> RiskGateCheck:
    coverage = candidate.evidence_coverage_percent
    if coverage < 50:
        status = "block"
        reason = "核心证据覆盖低于 50%"
    elif candidate.missing_evidence or coverage < 80:
        status = "warn"
        reason = "部分触发证据尚未补齐"
    else:
        status = "pass"
        reason = "核心证据覆盖达到观察要求"
    return RiskGateCheck(
        key="evidence",
        label="证据完整性",
        status=status,
        reason=reason,
        metric_value=coverage,
        threshold=Decimal("80"),
    )


def _tradability_gate(context: QuantRiskContext) -> RiskGateCheck:
    if context.suspended is True:
        return _gate("tradability", "可交易性", "block", "股票处于停牌状态", context)
    if context.limit_untradeable is True:
        return _gate(
            "tradability", "可交易性", "block", "涨跌停价格不可成交", context,
        )
    if context.average_amount_20d is None:
        return _gate(
            "tradability", "可交易性", "unavailable", "缺少20日平均成交额", context,
        )
    if context.average_amount_20d < MIN_LIQUIDITY_AMOUNT:
        return _gate(
            "tradability", "可交易性", "warn", "20日平均成交额低于流动性门槛",
            context, metric=context.average_amount_20d, threshold=MIN_LIQUIDITY_AMOUNT,
        )
    return _gate(
        "tradability", "可交易性", "pass", "停牌、涨跌停与流动性检查通过",
        context, metric=context.average_amount_20d, threshold=MIN_LIQUIDITY_AMOUNT,
    )


def _financial_anomaly_gate(context: QuantRiskContext) -> RiskGateCheck:
    components = context.beneish_components
    if components is None or any(key not in components for key in BENEISH_KEYS):
        return _gate(
            "financial_anomaly", "财务异常", "unavailable",
            "Beneish 所需财务字段不完整，不能视为通过", context,
        )
    score = (
        Decimal("-4.84")
        + Decimal("0.920") * components["dsri"]
        + Decimal("0.528") * components["gmi"]
        + Decimal("0.404") * components["aqi"]
        + Decimal("0.892") * components["sgi"]
        + Decimal("0.115") * components["depi"]
        - Decimal("0.172") * components["sgai"]
        + Decimal("4.679") * components["tata"]
        - Decimal("0.327") * components["lvgi"]
    ).quantize(Decimal("0.01"))
    status = "warn" if score > BENEISH_WARNING else "pass"
    reason = (
        "Beneish M-Score 高于异常观察阈值"
        if status == "warn" else "Beneish M-Score 未触发异常阈值"
    )
    return _gate(
        "financial_anomaly", "财务异常", status, reason, context,
        metric=score, threshold=BENEISH_WARNING,
    )


def _signal_conflict_gate(candidate: QuantStrategyCandidate) -> RiskGateCheck:
    if candidate.risk_flags:
        return RiskGateCheck(
            key="signal_conflict",
            label="信号冲突",
            status="warn",
            reason="；".join(candidate.risk_flags[:3]),
        )
    return RiskGateCheck(
        key="signal_conflict",
        label="信号冲突",
        status="pass",
        reason="当前候选未记录价量、风格或资金冲突",
    )


def _concentration_gate(context: QuantRiskContext) -> RiskGateCheck:
    exposures = tuple(
        item for item in (context.sector_exposure_percent, context.theme_exposure_percent)
        if item is not None
    )
    if not exposures:
        return _gate(
            "concentration", "暴露集中度", "unavailable",
            "缺少行业与题材暴露，不能判断拥挤度", context,
        )
    exposure = max(exposures)
    if exposure >= 60:
        status, reason = "block", "单一行业或题材暴露达到 60%"
    elif exposure >= 40:
        status, reason = "warn", "单一行业或题材暴露达到 40%"
    else:
        status, reason = "pass", "行业与题材暴露未触发集中度阈值"
    return _gate(
        "concentration", "暴露集中度", status, reason, context,
        metric=exposure, threshold=Decimal("40"),
    )


def _gate(
    key: str,
    label: str,
    status: str,
    reason: str,
    context: QuantRiskContext,
    *,
    metric: Decimal | None = None,
    threshold: Decimal | None = None,
) -> RiskGateCheck:
    return RiskGateCheck(
        key=key,
        label=label,
        status=status,
        reason=reason,
        metric_value=metric,
        threshold=threshold,
        source_snapshot_ids=context.source_snapshot_ids,
    )
