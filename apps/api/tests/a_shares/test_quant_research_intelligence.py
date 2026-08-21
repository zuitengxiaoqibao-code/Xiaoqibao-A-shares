from datetime import datetime, timezone
from decimal import Decimal

from qibao_api.a_shares.quant_research_intelligence import build_pitch_cards
from qibao_api.contracts.quant_research import QuantRiskContext, ShadowCohortEvidence

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

