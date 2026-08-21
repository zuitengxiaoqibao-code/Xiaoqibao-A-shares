from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.contracts.quant_research import FactorDefinition, FactorRegistrySnapshot


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def definition(**updates) -> FactorDefinition:
    values = {
        "factor_id": "return_5d",
        "name": "5日涨跌幅",
        "family": "momentum",
        "direction": "positive",
        "required_fields": ("close",),
        "minimum_history": 6,
        "formula_version": "a-share-factors-v1",
        "owner": "system",
        "lifecycle": "active",
        "registered_at": NOW,
    }
    values.update(updates)
    return FactorDefinition(**values)


def test_factor_definition_is_frozen_and_requires_a_stable_ascii_id() -> None:
    item = definition()

    with pytest.raises(ValidationError):
        item.name = "已修改"
    with pytest.raises(ValidationError, match="factor_id"):
        definition(factor_id="五日涨跌")


def test_retired_factor_requires_time_and_reason() -> None:
    with pytest.raises(ValidationError, match="retired"):
        definition(lifecycle="retired")


def test_registry_snapshot_rejects_duplicate_factor_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        FactorRegistrySnapshot(
            status="ready",
            as_of=NOW,
            factors=(definition(), definition(name="另一个名称")),
            formula_version="quant-factor-registry-v1",
        )

