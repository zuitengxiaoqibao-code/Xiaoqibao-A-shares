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


class _WarmingLocalSource:
    def __init__(self, quote: TdxRealtimeQuote) -> None:
        self.quote = quote
        self.refresh_calls = 0

    def current_quotes(self):
        return () if self.refresh_calls == 0 else (self.quote,)

    def refresh(self):
        self.refresh_calls += 1
        return None


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


def test_service_refreshes_a_warming_local_source_before_reporting_no_market_data() -> None:
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
    local_source = _WarmingLocalSource(quote)
    settings = LateSessionRuleSettings(
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
    )
    service = LateSessionSelectionService(
        local_market_source=local_source,
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        tencent_source=None,
        clock=lambda: datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")),
    )

    result = service.current(settings=settings)

    assert local_source.refresh_calls == 1
    assert result.data_state != "no_market_data"
    assert result.candidate_count == 1


def test_service_enrichment_uses_full_market_batches() -> None:
    class Tencent:
        def __init__(self) -> None:
            self.batches: list[tuple[str, ...]] = []

        def fetch_stocks(self, symbols):
            self.batches.append(tuple(symbols))
            return (), ()

    tencent = Tencent()
    service = LateSessionSelectionService(
        local_market_source=_LocalSource.__new__(_LocalSource),
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        tencent_source=tencent,
    )
    quotes = tuple(
        SimpleNamespace(symbol=f"{600000 + index:06d}")
        for index in range(321)
    )

    service._enrich(quotes, datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")))

    assert tuple(map(len, tencent.batches)) == (320, 1)


def test_service_skips_reenrichment_when_snapshot_has_verified_fields() -> None:
    class Tencent:
        def fetch_stocks(self, _symbols):
            raise AssertionError("verified snapshot must not be fetched again")

    service = LateSessionSelectionService(
        local_market_source=_LocalSource.__new__(_LocalSource),
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        tencent_source=Tencent(),
    )

    result = service._enrich(
        (SimpleNamespace(symbol="600000", turnover_rate=Decimal("0.31"), market_cap_yi=Decimal("162.25")),),
        datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")),
    )

    assert result == {}


def test_service_reads_history_once_for_all_tail_selection_symbols() -> None:
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

    class BatchBars:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], int, object]] = []

        def latest_many(self, symbols, limit, as_of):
            self.calls.append((symbols, limit, as_of))
            return {symbol: list(_Bars().latest(symbol, limit=limit)) for symbol in symbols}

        def latest(self, *_args, **_kwargs):
            raise AssertionError("tail selection must use one batched history query")

    bars = BatchBars()
    settings = LateSessionRuleSettings(
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
    )
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=bars,
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        clock=lambda: datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")),
    )

    result = service.current(settings=settings)

    assert result.candidate_count == 1
    assert bars.calls == [(["600000"], 21, datetime(2026, 8, 17).date())]


def test_service_reuses_slow_history_factors_across_same_day_refreshes() -> None:
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

    class BatchBars:
        def __init__(self) -> None:
            self.calls = 0

        def latest_many(self, symbols, limit, as_of):
            del limit, as_of
            self.calls += 1
            return {symbol: list(_LimitUpBars().latest(symbol, limit=21)) for symbol in symbols}

    bars = BatchBars()
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=bars,
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        clock=lambda: datetime(2026, 8, 17, 6, 31, tzinfo=ZoneInfo("UTC")),
    )

    first = service.current()
    second = service.current()

    assert first.candidate_count == second.candidate_count
    assert bars.calls == 1


def test_service_returns_truthful_observation_candidates_when_only_real_fields_are_missing() -> None:
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
        amount_wan=Decimal("0"),
        observed_at=datetime(2026, 8, 17, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        market_cap_yi=Decimal("100"),
        turnover_rate=Decimal("10"),
        intraday_average_price=None,
    )
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=_LimitUpBars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        tencent_source=None,
        clock=lambda: datetime(2026, 8, 17, 7, 1, tzinfo=ZoneInfo("UTC")),
    )

    result = service.current()

    assert result.data_state == "partial"
    assert result.candidate_count == 1
    assert result.candidates[0].passed is False
    assert result.candidates[0].risk_notes == ("待补齐：分时黄线",)


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


def test_service_publishes_only_meaningful_candidate_lifecycle_changes() -> None:
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

    class Bus:
        def __init__(self) -> None:
            self.events = []

        def publish(self, kind, payload, **metadata):
            self.events.append((kind, payload, metadata))

    bus = Bus()
    settings = LateSessionRuleSettings(
        turnover_rate_enabled=False,
        market_cap_enabled=False,
        twenty_day_limit_up_enabled=False,
    )
    service = LateSessionSelectionService(
        local_market_source=_LocalSource(quote),
        bar_repository=_Bars(),
        instrument_directory=SimpleNamespace(resolve=lambda _symbol: None),
        realtime_snapshot_bus=bus,
        clock=lambda: datetime(2026, 8, 17, 6, 31, tzinfo=ZoneInfo("UTC")),
    )

    first = service.current(settings=settings)
    second = service.current(settings=settings)
    third = service.current(settings=settings)
    fourth = service.current(settings=settings)

    assert first.monitor_stage == "monitor"
    assert first.candidates[0].lifecycle_status == "near_match"
    assert second.candidates[0].lifecycle_status == "near_match"
    assert third.candidates[0].lifecycle_status == "strict_passed"
    assert fourth.candidates[0].lifecycle_status == "strict_passed"
    assert [event[0] for event in bus.events] == ["late_session_candidates", "late_session_candidates"]
    assert bus.events[-1][1]["candidates"][0]["lifecycle_status"] == "strict_passed"
