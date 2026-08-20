import struct
import zipfile
from datetime import date
from decimal import Decimal

from qibao_api.gongbu.tdx_local_import import TdxLocalImportService
from qibao_api.gongbu.tdx_import_repository import TdxImportRepository
from qibao_api.storage.bar_repository import BarRepository


def _day_record(raw_date: int, close: int = 1000) -> bytes:
    return struct.pack(
        "<IIIIIfII", raw_date, close - 2, close + 2, close - 4,
        close, 100.0, 10, 0,
    )


def test_local_import_reads_day_files_and_skips_existing_dates(tmp_path) -> None:
    root = tmp_path / "vipdoc"
    lday = root / "sh" / "lday"
    lday.mkdir(parents=True)
    path = lday / "sh600000.day"
    path.write_bytes(_day_record(20260812) + _day_record(20260813, 1010))
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    from qibao_api.contracts.bars import DailyBar
    repository.upsert([DailyBar(
        symbol="600000", trade_date=date(2026, 8, 12), open=Decimal("9.98"),
        high=Decimal("10.02"), low=Decimal("9.96"), close=Decimal("10"),
        volume=10, amount=Decimal("100"), source="baidu",
    )])

    result = TdxLocalImportService(repository).import_now((root,))

    assert result.state == "completed"
    assert result.imported_rows == 1
    assert result.replaced_rows == 1
    assert [item.trade_date for item in repository.latest("600000", 10)] == [
        date(2026, 8, 13), date(2026, 8, 12)
    ]
    assert repository.latest("600000", 10)[-1].source == "tdx-local-day"


def test_local_import_reads_day_members_from_zip_archive(tmp_path) -> None:
    archive = tmp_path / "g3day.zip"
    payload = _day_record(20260813, 1000)
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sh/lday/sh600001.day", payload)
        handle.writestr("junk.txt", "ignored")
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")

    result = TdxLocalImportService(repository).import_now((archive,))

    assert result.state == "completed"
    assert result.imported_rows == 1
    assert repository.latest("600001", 1)[0].trade_date == date(2026, 8, 13)


def test_directory_scan_and_import_discovers_nested_tdx_archives(tmp_path) -> None:
    root = tmp_path / "T0002"
    root.mkdir()
    archive = root / "g4day.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sz/lday/sz000002.day", _day_record(20260813, 1000))
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    service = TdxLocalImportService(repository)

    scan = service.scan((root,))
    result = service.import_now((root,))

    assert scan.archive_files == 1
    assert scan.day_files == 1
    assert scan.readable_files == 1
    assert result.imported_rows == 1
    assert repository.latest("000002", 1)[0].trade_date == date(2026, 8, 13)
    assert not tuple(tmp_path.glob("qibao-tdx-import-*"))


def test_local_import_reports_invalid_day_file_without_writing_rows(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sz" / "lday"
    root.mkdir(parents=True)
    (root / "sz000001.day").write_bytes(b"not-a-day-record")
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")

    result = TdxLocalImportService(repository).import_now((tmp_path / "vipdoc",))

    assert result.state == "completed"
    assert result.imported_rows == 0
    assert result.failed_files == 1
    assert result.errors[0].code == "invalid_day_file"


def test_background_import_skips_non_stock_files_and_continues_after_bad_file(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh511010.day").write_bytes(_day_record(20260813, 1000))
    (root / "sh600000.day").write_bytes(_day_record(20260813, 1010))
    (root / "sh600001.day").write_bytes(b"broken")
    bars = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    jobs = TdxImportRepository(tmp_path / "tdx-import.sqlite3")
    service = TdxLocalImportService(bars, job_repository=jobs, as_of=date(2026, 8, 19))
    job = service.create_job((tmp_path / "vipdoc",))

    result = service.run(job.job_id)

    assert result.state == "completed"
    assert result.total_files == 2
    assert result.processed_files == 2
    assert result.imported_rows == 1
    assert result.failed_files == 1
    assert result.errors[0].code == "invalid_day_file"
    assert bars.latest("600000", 1)[0].trade_date == date(2026, 8, 13)


def test_background_import_records_one_file_error_and_continues(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(_day_record(20260813, 1010))
    (root / "sh600001.day").write_bytes(_day_record(20260813, 1020))

    class Repository:
        def __init__(self) -> None:
            self.symbols = []

        def append_preferred(self, rows, _priority):
            symbol = rows[0].symbol
            if symbol == "600000":
                raise RuntimeError("database temporarily unavailable")
            self.symbols.append(symbol)
            return len(rows), 0, 0

    bars = Repository()
    jobs = TdxImportRepository(tmp_path / "tdx-import.sqlite3")
    service = TdxLocalImportService(bars, job_repository=jobs, as_of=date(2026, 8, 19))
    job = service.create_job((tmp_path / "vipdoc",))

    result = service.run(job.job_id)

    assert result.state == "completed"
    assert result.processed_files == 2
    assert result.failed_files == 1
    assert bars.symbols == ["600001"]
    assert result.errors[0].code == "file_import_failed"
    assert "database temporarily unavailable" in result.errors[0].detail


def test_synchronous_import_reports_real_file_progress(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(_day_record(20260813, 1010))
    (root / "sh600001.day").write_bytes(_day_record(20260813, 1020))
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    observed = []

    result = TdxLocalImportService(repository, as_of=date(2026, 8, 19)).import_now(
        (tmp_path / "vipdoc",), progress=observed.append,
    )

    assert result.state == "completed"
    assert observed == [(1, 2, "600000"), (2, 2, "600001")]


def test_synchronous_import_reads_only_each_symbols_missing_date_range(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(
        _day_record(20250701, 900) + _day_record(20260817, 1000) + _day_record(20260818, 1010)
    )
    (root / "sh600001.day").write_bytes(
        _day_record(20250701, 1100) + _day_record(20260818, 1110)
    )

    class Coverage:
        def __init__(self, latest_trade_date):
            self.latest_trade_date = latest_trade_date

    class Repository:
        def __init__(self) -> None:
            self.rows = []

        def coverage(self, symbols, _as_of):
            assert symbols == ["600000", "600001"]
            return {
                "600000": Coverage(date(2026, 8, 17)),
                "600001": Coverage(None),
            }

        def append_preferred(self, rows, _priority):
            self.rows.extend(rows)
            return len(rows), 0, 0

    repository = Repository()
    result = TdxLocalImportService(repository, as_of=date(2026, 8, 19)).import_now(
        (tmp_path / "vipdoc",), incremental=True, source="tdx-package", batch_size=256,
    )

    by_symbol = {}
    for bar in repository.rows:
        by_symbol.setdefault(bar.symbol, []).append(bar)
    assert [bar.trade_date for bar in by_symbol["600000"]] == [date(2026, 8, 18)]
    assert [bar.trade_date for bar in by_symbol["600001"]] == [
        date(2025, 7, 1), date(2026, 8, 18),
    ]
    assert {bar.source for bar in repository.rows} == {"tdx-package"}
    assert result.imported_rows == 3


def test_synchronous_import_prefers_bulk_repository_write_for_package_batches(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(_day_record(20260818, 1000))

    class BulkRepository:
        def __init__(self) -> None:
            self.bulk_calls = []
            self.single_calls = 0

        def coverage(self, symbols, _as_of):
            class Coverage:
                latest_trade_date = None
            return {symbol: Coverage() for symbol in symbols}

        def append_preferred_batch(self, rows, _priority):
            self.bulk_calls.append(tuple(rows))
            return len(rows), 0, 0

        def append_preferred(self, rows, _priority):
            self.single_calls += 1
            raise AssertionError("official package import must use the bulk repository path")

    repository = BulkRepository()
    result = TdxLocalImportService(repository, as_of=date(2026, 8, 19)).import_now(
        (tmp_path / "vipdoc",), incremental=True, source="tdx-package", batch_size=256,
    )

    assert result.state == "completed"
    assert result.imported_rows == 1
    assert len(repository.bulk_calls) == 1
    assert repository.single_calls == 0


def test_bulk_repository_write_preserves_source_priority_and_counts(tmp_path) -> None:
    from qibao_api.contracts.bars import DailyBar

    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([
        DailyBar(
            symbol="600000", trade_date=date(2026, 8, 17), open=Decimal("10"),
            high=Decimal("10"), low=Decimal("10"), close=Decimal("10"),
            volume=10, amount=Decimal("100"), source="baidu",
        ),
        DailyBar(
            symbol="600000", trade_date=date(2026, 8, 18), open=Decimal("11"),
            high=Decimal("11"), low=Decimal("11"), close=Decimal("11"),
            volume=10, amount=Decimal("100"), source="tdx-local-day",
        ),
    ])
    incoming = [
        DailyBar(
            symbol="600000", trade_date=date(2026, 8, 17), open=Decimal("10.1"),
            high=Decimal("10.1"), low=Decimal("10.1"), close=Decimal("10.1"),
            volume=11, amount=Decimal("110"), source="tdx-package",
        ),
        DailyBar(
            symbol="600000", trade_date=date(2026, 8, 18), open=Decimal("11.1"),
            high=Decimal("11.1"), low=Decimal("11.1"), close=Decimal("11.1"),
            volume=11, amount=Decimal("110"), source="tdx-package",
        ),
        DailyBar(
            symbol="600000", trade_date=date(2026, 8, 19), open=Decimal("12"),
            high=Decimal("12"), low=Decimal("12"), close=Decimal("12"),
            volume=12, amount=Decimal("120"), source="tdx-package",
        ),
    ]

    result = repository.append_preferred_batch(
        incoming, ("tdx-local-day", "tdx-package"),
    )

    assert result == (1, 1, 1)
    latest = {item.trade_date: item for item in repository.latest("600000", 3)}
    assert latest[date(2026, 8, 17)].source == "tdx-package"
    assert latest[date(2026, 8, 18)].source == "tdx-local-day"
    assert latest[date(2026, 8, 19)].source == "tdx-package"


def test_incremental_import_uses_latest_dates_without_counting_full_history(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(
        _day_record(20260817, 1000) + _day_record(20260818, 1010)
    )

    class Repository:
        def __init__(self) -> None:
            self.rows = []

        def latest_dates(self, symbols, _as_of):
            assert symbols == ["600000"]
            return {"600000": date(2026, 8, 17)}

        def coverage(self, _symbols, _as_of):
            raise AssertionError("incremental import must not count the full history")

        def append_preferred_batch(self, rows, _priority):
            self.rows.extend(rows)
            return len(rows), 0, 0

        def append_preferred(self, rows, priority):
            return self.append_preferred_batch(rows, priority)

    repository = Repository()
    result = TdxLocalImportService(repository, as_of=date(2026, 8, 19)).import_now(
        (tmp_path / "vipdoc",), incremental=True, source="tdx-package", batch_size=256,
    )

    assert result.imported_rows == 1
    assert [bar.trade_date for bar in repository.rows] == [date(2026, 8, 18)]


def test_incremental_import_latest_date_comes_from_imported_rows_not_existing_watermark(tmp_path) -> None:
    root = tmp_path / "vipdoc" / "sh" / "lday"
    root.mkdir(parents=True)
    (root / "sh600000.day").write_bytes(_day_record(20260818, 1000))

    class Repository:
        def latest_dates(self, symbols, _as_of):
            return {symbol: date(2026, 8, 19) for symbol in symbols}

        def append_preferred_batch(self, _rows, _priority):
            raise AssertionError("no rows should be imported past the existing watermark")

        def append_preferred(self, rows, priority):
            return self.append_preferred_batch(rows, priority)

    result = TdxLocalImportService(
        Repository(), as_of=date(2026, 8, 19),
    ).import_now(
        (tmp_path / "vipdoc",), incremental=True, source="tdx-package", batch_size=256,
    )

    assert result.imported_rows == 0
    assert result.latest_trade_date is None
