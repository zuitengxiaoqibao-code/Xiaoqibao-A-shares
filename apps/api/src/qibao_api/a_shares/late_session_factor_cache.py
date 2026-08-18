from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Callable


@dataclass(frozen=True)
class LateSessionSlowFactor:
    volume_baseline_5d: Decimal | None
    twenty_day_limit_up_count: int | None


@dataclass(frozen=True)
class SlowFactorSnapshot:
    trading_date: date
    universe_hash: str
    built_at: datetime
    factors: dict[str, LateSessionSlowFactor]


class LateSessionFactorCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot: SlowFactorSnapshot | None = None
        self._builds = 0
        self._hits = 0

    def get_or_build(
        self,
        trading_date: date,
        symbols: tuple[str, ...],
        loader: Callable[[tuple[str, ...]], dict[str, list[object]]],
    ) -> SlowFactorSnapshot:
        normalized = tuple(sorted(set(symbols)))
        universe_hash = hashlib.sha256("|".join(normalized).encode("ascii")).hexdigest()
        with self._lock:
            if (
                self._snapshot is not None
                and self._snapshot.trading_date == trading_date
                and self._snapshot.universe_hash == universe_hash
            ):
                self._hits += 1
                return self._snapshot

            history = loader(normalized)
            snapshot = SlowFactorSnapshot(
                trading_date=trading_date,
                universe_hash=universe_hash,
                built_at=datetime.now(timezone.utc),
                factors={
                    symbol: _factor(symbol, history.get(symbol, ()), trading_date)
                    for symbol in normalized
                    if symbol in history
                },
            )
            self._snapshot = snapshot
            self._builds += 1
            return snapshot

    def status(self) -> dict[str, int | str | None]:
        with self._lock:
            return {
                "builds": self._builds,
                "hits": self._hits,
                "trading_date": self._snapshot.trading_date.isoformat() if self._snapshot else None,
                "factor_count": len(self._snapshot.factors) if self._snapshot else 0,
            }


def _factor(symbol: str, bars: list[object] | tuple[object, ...], as_of: date) -> LateSessionSlowFactor:
    eligible = [
        bar for bar in bars
        if getattr(bar, "trade_date", as_of) is None or getattr(bar, "trade_date", as_of) <= as_of
    ]
    volume_baseline = None
    if len(eligible) >= 6:
        baseline = sum((Decimal(str(bar.volume)) for bar in eligible[1:6]), Decimal("0")) / Decimal("5")
        if baseline > 0:
            volume_baseline = baseline

    limit_count = None
    if len(eligible) >= 21:
        limit_count = 0
        rate = Decimal("0.2") if symbol.startswith(("300", "301", "688", "689")) else Decimal("0.1")
        for index, bar in enumerate(eligible[:20]):
            previous_close = Decimal(str(eligible[index + 1].close))
            if previous_close <= 0:
                continue
            close = Decimal(str(bar.close))
            if close >= previous_close * (Decimal("1") + rate) * Decimal("0.995"):
                limit_count += 1
    return LateSessionSlowFactor(
        volume_baseline_5d=volume_baseline,
        twenty_day_limit_up_count=limit_count,
    )
