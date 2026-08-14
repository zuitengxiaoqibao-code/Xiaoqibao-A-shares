from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone

from qibao_api.contracts.history_quality import HistoryQualityGap, HistoryQualityReport


def inspect_history_quality(
    trading_dates: Iterable[date],
    symbols: Iterable[str],
    bars: Mapping[str, Iterable[date]],
    *,
    observed_at: datetime | None = None,
    source: str = "local-market-bars",
) -> HistoryQualityReport:
    sessions = tuple(sorted(set(trading_dates)))
    universe = tuple(sorted(set(symbols)))
    expected = set(sessions)
    gaps: list[HistoryQualityGap] = []
    covered_sessions: set[date] = set()
    for symbol in universe:
        values = tuple(bars.get(symbol, ()))
        counts: dict[date, int] = {}
        for item in values:
            counts[item] = counts.get(item, 0) + 1
            if item in expected:
                covered_sessions.add(item)
        missing = tuple(sorted(expected.difference(counts)))
        duplicates = tuple(sorted(item for item, count in counts.items() if count > 1 and item in expected))
        future = tuple(sorted(item for item in counts if sessions and item > sessions[-1]))
        if missing or duplicates or future:
            gaps.append(HistoryQualityGap(
                symbol=symbol,
                missing_dates=missing,
                duplicate_dates=duplicates,
                future_dates=future,
            ))
    ratio = len(covered_sessions) / len(expected) if expected else None
    status = "unavailable" if not universe or not expected else "ready" if not gaps and ratio == 1 else "partial"
    stamp = observed_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return HistoryQualityReport(
        observed_at=stamp,
        expected_sessions=len(expected),
        covered_sessions=len(covered_sessions),
        coverage_ratio=ratio,
        symbol_count=len(universe),
        gap_count=len(gaps),
        gaps=tuple(gaps),
        status=status,
        source=source,
    )

