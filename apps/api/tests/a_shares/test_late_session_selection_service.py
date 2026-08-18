from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from qibao_api.a_shares.late_session_selection_service import LateSessionSelectionService
from qibao_api.contracts.late_session_selection import LateSessionRuleSettings
from qibao_api.gongbu.tdx_local_overview import TdxRealtimeQuote


class _LocalSource:
    def __init__(self, quote: TdxRealtimeQuote) -> None:
        self.quote = quote

    def current_quotes(self):
        return (self.quote,)


class _Bars:
    def latest(self, _symbol, *, limit, cutoff=None):
        del cutoff
        return tuple(
            SimpleNamespace(open=Decimal("9"), close=Decimal("9"), volume=Decimal("100"))
            for _ in range(limit)
        )


class _LimitUpBars:
    def latest(self, _symbol, *, limit, cutoff=None):
        del cutoff
        bars = [
            SimpleNamespace(open=Decimal("10.80"), close=Decimal("11.00"), volume=Decimal("100")),
            SimpleNamespace(open=Decimal("10.00"), close=Decimal("10.00"), volume=Decimal("100")),
        ]
        bars.extend(
            SimpleNamespace(open=Decimal("10.00"), close=Decimal("10.00"), volume=Decimal("100"))
            for _ in range(max(0, limit - len(bars)))
        )
        return tuple(bars[:limit])


def test_service_can_select_when_tdx_average_field_is_missing_but_vwap_is_derivable() -> None:
    quote = TdxRealtimeQuote(
        symbol="600000",
        exchange_code="600000.SH",
        name="浦发银行",
        previous_close=Decimal("9.19"),
        price=Decimal("9.65"),
        high=Decimal("9.65"),
        low=Decimal("9.17"),
        open=Decimal("9.19"),
        volume=Decimal("300"),
        amount_wan=Decimal("27.90"),
        observed_at=datetime(2026, 8, 17, 14, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
        intraday_average_price=None,
    )
    settings = LateSessionRuleSettings(
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
    )
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        tencent_source=None,
        clock=lambda: datetime(2026, 8, 17, 6, 31, tzinfo=ZoneInfo("UTC")),
    )

    result = service.current(settings=settings)

    assert result.candidate_count == 1
    assert result.candidates[0].quote.intraday_average_price == Decimal("9.30")
    assert next(rule for rule in result.candidates[0].rules if rule.key == "above_intraday_average").status == "passed"


def test_twenty_day_limit_count_uses_previous_close_not_same_day_open() -> None:
    service = LateSessionSelectionService(
        local_market_source=_LocalSource.__new__(_LocalSource),
        bar_repository=_LimitUpBars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
    )

    assert service._twenty_day_limit_count("600000", datetime(2026, 8, 17).date()) == 1


def test_post_close_keeps_the_last_tail_window_snapshot() -> None:
    quote = TdxRealtimeQuote(
        symbol="600000",
        exchange_code="600000.SH",
        name="浦发银行",
        previous_close=Decimal("9.19"),
        price=Decimal("9.65"),
        high=Decimal("9.65"),
        low=Decimal("9.17"),
        open=Decimal("9.19"),
        volume=Decimal("300"),
        amount_wan=Decimal("27.90"),
        observed_at=datetime(2026, 8, 17, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        intraday_average_price=None,
    )
    settings = LateSessionRuleSettings(
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
    )
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        clock=lambda: datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")),
    )

    result = service.current(settings=settings)

    assert result.phase == "post_close"
    assert result.candidate_count == 1
