from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


StrategySource = Literal["builtin", "custom", "ai", "composite"]

ALLOWED_STRATEGY_FIELDS = frozenset(
    {
        "open", "high", "low", "close", "volume", "amount", "prev_close",
        "change_pct", "turnover", "market_cap", "ma5", "ma10", "ma20", "ma60",
        "rsi", "macd", "limit_up", "limit_down", "board",
    }
)


class StrategyPluginDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    version: str = Field(min_length=1)
    source: StrategySource
    name: str = ""
    description: str = ""
    fields: tuple[str, ...] = ()
    timeframe: str = "1d"
    asset_types: tuple[str, ...] = ("stock",)
    parameters: dict[str, Any] = Field(default_factory=dict)
    entry: dict[str, Any] = Field(default_factory=dict)
    exit: dict[str, Any] = Field(default_factory=dict)
    risk_gates: tuple[str, ...] = ()
    children: tuple[dict[str, Any], ...] = ()
    enabled: bool = False
    content_hash: str = Field(default="", pattern=r"^[0-9a-f]{64}$|^$")

    @model_validator(mode="after")
    def validate_definition(self) -> "StrategyPluginDefinition":
        unknown = sorted(set(self.fields) - ALLOWED_STRATEGY_FIELDS)
        if unknown:
            raise ValueError(f"字段未在白名单: {', '.join(unknown)}")
        if len(self.children) > 8:
            raise ValueError("复合策略最多允许 8 个子策略")
        if self.content_hash:
            return self
        payload = self.model_dump(exclude={"content_hash", "enabled"}, mode="json")
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "content_hash", digest)
        return self
