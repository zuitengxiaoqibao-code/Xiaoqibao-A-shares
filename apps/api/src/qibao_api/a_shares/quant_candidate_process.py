"""Process-isolated candidate scan for the portable desktop runtime.

The local DuckDB query materializes hundreds of thousands of bars and the
factor pass is CPU-heavy Python work. Running that work in a child process
keeps the FastAPI/Uvicorn process responsive while preserving the same local
data and scoring rules.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from qibao_api.a_shares.candidates import MINIMUM_AVERAGE_AMOUNT, build_candidate_board
from qibao_api.a_shares.factors import InsufficientHistoryError, build_factor_snapshot
from qibao_api.a_shares.models import (
    CandidateBoard,
    CandidateExclusion,
    CandidateFunnel,
    FACTOR_VERSION,
)
from qibao_api.storage.bar_repository import BarRepository


def scan_candidate_board_from_local_bars(
    database_path: str,
    parquet_dir: str,
    factor_as_of: date,
    limit: int,
) -> CandidateBoard:
    """Build a candidate board from the portable local market database.

    This function is intentionally module-level so ``ProcessPoolExecutor``
    can import it in a Windows child process. No network or broker calls are
    made, and the caller validates the returned Pydantic board before use.
    """
    repository = BarRepository(Path(database_path), Path(parquet_dir))
    requested_factor_as_of = factor_as_of
    effective_factor_as_of = repository.latest_common_trade_date(
        requested_factor_as_of, minimum_bars=60, minimum_coverage=0.8
    ) or repository.dominant_trade_date(
        requested_factor_as_of, minimum_bars=60
    ) or repository.latest_trade_date(requested_factor_as_of)
    if effective_factor_as_of is None:
        return CandidateBoard(
            as_of=requested_factor_as_of,
            universe_size=0,
            eligible_size=0,
            funnel=CandidateFunnel(
                completeness="unavailable",
                blockers=("no_daily_history_before_requested_date",),
            ),
            latest_trade_date=None,
            sources=(),
            short_term=[],
            swing=[],
        )
    factor_as_of = effective_factor_as_of
    symbols = repository.symbols_up_to(factor_as_of)
    histories = repository.latest_many(symbols, 60, factor_as_of)
    snapshots = []
    exclusions: list[CandidateExclusion] = []
    history_ready_size = 0
    for symbol in symbols:
        history = histories.get(symbol, [])
        if len(history) < 60:
            exclusions.append(CandidateExclusion(
                symbol=symbol,
                reason_code="insufficient_history",
                observed_value=len(history),
                threshold=60,
                detail="history requires at least 60 distinct daily bars",
            ))
            continue
        history_ready_size += 1
        try:
            snapshot = build_factor_snapshot(history, factor_as_of)
        except (InsufficientHistoryError, ValueError) as error:
            exclusions.append(CandidateExclusion(
                symbol=symbol,
                reason_code="invalid_history",
                detail=str(error),
            ))
            continue
        if snapshot.latest_trade_date != factor_as_of:
            exclusions.append(CandidateExclusion(
                symbol=symbol,
                reason_code="stale_history",
                detail="history does not reach the confirmed factor date",
            ))
            continue
        snapshots.append(snapshot)

    factor_ready_size = len(snapshots)
    if not snapshots:
        reason_counts: dict[str, int] = {}
        for item in exclusions:
            reason_counts[item.reason_code] = reason_counts.get(item.reason_code, 0) + 1
        return CandidateBoard(
            as_of=factor_as_of,
            universe_size=len(symbols),
            eligible_size=0,
            funnel=CandidateFunnel(
                history_ready_size=history_ready_size,
                factor_ready_size=0,
                liquidity_ready_size=0,
                ranked_size=0,
                exclusion_reasons=reason_counts,
                completeness="unavailable",
                blockers=("no_factor_ready_history",),
            ),
            latest_trade_date=None,
            sources=(),
            short_term=[],
            swing=[],
            exclusions=exclusions,
        )

    board = build_candidate_board(snapshots, limit)
    eligible_size = sum(
        item.liquidity_amount_20d >= MINIMUM_AVERAGE_AMOUNT
        for item in snapshots
    )
    latest_trade_date = max(
        (item.latest_trade_date for item in snapshots if item.latest_trade_date),
        default=None,
    )
    combined_exclusions = sorted(
        [*exclusions, *board.exclusions], key=lambda item: item.symbol
    )
    reason_counts: dict[str, int] = {}
    for item in combined_exclusions:
        reason_counts[item.reason_code] = reason_counts.get(item.reason_code, 0) + 1
    completeness = (
        "partial"
        if effective_factor_as_of < requested_factor_as_of
        else "complete" if history_ready_size == len(symbols) else "partial"
    )
    blockers = []
    if effective_factor_as_of < requested_factor_as_of:
        blockers.append("stale_daily_history")
    if completeness != "complete":
        blockers.append("incomplete_daily_history")
    return board.model_copy(update={
        "universe_size": len(symbols),
        "eligible_size": eligible_size,
        "funnel": CandidateFunnel(
            history_ready_size=history_ready_size,
            factor_ready_size=factor_ready_size,
            liquidity_ready_size=eligible_size,
            ranked_size=eligible_size,
            exclusion_reasons=reason_counts,
            completeness=completeness,
            blockers=tuple(blockers),
        ),
        "latest_trade_date": latest_trade_date,
        "sources": tuple(sorted({item.source for item in snapshots})),
        "exclusions": combined_exclusions,
        "factor_version": FACTOR_VERSION,
    })
