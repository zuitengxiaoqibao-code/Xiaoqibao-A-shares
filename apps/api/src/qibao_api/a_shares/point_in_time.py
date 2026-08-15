from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, TypeVar


T = TypeVar("T")


def _observed_at(value: Any) -> datetime | None:
    if isinstance(value, Mapping):
        observed = value.get("observed_at")
    else:
        observed = getattr(value, "observed_at", None)
    if observed is not None and observed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return observed


def as_of(value: T | None, cutoff: datetime) -> T | None:
    """Return evidence only when its observation time is inside the cutoff."""
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must include a timezone")
    if value is None:
        return None
    observed = _observed_at(value)
    if observed is None or observed > cutoff:
        return None
    return value


def filter_as_of(values: Iterable[T], cutoff: datetime) -> tuple[T, ...]:
    """Filter an iterable to evidence that was observable at ``cutoff``."""
    return tuple(value for value in values if as_of(value, cutoff) is not None)
