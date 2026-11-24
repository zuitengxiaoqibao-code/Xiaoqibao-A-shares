from datetime import date, datetime, time, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

import httpx
from pydantic import AwareDatetime, BaseModel


class MarketSessionStatus(BaseModel):
    status: Literal["ready", "unavailable"]
    trading_date: date
    observed_at: AwareDatetime
    is_trading_day: bool | None
    phase: Literal["closed", "pre_open", "intraday", "lunch_break", "post_close", "unknown"]


def market_session_status(now: datetime, calendar) -> MarketSessionStatus:
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    trading_day = None
    if calendar is not None:
        check = getattr(calendar, "trading_day_status", calendar.is_trading_day)
        try:
            trading_day = check(local.date())
        except (ValueError, OSError):
            trading_day = None
    phase = "unknown"
    if trading_day is False:
        phase = "closed"
    elif trading_day is True:
        clock = local.time()
        if clock < time(9, 30):
            phase = "pre_open"
        elif clock < time(11, 30) or time(13) <= clock < time(15):
            phase = "intraday"
        elif clock < time(13):
            phase = "lunch_break"
        else:
            phase = "post_close"
    return MarketSessionStatus(
        status="unavailable" if trading_day is None else "ready",
        trading_date=local.date(), observed_at=local,
        is_trading_day=trading_day, phase=phase,
    )


class TradingDaySignal(Protocol):
    def confirmed_date(self) -> date | None: ...


class TradingDaySchedule(Protocol):
    def is_trading_day(self, value: date) -> bool | None: ...


class ExchangeCalendarsTradingDaySchedule:
    def __init__(self, calendar=None) -> None:
        self.calendar = calendar

    def _resolved_calendar(self):
        if self.calendar is None:
            import exchange_calendars

            self.calendar = exchange_calendars.get_calendar("XSHG")
        return self.calendar

    def is_trading_day(self, value: date) -> bool | None:
        try:
            return bool(self._resolved_calendar().is_session(value))
        except ValueError:
            return None


class TencentIndexTradingDaySignal:
    def __init__(
        self,
        client,
        *,
        clock=datetime.now,
        cache_seconds: int = 30,
    ) -> None:
        self.client = client
        self.clock = clock
        self.cache_duration = timedelta(seconds=cache_seconds)
        self._cached_at: datetime | None = None
        self._cached_date: date | None = None

    def confirmed_date(self) -> date | None:
        now = self.clock()
        if self._cached_at is not None and now - self._cached_at < self.cache_duration:
            return self._cached_date
        try:
            response = self.client.get("https://qt.gtimg.cn/q=sh000001")
            response.raise_for_status()
            body = response.content.decode("gbk", errors="strict")
            payload = body.split('="', 1)[1].rsplit('"', 1)[0]
            fields = payload.split("~")
            if len(fields) < 31 or not fields[3] or fields[3] == "0":
                raise ValueError("Tencent index payload is incomplete")
            observed = datetime.strptime(fields[30], "%Y%m%d%H%M%S").date()
        except (httpx.HTTPError, IndexError, UnicodeError, ValueError, OSError):
            observed = None
        self._cached_at = now
        self._cached_date = observed
        return observed


class StoredTradingCalendar:
    def __init__(
        self,
        bar_repository,
        live_signal: TradingDaySignal | None = None,
        schedule: TradingDaySchedule | None = None,
    ) -> None:
        self.bar_repository = bar_repository
        self.live_signal = live_signal
        self.schedule = schedule

    def is_trading_day(self, value: date) -> bool:
        return self.trading_day_status(value) is True

    def trading_day_status(self, value: date) -> bool | None:
        if value in self.bar_repository.trade_dates(limit=1000):
            return True
        if self.schedule is not None:
            scheduled = self.schedule.is_trading_day(value)
            if scheduled is not None:
                return scheduled
        if self.live_signal is not None and self.live_signal.confirmed_date() == value:
            return True
        return False if value.weekday() >= 5 else None

    def previous_trading_day(self, value: date) -> date:
        candidates = [
            item for item in self.bar_repository.trade_dates(limit=1000) if item < value
        ]
        if not candidates:
            raise ValueError(f"no confirmed trading day exists before {value}")
        return max(candidates)
