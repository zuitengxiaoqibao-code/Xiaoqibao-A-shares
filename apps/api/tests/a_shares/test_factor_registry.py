from datetime import datetime, timezone

import pytest

from qibao_api.a_shares.factor_registry import FactorRegistry, build_default_factor_registry
from qibao_api.contracts.quant_research import FactorDefinition


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def test_default_registry_contains_only_existing_computable_factor_fields() -> None:
    snapshot = build_default_factor_registry(registered_at=NOW).snapshot(as_of=NOW)

    assert {item.factor_id for item in snapshot.factors} == {
        "return_5d",
        "return_20d",
        "distance_ma20",
        "volume_ratio_5_20",
        "volatility_20d",
        "drawdown_60d",
        "liquidity_amount_20d",
    }
    assert all(item.lifecycle == "active" for item in snapshot.factors)
    assert snapshot.status == "ready"


def test_registry_rejects_duplicate_ids_instead_of_silently_overwriting() -> None:
    registry = FactorRegistry()
    item = FactorDefinition(
        factor_id="return_5d",
        name="5日涨跌幅",
        family="momentum",
        direction="positive",
        required_fields=("close",),
        minimum_history=6,
        formula_version="a-share-factors-v1",
        owner="system",
        lifecycle="active",
        registered_at=NOW,
    )
    registry.register(item)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(item)


def test_registry_snapshot_order_is_stable() -> None:
    registry = build_default_factor_registry(registered_at=NOW)

    first = registry.snapshot(as_of=NOW)
    second = registry.snapshot(as_of=NOW)

    assert first == second
    assert [item.factor_id for item in first.factors] == sorted(
        item.factor_id for item in first.factors
    )
