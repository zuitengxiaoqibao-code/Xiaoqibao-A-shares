from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal


@dataclass(frozen=True)
class FieldEvidence:
    value: Any
    source: str
    observed_at: datetime
    priority: int
    max_age_seconds: float


@dataclass(frozen=True)
class FieldResolution:
    field: str
    status: Literal["selected", "conflicted", "unavailable"]
    value: Any = None
    source: str | None = None
    evidence: tuple[FieldEvidence, ...] = ()
    rejected_sources: tuple[str, ...] = ()


class FieldArbitrator:
    def __init__(
        self,
        *,
        price_relative_tolerance: Decimal = Decimal("0.001"),
        market_cap_relative_tolerance: Decimal = Decimal("0.02"),
        turnover_absolute_tolerance: Decimal = Decimal("0.20"),
    ) -> None:
        self.price_relative_tolerance = price_relative_tolerance
        self.market_cap_relative_tolerance = market_cap_relative_tolerance
        self.turnover_absolute_tolerance = turnover_absolute_tolerance

    def select(
        self,
        field: str,
        evidence: tuple[FieldEvidence, ...],
        *,
        now: datetime,
    ) -> FieldResolution:
        fresh: list[FieldEvidence] = []
        rejected: list[str] = []
        for item in evidence:
            age = max(0.0, (now - item.observed_at).total_seconds())
            if age > item.max_age_seconds:
                rejected.append(f"{item.source}:stale")
            elif item.value is None:
                rejected.append(f"{item.source}:missing")
            else:
                fresh.append(item)
        if not fresh:
            return FieldResolution(field=field, status="unavailable", rejected_sources=tuple(rejected))
        ordered = tuple(sorted(fresh, key=lambda item: (item.priority, -item.observed_at.timestamp())))
        if len(ordered) > 1 and self._conflicts(field, ordered[0].value, ordered[1].value):
            return FieldResolution(
                field=field,
                status="conflicted",
                evidence=ordered,
                rejected_sources=tuple(rejected),
            )
        selected = ordered[0]
        rejected.extend(f"{item.source}:lower_priority" for item in ordered[1:])
        return FieldResolution(
            field=field,
            status="selected",
            value=selected.value,
            source=selected.source,
            evidence=ordered,
            rejected_sources=tuple(rejected),
        )

    def _conflicts(self, field: str, left: Any, right: Any) -> bool:
        try:
            left_value = Decimal(str(left))
            right_value = Decimal(str(right))
        except (InvalidOperation, ValueError):
            return left != right
        difference = abs(left_value - right_value)
        if field == "turnover_rate":
            return difference > self.turnover_absolute_tolerance
        tolerance = self.market_cap_relative_tolerance if field == "market_cap_yi" else self.price_relative_tolerance
        denominator = max(abs(left_value), abs(right_value), Decimal("0.000001"))
        return difference / denominator > tolerance

