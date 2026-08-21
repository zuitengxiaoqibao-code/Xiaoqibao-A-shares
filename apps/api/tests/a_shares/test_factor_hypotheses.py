from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.a_shares.factor_hypotheses import (
    FactorHypothesisStore,
    validate_hypothesis_contract,
)
from qibao_api.contracts.quant_research import FactorHypothesisCreate


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def hypothesis(**updates) -> FactorHypothesisCreate:
    values = {
        "statement": "放量突破在轮动震荡期的20日样本外收益为正",
        "expected_direction": "positive",
        "required_fields": ("close", "volume", "market_regime"),
        "train_start": date(2023, 1, 1),
        "train_end": date(2024, 12, 31),
        "validation_start": date(2025, 1, 1),
        "validation_end": date(2025, 12, 31),
        "test_start": date(2026, 1, 1),
        "test_end": date(2026, 8, 20),
        "success_metric": "rank_ic_20",
        "success_threshold": "0.03",
        "invalidation_conditions": ("样本外 RankIC 小于等于 0",),
        "leakage_checks": ("point_in_time", "walk_forward", "transaction_cost", "fdr"),
        "model": "openai-compatible",
        "generated_at": NOW,
        "input_evidence_hash": HASH,
    }
    values.update(updates)
    return FactorHypothesisCreate(**values)


def test_ai_hypothesis_cannot_be_created_as_accepted() -> None:
    with pytest.raises(ValidationError, match="deterministic validation"):
        hypothesis(status="accepted")


def test_validation_is_insufficient_when_required_fields_are_missing() -> None:
    result = validate_hypothesis_contract(
        hypothesis(),
        available_fields={"close", "volume"},
        checks={
            "point_in_time": True,
            "walk_forward": True,
            "transaction_cost": True,
            "fdr": True,
        },
        validated_at=NOW,
    )

    assert result.status == "insufficient"
    assert result.missing_fields == ("market_regime",)


def test_validation_accepts_only_when_all_deterministic_checks_pass() -> None:
    result = validate_hypothesis_contract(
        hypothesis(),
        available_fields={"close", "volume", "market_regime"},
        checks={
            "point_in_time": True,
            "walk_forward": True,
            "transaction_cost": True,
            "fdr": True,
        },
        validated_at=NOW,
    )

    assert result.status == "accepted"
    assert result.checks == {
        "point_in_time": "passed",
        "walk_forward": "passed",
        "transaction_cost": "passed",
        "fdr": "passed",
    }


def test_hypothesis_store_is_append_only_and_returns_validation_status(tmp_path) -> None:
    store = FactorHypothesisStore(tmp_path / "hypotheses.sqlite3")
    record = store.append(hypothesis())
    validation = validate_hypothesis_contract(
        hypothesis(),
        available_fields={"close", "volume", "market_regime"},
        checks={key: False for key in ("point_in_time", "walk_forward", "transaction_cost", "fdr")},
        validated_at=NOW,
    )

    store.append_validation(record.hypothesis_id, validation)

    loaded = store.get(record.hypothesis_id)
    assert loaded.status == "rejected"
    assert len(store.validations(record.hypothesis_id)) == 1
