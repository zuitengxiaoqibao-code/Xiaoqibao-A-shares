from datetime import date, timedelta
from decimal import Decimal

from qibao_api.a_shares.quant_candidate_process import (
    scan_candidate_board_from_local_bars,
)
from qibao_api.contracts.bars import DailyBar
from qibao_api.storage.bar_repository import BarRepository


def test_process_candidate_scan_uses_the_same_local_daily_bar_contract(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    bars = []
    for symbol, offset in (("600001", Decimal("0")), ("600002", Decimal("1"))):
        for index in range(60):
            close = Decimal("10") + offset + Decimal(index) / Decimal("100")
            bars.append(DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=index),
                open=close,
                high=close + Decimal("0.1"),
                low=close - Decimal("0.1"),
                close=close,
                volume=1_000_000,
                amount=Decimal("20_000_000"),
                source="test-daily-bars",
            ))
    repository.upsert(bars)

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), start + timedelta(days=59), 12
    )

    assert board.as_of == start + timedelta(days=59)
    assert board.universe_size == 2
    assert board.eligible_size == 2
    assert {entry.symbol for entry in board.short_term} == {"600001", "600002"}
    assert board.sources == ("test-daily-bars",)


def test_process_candidate_scan_records_monotonic_funnel_and_exclusion_totals(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    bars = []
    for symbol in ("600001", "600002", "600003"):
        count = 60 if symbol != "600003" else 12
        for index in range(count):
            close = Decimal("10") + Decimal(index) / Decimal("100")
            bars.append(DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=index),
                open=close,
                high=close + Decimal("0.1"),
                low=close - Decimal("0.1"),
                close=close,
                volume=1_000_000,
                amount=Decimal("20_000_000"),
                source="test-daily-bars",
            ))
    repository.upsert(bars)

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), start + timedelta(days=59), 12
    )

    assert board.funnel.history_ready_size == 2
    assert board.funnel.factor_ready_size == 2
    assert board.funnel.liquidity_ready_size == 2
    assert board.funnel.exclusion_reasons["insufficient_history"] == 1
    counts = board.funnel.stage_counts()
    assert counts == sorted(counts, reverse=True)


def test_process_candidate_scan_marks_unavailable_when_no_confirmed_history(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    repository.upsert([
        DailyBar(
            symbol="600001",
            trade_date=start,
            open=Decimal("10"),
            high=Decimal("10.1"),
            low=Decimal("9.9"),
            close=Decimal("10"),
            volume=1_000_000,
            amount=Decimal("20_000_000"),
            source="test-daily-bars",
        )
    ])

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), start, 12
    )

    assert board.funnel.completeness == "unavailable"
    assert board.funnel.blockers
    assert board.short_term == []


def test_process_candidate_scan_uses_last_real_trade_date_when_request_is_later(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    latest = start + timedelta(days=59)
    bars = []
    for index in range(60):
        close = Decimal("10") + Decimal(index) / Decimal("100")
        bars.append(DailyBar(
            symbol="600001",
            trade_date=start + timedelta(days=index),
            open=close,
            high=close + Decimal("0.1"),
            low=close - Decimal("0.1"),
            close=close,
            volume=1_000_000,
            amount=Decimal("20_000_000"),
            source="test-daily-bars",
        ))
    repository.upsert(bars)

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), latest + timedelta(days=5), 12
    )

    assert board.as_of == latest
    assert board.latest_trade_date == latest
    assert board.short_term
    assert board.funnel.completeness == "partial"
    assert "stale_daily_history" in board.funnel.blockers


def test_process_candidate_scan_uses_latest_common_date_not_sparse_new_record(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    latest = start + timedelta(days=59)
    bars = []
    for symbol in ("600001", "600002"):
        for index in range(60):
            close = Decimal("10") + Decimal(index) / Decimal("100")
            bars.append(DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=index),
                open=close,
                high=close + Decimal("0.1"),
                low=close - Decimal("0.1"),
                close=close,
                volume=1_000_000,
                amount=Decimal("20_000_000"),
                source="test-daily-bars",
            ))
    bars.append(DailyBar(
        symbol="600003",
        trade_date=latest + timedelta(days=1),
        open=Decimal("10"), high=Decimal("10.1"), low=Decimal("9.9"),
        close=Decimal("10"), volume=1_000_000, amount=Decimal("20_000_000"),
        source="test-daily-bars",
    ))
    repository.upsert(bars)

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), latest + timedelta(days=1), 12
    )

    assert board.as_of == latest
    assert {entry.symbol for entry in board.short_term} == {"600001", "600002"}
    assert board.funnel.completeness == "partial"
    assert "stale_daily_history" in board.funnel.blockers


def test_process_candidate_scan_counts_all_ranked_candidates_before_display_limit(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    parquet = tmp_path / "parquet"
    repository = BarRepository(database, parquet)
    start = date(2026, 5, 1)
    bars = []
    for symbol_index in range(1, 14):
        symbol = f"600{symbol_index:03d}"
        for index in range(60):
            close = Decimal("10") + Decimal(symbol_index + index) / Decimal("100")
            bars.append(DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=index),
                open=close,
                high=close + Decimal("0.1"),
                low=close - Decimal("0.1"),
                close=close,
                volume=1_000_000,
                amount=Decimal("20_000_000"),
                source="test-daily-bars",
            ))
    repository.upsert(bars)

    board = scan_candidate_board_from_local_bars(
        str(database), str(parquet), start + timedelta(days=59), 12
    )

    assert board.eligible_size == 13
    assert board.funnel.ranked_size == 13
    assert len(board.short_term) == 12
    assert len(board.swing) == 12
    assert board.funnel.exclusion_reasons == {}
    assert board.exclusions == []
