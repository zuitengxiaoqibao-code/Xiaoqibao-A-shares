import pytest
from pydantic import ValidationError

from qibao_api.contracts.strategy_plugin import StrategyPluginDefinition


def test_strategy_definition_rejects_unapproved_field() -> None:
    with pytest.raises(ValidationError, match="字段未在白名单"):
        StrategyPluginDefinition(
            id="demo",
            version="1",
            source="custom",
            fields=("os.system",),
        )


def test_strategy_definition_has_stable_defaults() -> None:
    definition = StrategyPluginDefinition(
        id="demo",
        version="1",
        source="custom",
        fields=("close", "ma20"),
    )
    assert definition.timeframe == "1d"
    assert definition.enabled is False
    assert len(definition.content_hash) == 64
