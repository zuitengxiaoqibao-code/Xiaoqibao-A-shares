from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from qibao_api.shangshu.trading_calendar import (
    ExchangeCalendarsTradingDaySchedule,
    StoredTradingCalendar,
    TencentIndexTradingDaySignal,
    market_session_status,
)


class Bars:
    def trade_dates(self, limit=1000):
        return [date(2026, 7, 14), date(2026, 7, 11), date(2026, 7, 10)]


def test_calendar_uses_confirmed_local_market_dates() -> None:
    calendar = StoredTradingCalendar(Bars())

    assert calendar.is_trading_day(date(2026, 7, 14)) is True
    assert calendar.is_trading_day(date(2026, 7, 13)) is False
    assert calendar.previous_trading_day(date(2026, 7, 14)) == date(2026, 7, 11)


def test_calendar_fails_when_prior_market_data_is_missing() -> None:
    calendar = StoredTradingCalendar(type("Empty", (), {"trade_dates": lambda self, limit=1000: []})())

    with pytest.raises(ValueError, match="confirmed trading day"):
        calendar.previous_trading_day(date(2026, 7, 14))


def test_calendar_accepts_today_when_live_index_confirms_open_market() -> None:
    signal = type("Signal", (), {"confirmed_date": lambda self: date(2026, 7, 15)})()
    calendar = StoredTradingCalendar(Bars(), live_signal=signal)

    assert calendar.is_trading_day(date(2026, 7, 15)) is True
    assert calendar.previous_trading_day(date(2026, 7, 15)) == date(2026, 7, 14)


def test_calendar_fails_closed_when_live_signal_is_unavailable() -> None:
    signal = type("Signal", (), {"confirmed_date": lambda self: None})()

    assert StoredTradingCalendar(Bars(), live_signal=signal).is_trading_day(
        date(2026, 7, 15)
    ) is False


def test_exchange_calendar_confirms_premarket_session_and_national_day() -> None:
    schedule = ExchangeCalendarsTradingDaySchedule()

    assert schedule.is_trading_day(date(2026, 7, 17)) is True
    assert schedule.is_trading_day(date(2026, 10, 1)) is False
    assert schedule.is_trading_day(date(2027, 1, 4)) is None


def test_exchange_calendar_defers_heavy_calendar_construction_until_lookup() -> None:
    schedule = ExchangeCalendarsTradingDaySchedule()

    assert schedule.calendar is None
    assert schedule.is_trading_day(date(2026, 7, 17)) is True
    assert schedule.calendar is not None


class Response:
    content = (
        'v_sh000001="1~上证指数~000001~3500.00~3490.00~3501.00~123~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~20260715130630~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";'
    ).encode("gbk")

    def raise_for_status(self) -> None:
        return None


class Client:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, _url):
        self.calls += 1
        return Response()


def test_tencent_index_signal_confirms_payload_date_and_caches() -> None:
    client = Client()
    signal = TencentIndexTradingDaySignal(
        client,
        clock=lambda: datetime(2026, 7, 15, 13, 6, 45),
        cache_seconds=60,
    )

    assert signal.confirmed_date() == date(2026, 7, 15)
    assert signal.confirmed_date() == date(2026, 7, 15)
    assert client.calls == 1


@pytest.mark.parametrize("hour,minute,phase", [
    (9, 29, "pre_open"), (9, 30, "intraday"), (11, 30, "lunch_break"),
    (13, 0, "intraday"), (15, 0, "post_close"),
])
def test_server_market_phase_boundaries(hour, minute, phase):
    now = datetime(2026, 11, 19, hour, minute, tzinfo=ZoneInfo("Asia/Shanghai"))
    calendar = SimpleNamespace(is_trading_day=lambda _date: True)
    assert market_session_status(now, calendar).phase == phase


def test_weekday_holiday_is_closed_and_unavailable_calendar_is_unknown():
    now = datetime(2026, 10, 1, 10, tzinfo=ZoneInfo("Asia/Shanghai"))
    calendar = SimpleNamespace(is_trading_day=lambda _date: False)
    assert market_session_status(now, calendar).phase == "closed"
    assert market_session_status(now, None).phase == "unknown"


def test_market_session_route_uses_shared_calendar_and_server_time():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qibao_api.dependencies import get_server_time
    from qibao_api.routes.operations import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_server_time] = lambda: datetime(2026, 10, 1, 2, tzinfo=ZoneInfo("UTC"))
    client = TestClient(app)
    assert client.get("/api/v1/operations/market-session").json()["phase"] == "unknown"
    app.state.trading_calendar = SimpleNamespace(is_trading_day=lambda _date: False)
    response = client.get("/api/v1/operations/market-session")
    assert response.status_code == 200
    assert response.json()["phase"] == "closed"
    assert response.json()["trading_date"] == "2026-10-01"
