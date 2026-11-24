from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import duckdb
import pytest

from qibao_api.contracts.bars import DailyBar
from qibao_api.storage.bar_repository import BarRepository


def make_bar(close: str = "9.50") -> DailyBar:
    return DailyBar(
        symbol="600000",
        trade_date=date(2026, 7, 13),
        open=Decimal("9.10"),
        high=Decimal("9.80"),
        low=Decimal("9.00"),
        close=Decimal(close),
        volume=1000,
        amount=Decimal("9500"),
        source="mootdx",
    )


def test_upsert_replaces_same_symbol_and_date(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([make_bar()])

    repository.upsert([make_bar("9.60")])

    bars = repository.latest("600000", 10)
    assert len(bars) == 1
    assert bars[0].close == Decimal("9.60")


def test_export_parquet_contains_symbol_rows(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([make_bar()])

    path = repository.export_parquet("600000")

    assert path.exists()
    with duckdb.connect() as connection:
        count = connection.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
    assert count == 1


def test_export_parquet_contains_only_latest_same_day_revision(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([make_bar("9.50")])
    repository.upsert([make_bar("9.80")])

    path = repository.export_parquet("600000")

    with duckdb.connect() as connection:
        rows = connection.execute(
            "SELECT trade_date, close FROM read_parquet(?)", [str(path)]
        ).fetchall()
    assert rows == [(date(2026, 7, 13), Decimal("9.8000"))]


def test_trade_dates_are_distinct_and_descending(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([make_bar()])

    assert repository.trade_dates(limit=10) == [date(2026, 7, 13)]


def test_read_only_repository_can_read_an_existing_database_without_schema_writes(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    writable = BarRepository(database, tmp_path / "parquet")
    writable.upsert([make_bar()])

    readonly = BarRepository(database, tmp_path / "parquet", read_only=True)

    assert readonly.trade_dates(limit=10) == [date(2026, 7, 13)]


def test_schema_check_disabled_repository_can_share_database_with_an_open_writer(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    writable = BarRepository(database, tmp_path / "parquet")
    writable.upsert([make_bar()])
    writer = duckdb.connect(str(database))
    try:
        reader = BarRepository(database, tmp_path / "parquet", ensure_schema=False)
        assert reader.trade_dates(limit=10) == [date(2026, 7, 13)]
    finally:
        writer.close()


def test_dominant_trade_date_ignores_sparse_symbols_with_insufficient_history(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    latest = date(2026, 7, 13)
    repository.upsert(
        make_history("600000", 60, start=latest - timedelta(days=59))
        + make_history("000001", 60, start=latest - timedelta(days=59))
        + [make_bar().model_copy(update={"symbol": "600002", "trade_date": latest + timedelta(days=1)})]
    )

    assert repository.dominant_trade_date(latest + timedelta(days=1), minimum_bars=60) == latest
    assert repository.latest_common_trade_date(
        latest + timedelta(days=1), minimum_bars=60, minimum_coverage=0.8
    ) == latest


def make_history(symbol: str, count: int, start: date = date(2026, 1, 1)) -> list[DailyBar]:
    bars = []
    for index in range(count):
        close = Decimal("10") + Decimal(index) / Decimal("100")
        bars.append(DailyBar(
            symbol=symbol, trade_date=start + timedelta(days=index), open=close,
            high=close + Decimal("0.1"), low=close - Decimal("0.1"), close=close,
            volume=100_000, amount=close * Decimal("100000"), source="fixture",
        ))
    return bars


def test_repository_returns_only_symbols_with_enough_history(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert(make_history("600000", 80) + make_history("000001", 40))
    as_of = date(2026, 3, 31)

    assert repository.symbols_with_history(60, as_of) == ["600000"]


def test_latest_many_respects_as_of_and_returns_chronological_bars(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    bars = make_history("600000", 80)
    repository.upsert(bars)
    as_of = bars[-2].trade_date

    result = repository.latest_many(["600000"], limit=60, as_of=as_of)

    assert list(result) == ["600000"]
    assert len(result["600000"]) == 60
    assert result["600000"][0].trade_date < result["600000"][-1].trade_date
    assert result["600000"][-1].trade_date == as_of


def test_append_missing_ignores_existing_and_duplicate_symbol_dates(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    first, second = make_history("600000", 2)
    repository.upsert([first])

    inserted = repository.append_missing([first, second, second])

    assert inserted == 1
    assert [bar.trade_date for bar in repository.latest("600000", 10)] == [
        second.trade_date,
        first.trade_date,
    ]
    with duckdb.connect(str(repository.database_path)) as connection:
        assert connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0] == 2


def test_coverage_includes_missing_symbols_and_respects_target_date(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    history = make_history("600000", 3)
    repository.upsert(history)

    coverage = repository.coverage(
        ["600000", "000001"], target_date=history[-2].trade_date
    )

    assert coverage["600000"].bar_count == 2
    assert coverage["600000"].latest_trade_date == history[-2].trade_date
    assert coverage["000001"].bar_count == 0
    assert coverage["000001"].latest_trade_date is None


def test_latest_many_keeps_full_window_after_same_day_revisions(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    bars = make_history("600000", 80)
    repository.upsert(bars)

    revised = [
        DailyBar(
            symbol=bar.symbol,
            trade_date=bar.trade_date,
            open=bar.open,
            high=bar.high + Decimal("0.05"),
            low=bar.low,
            close=bar.close + Decimal("0.05"),
            volume=bar.volume + 1,
            amount=bar.amount + Decimal("5"),
            source="revision",
        )
        for bar in bars[::2]
    ]
    repository.upsert(revised)
    as_of = bars[-1].trade_date

    result = repository.latest_many(["600000"], limit=60, as_of=as_of)
    returned = result["600000"]

    assert len(returned) == 60
    assert len({bar.trade_date for bar in returned}) == 60
    assert returned[0].trade_date < returned[-1].trade_date
    assert returned[-1].trade_date == as_of
    assert returned[-2].source == "revision"


def test_latest_many_rejects_non_a_share_symbols(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")

    with pytest.raises(ValueError, match="A-share"):
        repository.latest_many(["113001"], limit=60, as_of=date(2026, 7, 14))


def test_cutoff_excludes_bars_ingested_after_decision_window(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert(make_history("600000", 60))
    cutoff = datetime(2026, 7, 15, 9, 25, tzinfo=UTC)
    with duckdb.connect(str(repository.database_path)) as connection:
        connection.execute(
            "UPDATE daily_bars SET ingested_at = ?",
            [datetime(2026, 7, 15, 9, 26)],
        )

    assert repository.symbols_with_history(60, date(2026, 7, 15), cutoff=cutoff) == []
    assert repository.latest_many(
        ["600000"], 60, date(2026, 7, 15), cutoff=cutoff,
    ) == {"600000": []}


def test_revised_bar_is_append_only_and_replayed_by_cutoff(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([make_bar("9.50")])
    with duckdb.connect(str(repository.database_path)) as connection:
        connection.execute("UPDATE daily_bars SET ingested_at = ?", [datetime(2026, 7, 14, 8)])
    repository.upsert([make_bar("9.80")])
    with duckdb.connect(str(repository.database_path)) as connection:
        connection.execute(
            "UPDATE daily_bars SET ingested_at = ? WHERE close = 9.80",
            [datetime(2026, 7, 15, 8)],
        )
        assert connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0] == 2

    old = repository.latest_many(
        ["600000"], 10, date(2026, 7, 15), cutoff=datetime(2026, 7, 14, 9, tzinfo=UTC)
    )
    new = repository.latest_many(
        ["600000"], 10, date(2026, 7, 15), cutoff=datetime(2026, 7, 15, 9, tzinfo=UTC)
    )

    assert old["600000"][0].close == Decimal("9.50")
    assert new["600000"][0].close == Decimal("9.80")


def test_existing_primary_key_schema_migrates_without_losing_rows(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("""CREATE TABLE daily_bars (
            symbol VARCHAR, trade_date DATE, open DECIMAL(18,4), high DECIMAL(18,4),
            low DECIMAL(18,4), close DECIMAL(18,4), volume BIGINT,
            amount DECIMAL(24,4), source VARCHAR, ingested_at TIMESTAMP,
            PRIMARY KEY(symbol, trade_date))""")
        connection.execute(
            "INSERT INTO daily_bars VALUES (?, ?, 9, 10, 8, 9.5, 1000, 9500, 'legacy', ?)",
            ["600000", date(2026, 7, 13), datetime(2026, 7, 14, 8)],
        )

    repository = BarRepository(database, tmp_path / "parquet")
    repository.upsert([make_bar("9.80")])

    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0] == 2
    assert repository.latest("600000")[0].close == Decimal("9.80")


def test_failed_migration_preserves_old_schema_and_can_retry(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("""CREATE TABLE daily_bars (
            symbol VARCHAR, trade_date DATE, open DECIMAL(18,4), high DECIMAL(18,4),
            low DECIMAL(18,4), close DECIMAL(18,4), volume BIGINT,
            amount DECIMAL(24,4), source VARCHAR, ingested_at TIMESTAMP,
            PRIMARY KEY(symbol, trade_date))""")
        connection.execute("""INSERT INTO daily_bars VALUES
            ('600000', '2026-07-13', 9, 10, 8, 9.5, 1000, 9500, NULL, current_timestamp)""")
    repository = BarRepository(database, tmp_path / "parquet")
    with pytest.raises(duckdb.ConstraintException):
        repository.latest("600000")
    assert not repository._schema_ready
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0] == 1
        assert "observation_id" not in {row[1] for row in connection.execute(
            "PRAGMA table_info('daily_bars')"
        ).fetchall()}
        connection.execute("UPDATE daily_bars SET source = 'legacy'")
    assert repository.latest("600000")[0].source == "legacy"
    assert BarRepository(database, tmp_path / "parquet").latest("600000")[0].close == Decimal("9.5")


def test_unfinished_legacy_migration_is_not_silently_accepted(tmp_path) -> None:
    database = tmp_path / "market.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE daily_bars_legacy (symbol VARCHAR)")
        connection.execute("INSERT INTO daily_bars_legacy VALUES ('600000')")
    repository = BarRepository(database, tmp_path / "parquet")
    with pytest.raises(RuntimeError, match="Unfinished"):
        repository.latest("600000")
    assert not repository._schema_ready


def test_bulk_insert_keeps_decimal_precision_and_deduplicates_late_rows(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    bars = make_history("600000", 1500)
    bars = [bar.model_copy(update={
        "open": Decimal("9"), "high": Decimal("10"),
        "low": Decimal("8"), "close": Decimal("9"),
    }) for bar in bars]
    last = bars[-1].model_copy(update={
        "close": Decimal("9.1234"), "amount": Decimal("12345678901234567890.1234"),
        "volume": 9_007_199_254_740_993,
    })
    bars[-1] = last

    assert repository.append_preferred_batch(bars + [last], (last.source,)) == (1500, 0, 0)
    assert repository.append_preferred_batch(bars, (last.source,)) == (0, 0, 1500)
    stored = repository.latest("600000", 1)[0]
    assert stored.close == last.close
    assert stored.amount == last.amount
    assert stored.volume == last.volume
