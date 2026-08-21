from datetime import date
from decimal import Decimal
from qibao_api.a_shares.quant_scan_snapshot import QuantScanSnapshotManager
from qibao_api.contracts.bars import DailyBar
from qibao_api.storage.bar_repository import BarRepository


def bar(symbol: str, trade_date: date, close: str) -> DailyBar:
    price = Decimal(close)
    return DailyBar(
        symbol=symbol,
        trade_date=trade_date,
        open=price,
        high=price + Decimal("0.1"),
        low=price - Decimal("0.1"),
        close=price,
        volume=1_000_000,
        amount=Decimal("20_000_000"),
        source="test-daily-bars",
    )


def test_scan_snapshot_is_isolated_and_reused_for_the_same_source_watermark(tmp_path) -> None:
    source_dir = tmp_path / "金融财经"
    repository = BarRepository(source_dir / "market.duckdb", source_dir / "parquet")
    repository.upsert([bar("600001", date(2026, 8, 20), "10")])
    manager = QuantScanSnapshotManager(tmp_path / "scan-cache")

    first = manager.prepare(repository, as_of=date(2026, 8, 20))
    second = manager.prepare(repository, as_of=date(2026, 8, 20))

    assert first.database_path != repository.database_path
    assert first.database_path.is_file()
    assert first.database_path == second.database_path
    assert first.source_size > 0
    snapshot_repository = BarRepository(
        first.database_path,
        first.parquet_path,
        read_only=True,
        ensure_schema=False,
    )
    assert snapshot_repository.latest("600001")[0].close == Decimal("10.0000")
    assert repository.latest("600001")[0].close == Decimal("10.0000")


def test_scan_snapshot_rebuilds_after_the_formal_database_watermark_changes(tmp_path) -> None:
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    repository.upsert([bar("600001", date(2026, 8, 20), "10")])
    manager = QuantScanSnapshotManager(tmp_path / "scan-cache")
    first = manager.prepare(repository, as_of=date(2026, 8, 20))

    repository.upsert([bar("600001", date(2026, 8, 21), "10.5")])
    second = manager.prepare(repository, as_of=date(2026, 8, 21))

    assert second.database_path != first.database_path
    assert second.source_mtime_ns >= first.source_mtime_ns
    snapshot_repository = BarRepository(
        second.database_path,
        second.parquet_path,
        read_only=True,
        ensure_schema=False,
    )
    assert snapshot_repository.latest("600001")[0].trade_date == date(2026, 8, 21)
