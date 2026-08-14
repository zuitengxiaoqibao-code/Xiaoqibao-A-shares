from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.field_evidence import FieldEvidence


OBSERVED_AT = datetime(2026, 8, 12, 2, 30, tzinfo=timezone.utc)


def test_field_evidence_accepts_a_derived_live_metric_with_formula_and_coverage() -> None:
    evidence = FieldEvidence(
        field_path="sentiment.score",
        value="76.00",
        source="market-sentiment-cache",
        source_field="score",
        status="live",
        trade_date=date(2026, 8, 12),
        observed_at=OBSERVED_AT,
        coverage_percent="88.50",
        derived=True,
        formula="a-share-sentiment-v2",
        evidence_ids=("sentiment-2026-08-12",),
    )

    assert evidence.coverage_percent == 88.5
    assert evidence.derived is True


def test_field_evidence_rejects_observed_status_without_observation_time() -> None:
    with pytest.raises(ValidationError, match="observed field evidence requires observed_at"):
        FieldEvidence(
            field_path="breadth.rising_count",
            value=3000,
            source="tdx-local-rpc",
            source_field="rising_count",
            status="cached",
            trade_date=date(2026, 8, 12),
            observed_at=None,
        )


def test_field_evidence_rejects_derived_metric_without_formula() -> None:
    with pytest.raises(ValidationError, match="derived field evidence requires formula"):
        FieldEvidence(
            field_path="regime.emotion_score",
            value="63.20",
            source="tdx-local-rpc",
            source_field=None,
            status="live",
            trade_date=date(2026, 8, 12),
            observed_at=OBSERVED_AT,
            derived=True,
        )


def test_field_evidence_requires_explicit_reason_for_missing_or_conflicting_values() -> None:
    for status in ("missing", "conflict"):
        with pytest.raises(ValidationError, match="requires explicit limitations"):
            FieldEvidence(
                field_path="liquidity.relative_amount",
                value=None,
                source="unavailable",
                source_field="relative_amount",
                status=status,
                trade_date=None,
                observed_at=None,
            )


def test_conflicting_field_evidence_discloses_alternative_value_and_resolution() -> None:
    evidence = FieldEvidence(
        field_path="valuation.pe_ttm",
        value="12.50",
        source="tdx-local-rpc-detail",
        source_field="pe_ttm",
        status="conflict",
        trade_date=date(2026, 8, 12),
        observed_at=OBSERVED_AT,
        alternatives=(
            {
                "value": "12.90",
                "source": "tencent",
                "source_field": "pe_ttm",
                "observed_at": OBSERVED_AT,
            },
        ),
        difference="-0.40 (-3.10%)",
        selection_reason="local TDX detail is the designated valuation source",
        affects_conclusion=False,
        limitations=("valuation_sources_disagree",),
    )

    assert evidence.alternatives[0].value == Decimal("12.90")
    assert evidence.difference == "-0.40 (-3.10%)"
    assert evidence.selection_reason.startswith("local TDX")
    assert evidence.affects_conclusion is False


def test_conflicting_field_evidence_requires_resolution_details() -> None:
    with pytest.raises(ValidationError, match="conflicting field evidence requires alternatives"):
        FieldEvidence(
            field_path="valuation.pe_ttm",
            value="12.50",
            source="tdx-local-rpc-detail",
            source_field="pe_ttm",
            status="conflict",
            trade_date=date(2026, 8, 12),
            observed_at=OBSERVED_AT,
            limitations=("valuation_sources_disagree",),
        )
