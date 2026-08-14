import struct
import zipfile
from datetime import date
from decimal import Decimal

from qibao_api.gongbu.tdx_local_import import TdxLocalImportService
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
