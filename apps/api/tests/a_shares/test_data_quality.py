from datetime import date
from decimal import Decimal

from qibao_api.a_shares.data_quality import assess_bar_series
from qibao_api.contracts.bars import DailyBar


def bar(day: int, close: str, *, volume: int = 100, amount: str = "1000") -> DailyBar:
    price = Decimal(close)
    return DailyBar(
        symbol="600000",
        trade_date=date(2026, 8, day),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
        amount=Decimal(amount),
        source="local-test",
    )


def test_clean_series_is_ready() -> None:
    report = assess_bar_series([bar(1, "10"), bar(2, "10.5"), bar(3, "10.8")])

    assert report.status == "ready"
    assert report.blocked is False
    assert report.sample_count == 3
    assert report.issues == ()


def test_duplicate_and_descending_dates_block_the_series() -> None:
    report = assess_bar_series([bar(2, "10"), bar(1, "10.1"), bar(1, "10.2")])

    assert report.status == "error"
    assert report.blocked is True
    assert {item.code for item in report.issues} == {"date_not_ascending", "duplicate_trade_date"}


def test_volume_amount_contradiction_blocks_the_series() -> None:
    report = assess_bar_series([bar(1, "10", volume=0, amount="1000")])

    assert report.blocked is True
    assert report.issues[0].code == "volume_amount_conflict"


def test_large_close_jump_is_a_warning_without_rewriting_values() -> None:
    report = assess_bar_series([bar(1, "10"), bar(2, "14")])

    assert report.status == "partial"
    assert report.blocked is False
    assert report.issues[0].code == "large_close_jump"
    assert report.issues[0].severity == "warning"
    assert report.issues[0].observed_value == Decimal("40.00")
