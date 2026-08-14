from datetime import date
from decimal import Decimal

from qibao_api.contracts.bars import DailyBar
from qibao_api.storage.bar_repository import BarRepository


def _bar(symbol: str, day: int) -> DailyBar:
    price = Decimal("10")
    return DailyBar(
        symbol=symbol,
        trade_date=date(2026, 1, day),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=100,
        amount=Decimal("1000"),
        source="test",
    )


def test_coverage_aggregate_uses_latest_revision_and_dominant_date(tmp_path) -> None:
    repository = BarRepository(tmp_path / "bars.duckdb", tmp_path / "parquet")
    symbols = ["600001", "600002", "600003"]
    repository.upsert([_bar(symbol, 1) for symbol in symbols[:2]])
    repository.upsert([_bar(symbol, 2) for symbol in symbols[:2]])
    repository.upsert([_bar("600003", 3)])

    aggregate = repository.coverage_aggregate(
        symbols, date(2026, 1, 3), minimum_bars=2, backfill_bars=3,
    )

    assert aggregate.universe_count == 3
    assert aggregate.dominant_trade_date == date(2026, 1, 2)
    assert aggregate.dominant_date_count == 2
    assert aggregate.latest_available_trade_date == date(2026, 1, 3)
    assert aggregate.latest_available_trade_date_count == 1
    assert aggregate.history_ready_count == 2
    assert aggregate.backfill_complete_count == 0
