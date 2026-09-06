from datetime import datetime
from decimal import Decimal

import httpx

from qibao_api.gongbu.external_quote_sources import (
    ExternalQuoteFallbackSource,
    TickFlowQuoteSource,
    TushareQuoteSource,
    build_external_quote_source,
)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)


def response(payload):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.test"))


def test_tickflow_normalizes_quotes_and_indices_without_leaking_key():
    client = FakeClient([response({"data": [
        {
            "symbol": "600000.SH", "region": "CN", "last_price": 12.3,
            "prev_close": 12.0, "open": 12.1, "high": 12.4, "low": 12.0,
            "volume": 1000, "amount": 1230000, "timestamp": 1770000000000,
            "ext": {"type": "cn_equity", "name": "浦发银行", "change_pct": 0.025,
                    "change_amount": 0.3, "turnover_rate": 0.12},
        },
    ]})])
    source = TickFlowQuoteSource(client, "secret-token")

    stocks, warnings = source.fetch_stocks(("600000",))

    assert warnings == ()
    assert stocks[0].symbol == "600000"
    assert stocks[0].name == "浦发银行"
    assert stocks[0].change_percent == Decimal("2.5")
    assert stocks[0].amount_yi == Decimal("0.0123")
    assert "secret-token" not in str(stocks)


def test_tushare_normalizes_latest_daily_rows():
    client = FakeClient([response({"code": 0, "data": {
        "fields": ["ts_code", "trade_date", "close", "pre_close", "change", "pct_chg", "amount"],
        "items": [["000001.SZ", "20260903", 10.2, 10.0, 0.2, 2.0, 12345]],
    }})])
    source = TushareQuoteSource(client, "secret-token")

    stocks, warnings = source.fetch_stocks(("000001",))

    assert warnings == ()
    assert stocks[0].symbol == "000001"
    assert stocks[0].change_percent == Decimal("2.0")
    assert stocks[0].amount_yi == Decimal("1.2345")
    assert stocks[0].observed_at == datetime.fromisoformat("2026-09-03T15:00:00+08:00")


def test_fallback_calls_external_only_when_primary_is_empty():
    class Primary:
        def __init__(self, result):
            self.result = result
            self.calls = 0

        def fetch_indices(self):
            self.calls += 1
            return self.result

        def fetch_stocks(self, symbols):
            self.calls += 1
            return self.result

    primary = Primary(((), ("primary_unavailable",)))
    external = Primary((("external-index",), ()))
    source = ExternalQuoteFallbackSource(primary, (external,))

    indices, warnings = source.fetch_indices()

    assert indices == ("external-index",)
    assert warnings == ("primary_unavailable",)
    assert primary.calls == 1
    assert external.calls == 1


def test_fallback_preserves_real_unavailable_when_no_external_source():
    class Empty:
        def fetch_indices(self):
            return (), ("index_quotes_unavailable",)

        def fetch_stocks(self, symbols):
            return (), ("stock_quotes_unavailable",)

    source = ExternalQuoteFallbackSource(Empty(), ())

    indices, warnings = source.fetch_indices()

    assert indices == ()
    assert warnings == ("index_quotes_unavailable",)


def test_factory_only_enables_configured_supported_sources():
    class Repository:
        def enabled_key(self, source_id):
            return {"tickflow": "tick-key", "tushare": None, "fuyao": "fuyao-key"}.get(source_id)

    primary = object()
    source = build_external_quote_source(primary, Repository(), FakeClient([]))

    assert source.primary is primary
    assert [item.source_id for item in source.fallbacks] == ["tickflow"]


def test_tickflow_normalizes_compact_intraday_series():
    client = FakeClient([response({"data": {
        "timestamp": [1770000000000],
        "open": [10.0], "high": [10.2], "low": [9.9], "close": [10.1],
        "volume": [100], "amount": [1010],
    }})])
    source = TickFlowQuoteSource(client, "key")

    points, warnings = source.fetch_minutes("sh000001")

    assert warnings == ()
    assert len(points) == 1
    assert points[0].price == Decimal("10.1")
    assert points[0].volume == Decimal("100")


def test_fallback_fetch_minutes_by_index_keeps_each_index_series():
    class Source:
        source_id = "configured"

        def __init__(self):
            self.calls = []

        def fetch_minutes(self, instrument="sh000001"):
            self.calls.append(instrument)
            return (instrument,), ()

    primary = Source()
    source = ExternalQuoteFallbackSource(primary, ())

    series, warnings = source.fetch_minutes_by_index(("sh000001", "sz399001", "sz399006"))

    assert series == {
        "sh000001": ("sh000001",),
        "sz399001": ("sz399001",),
        "sz399006": ("sz399006",),
    }
    assert warnings == ()
    assert primary.calls == ["sh000001", "sz399001", "sz399006"]
