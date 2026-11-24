from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from qibao_api.gongbu.axdata_quotes import AxDataTencentQuoteSource
from qibao_api.gongbu.eltdx_source import EltdxSource
from qibao_api.gongbu.external_quote_sources import ExternalQuoteFallbackSource
from qibao_api.gongbu.history_sync_repository import HistorySyncRepository

NOW = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)


def bar(**changes):
    values = dict(time=datetime(2026, 11, 20), open=10, high=12, low=9, close=11,
                  volume_wire_value=12345, volume_raw=999, amount=135795)
    return NS(**(values | changes))


def series(*bars, **changes):
    return NS(**(dict(full_code="sh600000", adjust_mode="none", bars=bars or (bar(),)) | changes))


def native(result=None):
    return NS(bars=NS(get=Mock(return_value=result or series())), close=Mock())


def test_eltdx_lazy_pool_reused_and_units_preserved():
    client = native()
    factory = Mock(return_value=client)
    events = []
    source = EltdxSource(factory=factory, clock=lambda: NOW, observer=events.append)
    factory.assert_not_called()
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(lambda _: source.fetch_daily("600000", 1), range(8)))
    factory.assert_called_once()
    result = results[0][0]
    assert result.volume == 12345  # shares, never compressed volume_raw
    assert result.amount == Decimal("135795")
    assert result.source == "eltdx"
    assert all(e.status == "ready" and e.metadata["upstream"] == "tdx" for e in events)
    source.close()
    source.close()
    client.close.assert_called_once()
    with pytest.raises(Exception, match="closed"):
        source.fetch_daily("600000", 1)


@pytest.mark.parametrize("result", [
    series(full_code="sz000001"), series(adjust_mode="qfq"),
    series(bar(volume_wire_value=-1)), series(bar(volume_wire_value=1.2)),
    series(bar(volume_wire_value=float("nan"))), series(bar(amount=float("nan"))),
    series(bar(close=20)), series(bar(time=datetime(2026, 11, 21))),
    series(bar(), bar()), NS(full_code="sh600000", adjust_mode="none", bars=()),
])
def test_eltdx_rejects_invalid_data(result):
    source = EltdxSource(factory=lambda: native(result), clock=lambda: NOW)
    with pytest.raises(Exception):
        source.fetch_daily("600000", 10)


@pytest.mark.parametrize("limit", [0, -1, 4001])
def test_eltdx_invalid_limit_does_not_initialize(limit):
    factory = Mock()
    with pytest.raises(ValueError):
        EltdxSource(factory=factory).fetch_daily("600000", limit)
    factory.assert_not_called()


def test_eltdx_pages_and_sorts():
    client = native()
    bars = tuple(bar(time=datetime(2026, 11, 20) - timedelta(days=i)) for i in range(801))
    client.bars.get.side_effect = [series(*bars[:800]), series(bars[800])]
    source = EltdxSource(factory=lambda: client, clock=lambda: NOW)
    values = source.fetch_daily("600000", 801)
    assert len(values) == 801 and values[0].trade_date < values[-1].trade_date
    assert client.bars.get.call_args_list[1].kwargs == dict(period="day", start=800, count=1, adjust="none")


def test_eltdx_operation_cooldowns_separate_and_bounded(monkeypatch):
    tick = [100.0]
    monkeypatch.setattr("qibao_api.gongbu.eltdx_source.monotonic", lambda: tick[0])
    client = native()
    client.bars.get.side_effect = [OSError("offline"), series()]
    source = EltdxSource(factory=lambda: client, clock=lambda: NOW)
    with pytest.raises(OSError):
        source._minutes("sh600000")
    assert source.fetch_daily("600000", 1)
    with pytest.raises(Exception, match="冷却"):
        source._minutes("sh600000")
    tick[0] = 131
    client.bars.get.side_effect = None
    client.minutes = NS(history=Mock(return_value=NS(full_code="sh600000", trading_date=date(2026,11,20),
        prev_close=10, points=(NS(time=datetime(2026,11,20,15),price=11),))))
    assert source._minutes("sh600000")[1][-1].price == 11
    client.minutes.history.assert_called_once_with("sh600000", date(2026,11,20))


def test_eltdx_does_not_fabricate_intraday_amount_or_snapshot_date():
    factory = Mock()
    source = EltdxSource(factory=factory)
    assert source.fetch_minutes()[0] == ()
    assert source.fetch_stocks(("600000",))[0] == ()
    factory.assert_not_called()


def test_eltdx_native_transport_outage_cools_all_symbols(monkeypatch):
    from eltdx.exceptions import ResponseTimeoutError

    tick = [100.0]
    monkeypatch.setattr("qibao_api.gongbu.eltdx_source.monotonic", lambda: tick[0])
    client = native()
    client.bars.get.side_effect = ResponseTimeoutError("offline")
    source = EltdxSource(factory=lambda: client, clock=lambda: NOW)
    with pytest.raises(ResponseTimeoutError):
        source.fetch_daily("600000", 1)
    with pytest.raises(Exception, match="冷却"):
        source.fetch_daily("000001", 1)
    assert client.bars.get.call_count == 1
    tick[0] = 131
    client.bars.get.side_effect = None
    assert source.fetch_daily("600000", 1)


def row(**changes):
    return dict(instrument_id="600000.SH", symbol="600000", name="浦发银行", quote_time="20261120150000",
        change_pct=1.59, amount=1080161854, total_market_value=3620.34, turnover_rate=0.3,
        last_price=10.87, change=0.17) | changes


def ax(rows):
    adapter = NS(request=Mock(return_value=rows))
    return AxDataTencentQuoteSource(factory=lambda: adapter, clock=lambda: NOW), adapter


def test_axdata_stateless_adapter_fields_and_duplicates_requested():
    source, adapter = ax([row()])
    quotes, warnings = source.fetch_stocks(("600000", "600000", "000001"))
    assert len(quotes) == 1
    assert quotes[0].amount_yi == Decimal("10.80161854")
    assert quotes[0].market_cap_yi == Decimal("3620.34")
    assert quotes[0].turnover_rate == Decimal("0.3")
    assert "axdata_quote_missing:000001.SZ" in warnings
    adapter.request.assert_called_once_with("tencent_realtime_snapshot", {"code": ["600000.SH", "000001.SZ"]})


@pytest.mark.parametrize("rows", [[], [row(),row()], [row(symbol="000001")],
    [row(instrument_id="600000.SZ")], [row(quote_time="20261121150000")],
    [row(change_pct=float("nan"))], [row(amount=-1)], [row(quote_time="bad")]])
def test_axdata_validation_failure_observable_and_cooled(rows):
    source, adapter = ax(rows)
    events = []
    source.observer = events.append
    with pytest.raises(Exception):
        source.fetch_stocks(("600000",))
    with pytest.raises(Exception, match="冷却"):
        source.fetch_stocks(("600000",))
    assert adapter.request.call_count == 1
    assert events[0].status == "error"


def test_axdata_small_clock_skew_preserves_original_time_and_warns():
    source, _ = ax([row(quote_time="20261120160010")])
    values, warnings = source.fetch_stocks(("600000",))
    assert values[0].observed_at > NOW
    assert "axdata_clock_skew_within_30s" in warnings


def test_axdata_bse_identity():
    source, adapter = ax([row(instrument_id="920000.BJ", symbol="920000")])
    assert source.fetch_stocks(("920000",))[0][0].symbol == "920000"
    assert adapter.request.call_args.args[1] == {"code":["920000.BJ"]}


def test_axdata_indices_stale_and_missing_reported():
    source, _ = ax([row(instrument_id="000001.SH", symbol="000001")])
    values, warnings = source.fetch_indices()
    assert values[0].instrument == "sh000001" and values[0].quality == "stale"
    assert "axdata_quote_missing:399001.SZ" in warnings


def test_axdata_chunks_large_request_at_eighty_symbols():
    symbols = tuple(str(600000 + index) for index in range(81))
    adapter = NS(request=Mock(side_effect=lambda interface, params: [
        row(instrument_id=code, symbol=code[:6]) for code in params["code"]
    ]))
    source = AxDataTencentQuoteSource(factory=lambda: adapter, clock=lambda: NOW)
    assert len(source.fetch_stocks(symbols)[0]) == 81
    assert [len(call.args[1]["code"]) for call in adapter.request.call_args_list] == [80, 1]


@pytest.mark.parametrize("points,day", [
    ((NS(time=None,price=11),), date(2026,11,20)),
    ((NS(time=datetime(2026,11,21,10),price=11),), date(2026,11,20)),
    ((NS(time=datetime(2026,11,20,10),price=float("nan")),), date(2026,11,20)),
    ((NS(time=datetime(2026,11,20,10),price=11),)*2, date(2026,11,20)),
    ((NS(time=datetime(2026,11,19,10),price=11),), date(2026,11,19)),
])
def test_eltdx_index_rejects_unverified_minutes(points, day):
    client = native()
    client.minutes = NS(history=Mock(return_value=NS(full_code="sh600000", trading_date=day, points=points)))
    source = EltdxSource(factory=lambda: client, clock=lambda: NOW)
    with pytest.raises(Exception):
        source._minutes("sh600000")


def test_nested_fallback_preserves_actual_source():
    primary = NS(source_id="tencent", fetch_stocks=lambda _: ((), ("offline",)))
    fallback = NS(source_id="configured", fetch_stocks=lambda _: (("quote",), ()))
    inner = ExternalQuoteFallbackSource(primary, (fallback,))
    outer = ExternalQuoteFallbackSource(inner, (ax([])[0],))
    assert outer.fetch_stocks(("600000",))[0] == ("quote",)
    assert outer.last_source_id == "configured"


def test_eltdx_source_count_separate_from_legacy_tdx(tmp_path):
    repository = HistorySyncRepository(tmp_path / "history.sqlite3")
    job = repository.create_job("backfill", date(2026,11,20), ("600000",))
    repository.complete_item(job.job_id,"600000",state="ready",source="eltdx",written_rows=300)
    updated = repository.finish(job.job_id)
    assert updated.eltdx_ready_count == 1 and updated.tdx_ready_count == 0
    assert repository.items(job.job_id)[0].source == "eltdx"
    repository.close()


@pytest.mark.parametrize("primary_fails", [False, True])
def test_full_market_eltdx_primary_and_original_fallback(tmp_path, primary_fails):
    from tests.gongbu.test_full_market_history import service, bars, Source

    primary = Source({"600000": OSError("offline") if primary_fails else bars("600000", 300, source="eltdx")})
    legacy = Source({"600000": bars("600000", 300)})
    value = service(tmp_path, symbols=("600000",), coverage={}, tdx=legacy, baidu=Source({}))
    value.fallback_sources = (("eltdx", primary),)
    job = value.run(value.create_backfill().job_id, comprehensive=True)
    assert job.ready_count == 1
    assert job.eltdx_ready_count == (0 if primary_fails else 1)
    assert job.tdx_ready_count == (1 if primary_fails else 0)
    assert bool(legacy.calls) == primary_fails
