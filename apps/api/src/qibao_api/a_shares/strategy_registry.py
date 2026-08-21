from __future__ import annotations

import json
from pathlib import Path

from qibao_api.contracts.strategy_plugin import StrategyPluginDefinition


class StrategyRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, strategy_id: str, version: str) -> Path:
        return self.root / strategy_id / f"{version}.json"

    def register(self, definition: StrategyPluginDefinition) -> StrategyPluginDefinition:
        target = self._path(definition.id, definition.version)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(definition.model_dump_json(), encoding="utf-8")
        return definition

    def latest(self, strategy_id: str) -> StrategyPluginDefinition:
        files = sorted((self.root / strategy_id).glob("*.json"), reverse=True)
        if not files:
            raise KeyError(f"策略不存在: {strategy_id}")
        return StrategyPluginDefinition.model_validate(json.loads(files[0].read_text(encoding="utf-8")))

    def enable(self, strategy_id: str, version: str) -> StrategyPluginDefinition:
        path = self._path(strategy_id, version)
        if not path.exists():
            raise KeyError(f"策略版本不存在: {strategy_id}@{version}")
        definition = StrategyPluginDefinition.model_validate(json.loads(path.read_text(encoding="utf-8"))).model_copy(update={"enabled": True})
        path.write_text(definition.model_dump_json(), encoding="utf-8")
        return definition

    def disable(self, strategy_id: str) -> StrategyPluginDefinition:
        definition = self.latest(strategy_id).model_copy(update={"enabled": False})
        self._path(strategy_id, definition.version).write_text(definition.model_dump_json(), encoding="utf-8")
        return definition
