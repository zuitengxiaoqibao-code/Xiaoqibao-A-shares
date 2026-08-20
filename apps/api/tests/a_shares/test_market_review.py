from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.market_review import build_interval_review, build_market_review
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


def test_review_detects_one_hundred_day_close_new_high() -> None:
    histories = {
        "600007": bars("600007", [*["10"] * 100, "11"]),
        "600008": bars("600008", [*["10"] * 99, "11", "10.5"]),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert [item.symbol for item in result.new_high_100] == ["600007"]
    assert result.new_high_100[0].reference_high == Decimal("10")
    assert result.new_high_100[0].window_days == 100


def test_review_detects_next_day_feedback_after_previous_limit_up() -> None:
    result = build_market_review(
        {"600009": bars("600009", ["10.00", "11.00", "10.50"])},
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: "昨涨停反馈样本",
    )

    item = result.previous_limit_up[0]
    assert item.symbol == "600009"
    assert item.prior_close == Decimal("11.00")
    assert item.prior_change_percent == Decimal("10.00")
    assert item.change_percent == Decimal("-4.55")


def test_interval_review_resolves_trading_dates_and_calculates_return_and_amplitude() -> None:
    result = build_interval_review(
        {"600010": bars("600010", ["10.00", "10.50", "11.00", "10.80"])},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        as_of=date(2026, 1, 4),
        observed_at=NOW,
        name_resolver=lambda _symbol: "区间样本",
    )

    assert result.start_date == date(2026, 1, 1)
    assert result.end_date == date(2026, 1, 4)
    item = result.rows[0]
    assert item.symbol == "600010"
    assert item.start_close == Decimal("10.00")
    assert item.end_close == Decimal("10.80")
    assert item.return_percent == Decimal("8.00")
    assert item.amplitude_percent == Decimal("10.00")


def test_interval_review_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError, match="start_date must be before end_date"):
        build_interval_review(
            {},
            start_date=date(2026, 1, 4),
            end_date=date(2026, 1, 1),
            as_of=date(2026, 1, 4),
            observed_at=NOW,
            name_resolver=lambda symbol: symbol,
        )


def test_review_excludes_benchmark_files_from_stock_rankings() -> None:
    result = build_market_review(
        {"000300": bars("000300", [*(["10"] * 100), "11"])},
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda _symbol: "沪深300",
    )

    assert result.new_high_100 == ()
    assert result.first_limit_up == ()


def test_review_uses_dominant_trade_date_instead_of_sparse_latest_outlier() -> None:
    histories = {
        "600011": bars("600011", ["10.00", "10.10"]),
        "600012": bars("600012", ["10.00", "10.20"]),
        "600013": bars("600013", ["10.00", "10.30", "10.40"]),
    }
    # The third symbol has one newer bar, but it must not move the market-wide
    # review date away from the date shared by the majority of stocks.
    histories["600013"] = tuple([
        *histories["600013"][:-1],
        TdxLocalDailyBar(
            symbol="600013",
            trade_date=date(2026, 1, 3),
            open=Decimal("10.40"),
            high=Decimal("10.40"),
            low=Decimal("10.40"),
            close=Decimal("10.40"),
            volume=100,
            amount=Decimal("1040"),
        ),
    ])

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert result.latest_trade_date == date(2026, 1, 2)
    assert result.latest_available_trade_date == date(2026, 1, 3)
    assert result.latest_trade_date_coverage_percent == Decimal("66.67")
    assert result.watermark.dominant_trade_date == date(2026, 1, 2)
    assert result.watermark.latest_available_trade_date == date(2026, 1, 3)
    assert result.watermark.universe_count == 3
    assert result.watermark.history_ready_count == 2
    assert result.watermark.fragmented_latest_count == 1
    assert result.watermark.coverage_percent == Decimal("66.67")
    assert result.watermark.quality == "partial"
    assert "history_dates_fragmented" in result.warnings
    assert "history_latest_outlier" in result.warnings


def test_review_exposes_query_date_and_requires_refresh_when_history_lags_query() -> None:
    result = build_market_review(
        {
            "600014": bars("600014", ["10.00", "10.10"]),
            "600015": bars("600015", ["10.00", "10.20"]),
        },
        as_of=date(2026, 8, 19),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert result.expected_trade_date == date(2026, 8, 19)
    assert result.latest_trade_date == date(2026, 1, 2)
    assert result.refresh_required is True
    assert result.refresh_reason == "历史日线主导日期落后查询日期"
    assert result.quality == "stale"


def test_review_marks_fragmented_history_partial_but_still_requires_refresh() -> None:
    histories = {
        "600016": bars("600016", ["10.00", "10.10"]),
        "600017": bars("600017", ["10.00", "10.20"]),
        "600018": bars("600018", ["10.00", "10.30", "10.40"]),
    }

    result = build_market_review(
        histories,
        as_of=date(2026, 1, 3),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert result.refresh_required is True
    assert result.refresh_reason == "历史日线覆盖日期分散，不能代表查询日期全市场"
    assert result.quality == "partial"


def test_review_does_not_mark_large_fragmented_watermark_ready() -> None:
    histories = {
        f"6{index:05d}": bars(f"6{index:05d}", ["10.00", "10.10"])
        for index in range(1_021)
    }
    for index in range(1_000, 1_021):
        symbol = f"6{index:05d}"
        histories[symbol] = (
            histories[symbol][0],
            replace(histories[symbol][1], trade_date=date(2026, 1, 3)),
        )

    result = build_market_review(
        histories,
        as_of=date(2026, 7, 30),
        observed_at=NOW,
        name_resolver=lambda symbol: symbol,
    )

    assert result.history_ready_count == 1_000
    assert result.latest_trade_date_coverage_percent == Decimal("97.94")
    assert result.quality == "partial"
    assert result.watermark.quality == "partial"
    assert "history_dates_fragmented" in result.watermark.blockers
    assert "history_coverage_below_98_percent" in result.watermark.blockers
