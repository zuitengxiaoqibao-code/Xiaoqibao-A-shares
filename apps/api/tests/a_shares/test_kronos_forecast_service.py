from datetime import date, timedelta
from decimal import Decimal

import pytest

from qibao_api.a_shares.kronos_forecast import (
    KronosForecastService,
    KronosUnavailableError,
)
from qibao_api.contracts.bars import DailyBar


def bar(symbol: str, trade_date: date, close: str) -> DailyBar:
    value = Decimal(close)
    return DailyBar(
        symbol=symbol,
        trade_date=trade_date,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=1_000_000,
        amount=value * Decimal("1000000"),
        source="fixture",
    )


def history(symbol: str = "600000", count: int = 250) -> list[DailyBar]:
    start = date(2025, 7, 1)
    return [bar(symbol, start + timedelta(days=index), str(10 + index / 100)) for index in range(count)]


class FakeBars:
    def __init__(self, bars: list[DailyBar]):
        self.bars = bars

    def latest(self, symbol: str, limit: int = 250):
        return self.bars[-limit:]


class WeekdayCalendar:
    def is_trading_day(self, value: date) -> bool:
        return value.weekday() < 5


class FakePredictor:
    def predict_paths(self, bars, future_dates, sample_count):
        assert len(bars) == 250
        assert len(future_dates) == 5
        assert sample_count == 3
        last = bars[-1].close
        return [
            [last + Decimal("0.10") * Decimal(index + 1) for index in range(5)],
            [last + Decimal("0.20") * Decimal(index + 1) for index in range(5)],
        ]


class UnavailablePredictor:
    def predict_paths(self, bars, future_dates, sample_count):
        raise KronosUnavailableError("kronos_dependencies_missing")


class BrokenPredictor:
    def predict_paths(self, bars, future_dates, sample_count):
        raise RuntimeError("model crashed")


@pytest.mark.asyncio
async def test_forecast_returns_ready_summary_from_verified_daily_bars() -> None:
    service = KronosForecastService(
        bar_repository=FakeBars(history()),
        trading_calendar=WeekdayCalendar(),
        predictor=FakePredictor(),
        lookback_bars=250,
        sample_count=3,
    )

    response = await service.forecast("600000", as_of=date(2026, 7, 24), horizon=5)

    assert response.status == "ready"
    assert response.observed_through == history()[-1].trade_date
    assert len(response.points) == 5
    assert response.summary is not None
    assert response.sources == ("local-daily-bars", "kronos")


@pytest.mark.asyncio
async def test_forecast_reports_insufficient_history_without_calling_predictor() -> None:
    predictor = FakePredictor()
    service = KronosForecastService(
        bar_repository=FakeBars(history(count=20)),
        trading_calendar=WeekdayCalendar(),
        predictor=predictor,
        lookback_bars=250,
        sample_count=3,
    )

    response = await service.forecast("600000", as_of=date(2026, 7, 24), horizon=5)

    assert response.status == "insufficient"
    assert response.points == ()
    assert "daily_history_insufficient" in response.reasons


@pytest.mark.asyncio
async def test_forecast_keeps_missing_runtime_explicit() -> None:
    service = KronosForecastService(
        bar_repository=FakeBars(history()),
        trading_calendar=WeekdayCalendar(),
        predictor=UnavailablePredictor(),
    )

    response = await service.forecast("600000", as_of=date(2026, 7, 24), horizon=5)

    assert response.status == "unavailable"
    assert response.points == ()
    assert response.reasons == ("kronos_dependencies_missing",)


@pytest.mark.asyncio
async def test_forecast_isolates_runtime_errors() -> None:
    service = KronosForecastService(
        bar_repository=FakeBars(history()),
        trading_calendar=WeekdayCalendar(),
        predictor=BrokenPredictor(),
    )

    response = await service.forecast("600000", as_of=date(2026, 7, 24), horizon=5)

    assert response.status == "error"
    assert response.points == ()
    assert response.reasons == ("kronos_runtime_error",)
