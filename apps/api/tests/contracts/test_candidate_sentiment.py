from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.candidate_sentiment import (
    CandidateSentimentBatch,
    CandidateSentimentComponent,
    CandidateSentimentSnapshot,
)


CUTOFF = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)


def component(
    name: str = "news",
    *,
    status: str = "ready",
    score: Decimal | None = Decimal("75"),
    weight: Decimal = Decimal("40"),
) -> CandidateSentimentComponent:
    return CandidateSentimentComponent(
        name=name,
        status=status,
        score=score,
        weight=weight,
        summary="已核验分项",
        observed_at=CUTOFF,
        evidence_ids=("evidence-1",),
    )


def snapshot(**overrides) -> CandidateSentimentSnapshot:
    values = {
        "candidate_snapshot_id": "a-share-candidates-1",
        "candidate_input_hash": "a" * 64,
        "symbol": "600000",
        "quality": "ready",
        "freshness": "current",
        "score": Decimal("65"),
        "band": "positive",
        "coverage_percent": Decimal("100"),
        "components": (
            component(),
            component("hotspot", score=Decimal("65"), weight=Decimal("30")),
            component("fund_flow", score=Decimal("55"), weight=Decimal("30")),
        ),
        "primary_reason": "新闻倾向偏积极。",
        "primary_risk": "高分不代表低风险。",
        "beginner_guidance": "先观察证据是否持续。",
        "observed_at": CUTOFF,
        "generated_at": CUTOFF,
        "source_snapshot_ids": ("evidence-1",),
    }
    values.update(overrides)
    return CandidateSentimentSnapshot(**values)


def test_component_requires_unavailable_status_and_missing_score_to_agree() -> None:
    with pytest.raises(ValidationError):
        component(status="unavailable", score=Decimal("50"))
    with pytest.raises(ValidationError):
        component(status="ready", score=None)


def test_snapshot_requires_score_band_quality_and_coverage_to_agree() -> None:
    with pytest.raises(ValidationError):
        snapshot(score=None, band="neutral", quality="unavailable", coverage_percent=Decimal("40"))
    with pytest.raises(ValidationError):
        snapshot(quality="ready", coverage_percent=Decimal("70"))
    with pytest.raises(ValidationError):
        snapshot(quality="partial", score=None, band="unavailable", coverage_percent=Decimal("60"))


def test_snapshot_rejects_future_observation_and_duplicate_components() -> None:
    with pytest.raises(ValidationError):
        snapshot(observed_at=CUTOFF.replace(hour=7))
    with pytest.raises(ValidationError):
        snapshot(components=(component(), component(), component()))


def test_batch_rejects_duplicate_symbols_and_more_than_twenty_items() -> None:
    with pytest.raises(ValidationError):
        CandidateSentimentBatch(
            candidate_snapshot_id="a-share-candidates-1",
            candidate_input_hash="a" * 64,
            as_of=date(2026, 7, 18),
            cutoff=CUTOFF,
            quality="ready",
            items=(snapshot(), snapshot()),
            generated_at=CUTOFF,
        )
    items = tuple(snapshot(symbol=f"600{index:03d}") for index in range(21))
    with pytest.raises(ValidationError):
        CandidateSentimentBatch(
            candidate_snapshot_id="a-share-candidates-1",
            candidate_input_hash="a" * 64,
            as_of=date(2026, 7, 18),
            cutoff=CUTOFF,
            quality="ready",
            items=items,
            generated_at=CUTOFF,
        )
