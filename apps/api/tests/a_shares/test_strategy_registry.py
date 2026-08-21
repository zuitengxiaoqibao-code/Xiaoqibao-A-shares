from qibao_api.a_shares.strategy_registry import StrategyRegistry
from qibao_api.contracts.strategy_plugin import StrategyPluginDefinition


def test_registry_keeps_versions_and_only_enables_approved_definition(tmp_path):
    registry = StrategyRegistry(tmp_path)
    definition = StrategyPluginDefinition(id="demo", version="1", source="custom", fields=("close",))
    registry.register(definition)
    assert registry.enable("demo", "1").enabled is True
    assert registry.latest("demo").version == "1"
    assert registry.disable("demo").enabled is False
