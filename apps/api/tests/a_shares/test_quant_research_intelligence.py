from datetime import datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.quant_research_intelligence import (
    QuantResearchIntelligenceService,
    build_pitch_cards,
)
from qibao_api.a_shares.quant_research_snapshot import QuantResearchSnapshotStore
from qibao_api.contracts.quant_research import QuantRiskContext, ShadowCohortEvidence
from qibao_api.contracts.quant_shadow import QuantShadowAnalytics, StrategyDriftAssessment

from .test_quant_strategy import NOW, board, overview
from qibao_api.a_shares.quant_strategy import build_quant_strategy_dashboard


def dashboard():
    return build_quant_strategy_dashboard(
        overview(), board(), names={"600001": "样本股份"}, generated_at=NOW,
    )


def cohort(sample_count: int) -> ShadowCohortEvidence:
    return ShadowCohortEvidence(
        opportunity_type="trend_continuation",
        decision_source="opportunity_scan",
        horizon=20,
        status="ready" if sample_count >= 20 else "insufficient",
        sample_count=sample_count,
        hit_rate_percent=Decimal("64.25"),
        average_return_percent=Decimal("3.18"),
        generated_at=datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc),
    )


def test_pitch_never_turns_strategy_score_or_small_sample_into_probability() -> None:
    source = dashboard()

    result = build_pitch_cards(
        source.candidates,
        regime=source.regime.regime,
        risk_contexts={
            "600001": QuantRiskContext(average_amount_20d=Decimal("80000000")),
        },
        cohort_evidence={"trend_continuation": cohort(3)},
        source_snapshot_ids=source.input_snapshot_ids,
    )

    assert len(result) == 1
    assert result[0].opportunity_type == "trend_continuation"
    assert result[0].strategy_score == source.candidates[0].strategy_score
    assert result[0].calibrated_hit_rate_percent is None
    assert any("成熟样本不足" in item for item in result[0].limitations)


def test_pitch_uses_only_mature_same_type_shadow_evidence() -> None:
    source = dashboard()

    result = build_pitch_cards(
        source.candidates,
        regime=source.regime.regime,
        risk_contexts={"600001": QuantRiskContext()},
        cohort_evidence={"trend_continuation": cohort(25)},
        source_snapshot_ids=("snapshot-1",),
    )

    assert result[0].calibrated_hit_rate_percent == Decimal("64.25")
    assert result[0].shadow_sample_count == 25
    assert result[0].source_snapshot_ids == ("snapshot-1",)
    assert len(result[0].core_evidence) <= 3


def test_blocked_risk_gate_excludes_pitch_instead_of_hiding_the_blocker() -> None:
    source = dashboard()

    result = build_pitch_cards(
        source.candidates,
        regime=source.regime.regime,
        risk_contexts={"600001": QuantRiskContext(suspended=True)},
        cohort_evidence={},
    )

    assert result[0].status == "excluded"
    assert "股票处于停牌状态" in result[0].risk_gate.blockers


def test_service_builds_once_then_returns_fresh_last_good_snapshot(tmp_path) -> None:
    source = dashboard()

    class Strategy:
        def __init__(self) -> None:
            self.calls = 0

        def current(self, now, *, limit=12):
            self.calls += 1
            assert limit == 12
            return source

    class Ledger:
        def analytics(self, *, horizon, decision_source, opportunity_type):
            assert horizon == 20
            return QuantShadowAnalytics(
                status="insufficient",
                horizon=20,
                decision_source=decision_source,
                opportunity_type=opportunity_type,
                mature_sample_count=0,
                pending_sample_count=0,
                drift=StrategyDriftAssessment(
                    status="insufficient", recent_sample_count=0, baseline_sample_count=0,
                ),
                generated_at=NOW,
                limitations=("成熟样本不足",),
            )

    strategy = Strategy()
    store = QuantResearchSnapshotStore(tmp_path / "quant-research.json")
    service = QuantResearchIntelligenceService(strategy, Ledger(), store)

    computed = service.current(NOW)
    cached = service.current(NOW + timedelta(seconds=30))

    assert computed.snapshot_source == "computed"
    assert computed.opportunities[0].symbol == "600001"
    assert computed.module_statuses["factor_health"].status == "insufficient"
    assert cached.snapshot_source == "cache"
    assert strategy.calls == 1


def test_service_isolates_shadow_failure_and_keeps_pitch_visible(tmp_path) -> None:
    class Strategy:
        def current(self, now, *, limit=12):
            return dashboard()

    class FailingLedger:
        def analytics(self, **kwargs):
            raise OSError("ledger locked")

    service = QuantResearchIntelligenceService(
        Strategy(),
        FailingLedger(),
        QuantResearchSnapshotStore(tmp_path / "quant-research.json"),
    )

    result = service.current(NOW)

    assert result.status == "partial"
    assert result.opportunities
    assert result.module_statuses["shadow"].status == "error"
    assert "影子验证读取失败" in result.module_statuses["shadow"].message
