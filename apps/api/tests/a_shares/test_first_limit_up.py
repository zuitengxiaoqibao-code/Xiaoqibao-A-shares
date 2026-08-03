from datetime import date, timedelta
from decimal import Decimal

from qibao_api.a_shares.first_limit_up import (
    evaluate_first_limit_up,
    refresh_candidate_state,
)
from qibao_api.contracts.bars import DailyBar


AS_OF = date(2026, 7, 24)


def _business_days_ending(end: date, count: int) -> list[date]:
    values = []
    cursor = end
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(values))


def _bar(symbol: str, trade_date: date, close: str) -> DailyBar:
    price = Decimal(close)
    return DailyBar(
        symbol=symbol,
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1_000_000,
        amount=price * Decimal("1000000"),
        source="fixture",
    )


def _first_board_history(
    symbol: str = "600001",
    *,
    base: str = "10.00",
    limit_close: str = "11.00",
) -> list[DailyBar]:
    days = _business_days_ending(AS_OF, 270)
    bars = [_bar(symbol, day, base) for day in days[:-1]]
    bars.append(_bar(symbol, days[-1], limit_close))
    return bars


def test_main_board_first_limit_up_is_qualified_but_cannot_be_bought_that_day() -> None:
    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="底部样本",
        bars=_first_board_history(),
        pe_ttm=Decimal("24.8"),
        as_of=AS_OF,
    )

    assert candidate is not None
    assert candidate.selection_status == "qualified"
    assert candidate.stage == "limit_up_day"
    assert candidate.action == "no_buy"
    assert "limit_up_day_no_buy" in candidate.risk_flags
    assert candidate.weekly_bottom is True
    assert candidate.monthly_bottom is True


def test_chinext_uses_twenty_percent_limit_and_pe_must_be_positive_at_most_fifty() -> None:
    valid = evaluate_first_limit_up(
        symbol="300001",
        name="创业样本",
        bars=_first_board_history("300001", limit_close="12.00"),
        pe_ttm=Decimal("50"),
        as_of=AS_OF,
    )
    negative = evaluate_first_limit_up(
        symbol="300001",
        name="创业样本",
        bars=_first_board_history("300001", limit_close="12.00"),
        pe_ttm=Decimal("-2"),
        as_of=AS_OF,
    )
    too_high = evaluate_first_limit_up(
        symbol="300001",
        name="创业样本",
        bars=_first_board_history("300001", limit_close="12.00"),
        pe_ttm=Decimal("50.01"),
        as_of=AS_OF,
    )

    assert valid is not None and valid.selection_status == "qualified"
    assert negative is not None and negative.selection_status == "excluded"
    assert "pe_not_positive" in negative.reasons
    assert too_high is not None and too_high.selection_status == "excluded"
    assert "pe_above_50" in too_high.reasons


def test_recent_limit_up_is_not_treated_as_stage_first_board() -> None:
    bars = _first_board_history()
    earlier = len(bars) - 10
    previous = bars[earlier - 1].close
    bars[earlier] = _bar("600001", bars[earlier].trade_date, str(previous * Decimal("1.10")))

    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="重复涨停样本",
        bars=bars,
        pe_ttm=Decimal("20"),
        as_of=AS_OF,
    )

    assert candidate is not None
    assert candidate.selection_status == "excluded"
    assert "recent_limit_up_within_20_bars" in candidate.reasons


def test_weekly_and_monthly_position_must_both_be_near_the_bottom() -> None:
    bars = _first_board_history(base="5.00", limit_close="11.00")
    bars[-2] = _bar("600001", bars[-2].trade_date, "10.00")

    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="高位样本",
        bars=bars,
        pe_ttm=Decimal("18"),
        as_of=AS_OF,
    )

    assert candidate is not None
    assert candidate.selection_status == "excluded"
    assert candidate.weekly_bottom is False
    assert candidate.monthly_bottom is False
    assert "weekly_not_at_bottom" in candidate.reasons
    assert "monthly_not_at_bottom" in candidate.reasons


def test_five_to_twenty_percent_pullback_after_stable_period_opens_reference_window() -> None:
    initial_bars = _first_board_history()
    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="回撤样本",
        bars=initial_bars,
        pe_ttm=Decimal("22"),
        as_of=AS_OF,
    )
    assert candidate is not None
    future_days = _business_days_ending(date(2026, 7, 31), 5)
    extended = [*initial_bars, *[_bar("600001", day, "10.20") for day in future_days]]

    refreshed = refresh_candidate_state(candidate, extended, as_of=future_days[-1])

    assert refreshed.stage == "pullback_window"
    assert refreshed.action == "staged_entry_reference"
    assert Decimal("0.05") <= refreshed.pullback_pct <= Decimal("0.20")
    assert refreshed.consolidation_days >= 5
    assert refreshed.entry_reference.buy_steps_pct == (
        Decimal("-0.02"), Decimal("-0.05"), Decimal("-0.08")
    )
    assert refreshed.entry_reference.sell_steps_pct == (
        Decimal("0.03"), Decimal("0.06"), Decimal("0.10")
    )


def test_pullback_beyond_twenty_percent_is_risk_expansion_not_a_buy_signal() -> None:
    initial_bars = _first_board_history()
    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="破位样本",
        bars=initial_bars,
        pe_ttm=Decimal("22"),
        as_of=AS_OF,
    )
    assert candidate is not None
    future_days = _business_days_ending(date(2026, 7, 31), 5)
    extended = [*initial_bars, *[_bar("600001", day, "8.50") for day in future_days]]

    refreshed = refresh_candidate_state(candidate, extended, as_of=future_days[-1])

    assert refreshed.stage == "risk_expanded"
    assert refreshed.action == "avoid"
    assert "pullback_above_20_percent" in refreshed.risk_flags
