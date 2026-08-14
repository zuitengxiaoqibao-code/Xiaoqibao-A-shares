"""Small in-process cache for deterministic daily factor calculations."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable, Sequence
from datetime import date
from threading import RLock
from typing import TypeVar


T = TypeVar("T")


def daily_history_fingerprint(history: Sequence[object]) -> str:
    rows = []
    for bar in history:
        if hasattr(bar, "model_dump"):
            rows.append(bar.model_dump(mode="json"))
        else:
            rows.append(repr(bar))
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class QuantFactorCache:
    def __init__(self, max_entries: int = 20_000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._values: OrderedDict[tuple[date, str, str, str], T] = OrderedDict()
        self._lock = RLock()

    def get_or_compute(
        self,
        *,
        trading_date: date,
        symbol: str,
        factor_version: str,
        history_fingerprint: str,
        loader: Callable[[], T],
    ) -> T:
        key = (trading_date, symbol, factor_version, history_fingerprint)
        with self._lock:
            value = self._values.get(key)
            if value is not None:
                self._values.move_to_end(key)
                return value
        value = loader()
        with self._lock:
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)
        return value
