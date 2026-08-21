from __future__ import annotations

from datetime import datetime

from qibao_api.contracts.quant_research import (
    FactorDefinition,
    FactorRegistrySnapshot,
    utc_now,
)


class FactorRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, FactorDefinition] = {}

    def register(self, definition: FactorDefinition) -> None:
        if definition.factor_id in self._definitions:
            raise ValueError(f"factor id already registered: {definition.factor_id}")
        self._definitions[definition.factor_id] = definition

    def get(self, factor_id: str) -> FactorDefinition:
        try:
            return self._definitions[factor_id]
        except KeyError as error:
            raise KeyError(f"unknown factor: {factor_id}") from error

    def snapshot(self, *, as_of: datetime) -> FactorRegistrySnapshot:
        definitions = tuple(
            self._definitions[factor_id] for factor_id in sorted(self._definitions)
        )
        return FactorRegistrySnapshot(
            status="ready" if definitions else "unavailable",
            as_of=as_of,
            factors=definitions,
            limitations=() if definitions else ("当前没有已注册因子",),
        )


def build_default_factor_registry(
    *, registered_at: datetime | None = None,
) -> FactorRegistry:
    observed_at = registered_at or utc_now()
    registry = FactorRegistry()
    definitions = (
        ("return_5d", "5日涨跌幅", "momentum", "positive", ("close",), 6),
        ("return_20d", "20日涨跌幅", "momentum", "positive", ("close",), 21),
        ("distance_ma20", "距20日均线", "trend", "positive", ("close",), 20),
        (
            "volume_ratio_5_20", "5日/20日量比", "volume_price", "positive",
            ("volume",), 20,
        ),
        (
            "volatility_20d", "20日波动率", "volatility", "negative",
            ("close",), 21,
        ),
        ("drawdown_60d", "60日回撤", "risk", "positive", ("close",), 60),
        (
            "liquidity_amount_20d", "20日平均成交额", "liquidity", "positive",
            ("amount",), 20,
        ),
    )
    for factor_id, name, family, direction, fields, history in definitions:
        registry.register(FactorDefinition(
            factor_id=factor_id,
            name=name,
            family=family,
            direction=direction,
            required_fields=fields,
            minimum_history=history,
            formula_version="a-share-factors-v1",
            owner="system",
            lifecycle="active",
            registered_at=observed_at,
        ))
    return registry
