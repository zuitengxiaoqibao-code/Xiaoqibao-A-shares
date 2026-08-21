from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from qibao_api.a_shares.opportunity_registry import build_default_opportunity_registry
from qibao_api.a_shares.factor_registry import build_default_factor_registry
from qibao_api.a_shares.quant_risk_gates import evaluate_risk_gates
from qibao_api.a_shares.quant_research_snapshot import QuantResearchSnapshotStore
from qibao_api.contracts.quant_research import (
    OpportunityPitch,
    QuantResearchSnapshot,
    QuantRiskContext,
    ResearchModuleStatus,
    ShadowCohortEvidence,
)
from qibao_api.contracts.quant_strategy import QuantStrategyCandidate


MIN_MATURE_COHORT = 20
CACHE_TTL_SECONDS = 60


class QuantResearchIntelligenceService:
    def __init__(
        self,
        strategy_service,
        shadow_ledger,
        snapshot_store: QuantResearchSnapshotStore,
    ) -> None:
        self.strategy_service = strategy_service
        self.shadow_ledger = shadow_ledger
        self.snapshot_store = snapshot_store

    def current(self, now: datetime) -> QuantResearchSnapshot:
        cached = self.snapshot_store.load_latest()
        if cached is not None:
            age = max(0, int((now - cached.generated_at).total_seconds()))
            if age <= CACHE_TTL_SECONDS:
                return cached.model_copy(update={
                    "snapshot_source": "cache",
                    "refresh_state": "ready",
                    "refresh_progress": 100,
                    "refresh_stage": "已加载最新研究快照，实时监控中",
                })
        try:
            return self._build(now)
        except (OSError, ValueError) as error:
            if cached is not None:
                return cached.model_copy(update={
                    "status": "stale",
                    "snapshot_source": "cache",
                    "refresh_state": "failed",
                    "refresh_progress": 100,
                    "refresh_stage": "最新研究刷新失败，继续展示上次完整快照",
                    "limitations": tuple(dict.fromkeys((
                        *cached.limitations,
                        f"最新研究刷新失败：{type(error).__name__}",
                    ))),
                })
            return self._empty(now, f"研究快照建立失败：{type(error).__name__}")

    def _build(self, now: datetime) -> QuantResearchSnapshot:
        dashboard = self.strategy_service.current(now, limit=12)
        opportunity_types = tuple(dict.fromkeys(
            _opportunity_type(item.model) for item in dashboard.candidates
        ))
        cohorts: dict[str, ShadowCohortEvidence] = {}
        shadow_error: str | None = None
        for opportunity_type in opportunity_types:
            try:
                analytics = self.shadow_ledger.analytics(
                    horizon=20,
                    decision_source="opportunity_scan",
                    opportunity_type=opportunity_type,
                )
            except (OSError, ValueError) as error:
                shadow_error = type(error).__name__
                continue
            cohorts[opportunity_type] = ShadowCohortEvidence(
                opportunity_type=opportunity_type,
                decision_source="opportunity_scan",
                horizon=20,
                status=analytics.status,
                sample_count=analytics.mature_sample_count,
                hit_rate_percent=analytics.hit_rate_percent,
                average_return_percent=analytics.average_return_percent,
                generated_at=analytics.generated_at,
                limitations=analytics.limitations,
            )
        pitches = build_pitch_cards(
            dashboard.candidates,
            regime=dashboard.regime.regime,
            risk_contexts={},
            cohort_evidence=cohorts,
            source_snapshot_ids=dashboard.input_snapshot_ids,
        )
        limitations = [
            "因子健康需要点时横截面样本，当前不以候选截面替代",
            "ETF 映射等待可核验 ETF 目录与不少于60个共同交易日",
            "AI 因子假设需由用户或研究任务创建后再做确定性验证",
        ]
        if shadow_error:
            limitations.append(f"影子验证读取失败：{shadow_error}")
        module_statuses = {
            "factor_registry": ResearchModuleStatus(
                status="ready", message="七个现有价量因子已纳入生命周期治理",
            ),
            "factor_health": ResearchModuleStatus(
                status="insufficient", message="点时横截面样本正在积累，暂不输出 ICIR",
            ),
            "risk": ResearchModuleStatus(
                status="partial" if pitches else "insufficient",
                message="候选已完成证据、可交易性、财务、冲突与集中度分项检查",
            ),
            "opportunities": ResearchModuleStatus(
                status="partial" if pitches else "insufficient",
                message=("已生成证据绑定的机会卡" if pitches else "当前候选池没有可生成的机会卡"),
            ),
            "shadow": ResearchModuleStatus(
                status="error" if shadow_error else (
                    "partial" if cohorts else "insufficient"
                ),
                message=(
                    f"影子验证读取失败：{shadow_error}"
                    if shadow_error else "60日与分类样本按成熟度展示"
                ),
            ),
            "etf": ResearchModuleStatus(
                status="unavailable", message="缺少满足共同样本与流动性门槛的 ETF 映射",
            ),
            "hypotheses": ResearchModuleStatus(
                status="unavailable", message="当前没有待验证的 AI 因子假设",
            ),
        }
        snapshot = QuantResearchSnapshot(
            status="partial" if dashboard.status != "unavailable" else "insufficient",
            as_of=dashboard.as_of,
            observed_at=dashboard.observed_at,
            generated_at=now,
            snapshot_source="computed",
            refresh_state="ready",
            factor_registry=build_default_factor_registry(
                registered_at=now,
            ).snapshot(as_of=now),
            risk_summaries=tuple(item.risk_gate for item in pitches),
            opportunities=pitches,
            shadow_cohorts=tuple(cohorts.values()),
            module_statuses=module_statuses,
            source_snapshot_ids=dashboard.input_snapshot_ids,
            limitations=tuple(limitations),
        )
        self.snapshot_store.save(snapshot)
        return snapshot

    def _empty(self, now: datetime, reason: str) -> QuantResearchSnapshot:
        unavailable = ResearchModuleStatus(status="unavailable", message=reason)
        return QuantResearchSnapshot(
            status="error",
            as_of=now.date(),
            observed_at=now,
            generated_at=now,
            snapshot_source="empty",
            refresh_state="failed",
            factor_registry=build_default_factor_registry(
                registered_at=now,
            ).snapshot(as_of=now),
            module_statuses={
                key: unavailable for key in (
                    "factor_registry", "factor_health", "risk", "opportunities",
                    "shadow", "etf", "hypotheses",
                )
            },
            refresh_progress=100,
            refresh_stage="量化研究快照加载失败",
            limitations=(reason,),
        )


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
