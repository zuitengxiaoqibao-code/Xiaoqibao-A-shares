from __future__ import annotations

from collections.abc import Mapping

from qibao_api.a_shares.opportunity_registry import build_default_opportunity_registry
from qibao_api.a_shares.quant_risk_gates import evaluate_risk_gates
from qibao_api.contracts.quant_research import (
    OpportunityPitch,
    QuantRiskContext,
    ShadowCohortEvidence,
)
from qibao_api.contracts.quant_strategy import QuantStrategyCandidate


MIN_MATURE_COHORT = 20


def build_pitch_cards(
    candidates: tuple[QuantStrategyCandidate, ...],
    *,
    regime: str | None,
    risk_contexts: Mapping[str, QuantRiskContext],
    cohort_evidence: Mapping[str, ShadowCohortEvidence],
    source_snapshot_ids: tuple[str, ...] = (),
) -> tuple[OpportunityPitch, ...]:
    definitions = {
        item.opportunity_id: item
        for item in build_default_opportunity_registry().definitions()
    }
    cards = []
    for candidate in candidates:
        opportunity_type = _opportunity_type(candidate.model)
        definition = definitions[opportunity_type]
        risk_gate = evaluate_risk_gates(
            candidate,
            risk_contexts.get(candidate.symbol, QuantRiskContext()),
        )
        cohort = cohort_evidence.get(opportunity_type)
        limitations: list[str] = []
        mature = (
            cohort is not None
            and cohort.sample_count >= MIN_MATURE_COHORT
            and cohort.status in {"ready", "partial"}
            and cohort.hit_rate_percent is not None
        )
        if not mature:
            limitations.append("同类成熟样本不足 20 条，不展示校准胜率")
        if regime is None:
            limitations.append("市场风格尚未确认")
        elif regime not in definition.applicable_regimes:
            limitations.append("当前市场风格不在该机会类型的适用范围")
        if risk_gate.overall_status == "block":
            status = "excluded"
        elif candidate.trigger_confirmed:
            status = "triggered"
        else:
            status = "watch"
        trigger_rules = candidate.buy_triggers or definition.trigger_rules
        invalidation_rules = candidate.invalidation_rules or definition.invalidation_rules
        cards.append(OpportunityPitch(
            symbol=candidate.symbol,
            name=candidate.name,
            opportunity_type=opportunity_type,
            opportunity_name=definition.name,
            market_regime=regime,
            status=status,
            strategy_score=candidate.strategy_score,
            trigger_confirmed=candidate.trigger_confirmed,
            reference_price=candidate.reference_price,
            core_evidence=(
                f"策略综合分 {candidate.strategy_score}",
                f"证据覆盖 {candidate.evidence_coverage_percent}%",
                "盘中触发已确认" if candidate.trigger_confirmed else "等待盘中触发确认",
            ),
            trigger_rules=tuple(trigger_rules),
            invalidation_rules=tuple(invalidation_rules),
            risk_gate=risk_gate,
            shadow_sample_count=cohort.sample_count if cohort is not None else 0,
            calibrated_hit_rate_percent=(
                cohort.hit_rate_percent if mature and cohort is not None else None
            ),
            average_return_percent=(
                cohort.average_return_percent if mature and cohort is not None else None
            ),
            sources=candidate.sources,
            source_snapshot_ids=source_snapshot_ids,
            limitations=tuple(limitations),
        ))
    return tuple(cards)


def _opportunity_type(model: str) -> str:
    if "恐慌" in model or "反核" in model:
        return "oversold_recovery"
    if "分歧" in model:
        return "volume_breakout"
    if "空仓" in model:
        return "defensive_low_volatility"
    return "trend_continuation"
