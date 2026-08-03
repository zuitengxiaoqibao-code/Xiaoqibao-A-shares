from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.a_shares.market_review import build_market_review
from qibao_api.gongbu.tdx_local_daily import TdxLocalDailyBar


NOW = datetime(2026, 7, 30, 8, 30, tzinfo=timezone.utc)


def bars(symbol: str, closes: list[str], volumes: list[int] | None = None):
    volumes = volumes or [100] * len(closes)
    result = []
    for index, (close, volume) in enumerate(zip(closes, volumes, strict=True), start=1):
        price = Decimal(close)
        result.append(TdxLocalDailyBar(
            symbol=symbol,
            trade_date=date(2025, 12, 31) + timedelta(days=index),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume,
            amount=price * volume,
        ))
    return tuple(result)


def test_review_separates_consecutive_limit_up_and_first_board() -> None:
    histories = {
        "600001": bars("600001", ["10.00", "11.00", "12.10"]),
        "600002": bars("600002", ["10.00", "10.20", "11.22"]),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: {"600001": "两连样本", "600002": "首板样本"}[symbol],
    )

    assert [(item.symbol, item.board_count) for item in result.consecutive_limit_up] == [
        ("600001", 2),
    ]
    assert [item.symbol for item in result.first_limit_up] == ["600002"]
    assert result.latest_trade_date == date(2026, 1, 3)


def test_review_uses_twenty_percent_limit_for_chinext() -> None:
    histories = {
        "300001": bars("300001", ["10.00", "12.00"]),
        "300002": bars("300002", ["10.00", "11.00"]),
        "600001": bars("600001", ["10.00", "11.00"]),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: "ST创业板" if symbol == "300002" else symbol,
    )

    assert {item.symbol for item in result.first_limit_up} == {"300001", "600001"}


def test_review_detects_volume_breakout_without_lookahead() -> None:
    prior = [str(Decimal("10") + Decimal(index) / Decimal("100")) for index in range(60)]
    histories = {
        "600003": bars(
            "600003",
            [*prior, "10.80"],
            [100] * 60 + [250],
        ),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: "放量突破样本",
    )

    item = result.volume_breakouts[0]
    assert item.symbol == "600003"
    assert item.reference_high == Decimal("10.59")
    assert item.volume_multiple == Decimal("2.50")
    assert item.window_days == 60


def test_review_detects_low_position_volume_only_in_lower_thirty_percent() -> None:
    low_position = ["10", *(["20"] * 118), "11"]
    high_position = ["10", *(["20"] * 118), "19"]
    histories = {
        "600004": bars("600004", low_position, [100] * 119 + [200]),
        "600005": bars("600005", high_position, [100] * 119 + [200]),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert [item.symbol for item in result.low_position_volume] == ["600004"]
    assert result.low_position_volume[0].range_position_percent == Decimal("10.00")


def test_review_does_not_fabricate_intraday_limit_fields() -> None:
    result = build_market_review(
        {"600006": bars("600006", ["10.00", "11.00"])},
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: "字段边界样本",
    )

    item = result.first_limit_up[0]
    assert item.seal_amount_yi is None
    assert item.failed_limit_count is None
    assert item.first_seal_time is None
    assert item.turnover_rate is None
