from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GateResult:
    status: str
    reasons: tuple[str, ...]
    evidence: tuple[str, ...]
    probability: float | None


class StrategyDraftGate:
    minimum_samples = 30

    @classmethod
    def review(cls, draft: dict[str, Any], data_version: str) -> GateResult:
        reasons: list[str] = []
        evidence = [f"数据版本：{data_version}"]
        if int(draft.get("sample_count", 0)) < cls.minimum_samples:
            reasons.append("样本交易不足")
        if not draft.get("fields"):
            reasons.append("缺少策略字段")
        status = "rejected" if reasons else "accepted"
        return GateResult(status, tuple(reasons), tuple(evidence), None if reasons else None)
