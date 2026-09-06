from datetime import datetime
from decimal import Decimal

import pytest

from qibao_api.gongbu.tencent_overview import (
    TencentOverviewSource,
    parse_index_minutes,
    parse_index_quotes,
    parse_stock_quotes,
)


def quote_line(instrument: str, name: str, code: str, price: str, previous: str) -> str:
    fields = [""] * 50
    fields[0] = "1"
    fields[1] = name
    fields[2] = code
    fields[3] = price
    fields[4] = previous
    fields[30] = "20260729093342"
    fields[31] = str(Decimal(price) - Decimal(previous))
    fields[32] = "-0.18"
    return f'v_{instrument}="{"~".join(fields)}";'


def test_parse_index_quotes_decodes_gbk_and_preserves_requested_order() -> None:
    raw = "\n".join((
        quote_line("sz399001", "深证成指", "399001", "13456.09", "13509.68"),
        quote_line("sh000001", "上证指数", "000001", "3806.47", "3813.31"),
    )).encode("gbk")

    quotes, warnings = parse_index_quotes(raw, ("sh000001", "sz399001"))

    assert warnings == ()
    assert [item.instrument for item in quotes] == ["sh000001", "sz399001"]
    assert quotes[0].name == "上证指数"
    assert quotes[0].value == Decimal("3806.47")
    assert quotes[0].observed_at == datetime.fromisoformat("2026-07-29T09:33:42+08:00")


def test_parse_index_quotes_skips_a_bad_row_and_reports_it() -> None:
    raw = (
        quote_line("sh000001", "上证指数", "000001", "3806.47", "3813.31")
        + '\nv_sz399001="51~深证成指~399001~--";'
    ).encode("gbk")

    quotes, warnings = parse_index_quotes(raw, ("sh000001", "sz399001"))

    assert [item.instrument for item in quotes] == ["sh000001"]
    assert warnings == ("index_quote_invalid:sz399001",)


def test_parse_index_quotes_rejects_non_gbk_payload() -> None:
    with pytest.raises(ValueError, match="GBK"):
        parse_index_quotes(b"\xff\xfe\xff", ("sh000001",))


def test_parse_index_minutes_builds_aware_points() -> None:
    payload = b'''{"code":0,"data":{"sh000001":{"data":{"date":"20260729","data":["0930 3823.29 3929599 8035306473.60","0931 3818.00 15927496 29813887322.90"]}}}}'''

    points, warnings = parse_index_minutes(payload, "sh000001")

    assert warnings == ()
    assert len(points) == 2
    assert points[0].price == Decimal("3823.29")
    assert points[0].observed_at.isoformat() == "2026-07-29T09:30:00+08:00"
    assert points[1].volume == Decimal("15927496")


def test_parse_index_minutes_ignores_malformed_points_but_keeps_valid_data() -> None:
    payload = b'''{"code":0,"data":{"sh000001":{"data":{"date":"20260729","data":["bad row","0931 3818.00 15927496 29813887322.90"]}}}}'''

    points, warnings = parse_index_minutes(payload, "sh000001")

    assert len(points) == 1
    assert warnings == ("minute_point_invalid:bad row",)


def test_parse_stock_quotes_extracts_market_fields() -> None:
    fields = [""] * 47
    fields[1] = "东方新能"
    fields[2] = "002310"
    fields[3] = "12.10"
    fields[4] = "11.00"
    fields[30] = "20260729103000"
    fields[32] = "10.00"
    fields[37] = "126500"
    fields[44] = "106.02"
    raw = f'v_sz002310="{"~".join(fields)}";'.encode("gbk")

    quotes, warnings = parse_stock_quotes(raw, ("002310",))

    assert warnings == ()
    assert quotes[0].symbol == "002310"
    assert quotes[0].change_percent == Decimal("10.00")
    assert quotes[0].amount_yi == Decimal("12.6500")
    assert quotes[0].market_cap_yi == Decimal("106.02")


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, minute: bytes, quote: bytes):
        self.responses = [FakeResponse(minute), FakeResponse(quote)]

    def get(self, *_args, **_kwargs):
        return self.responses.pop(0)


class IndexedMinuteClient:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.requested: list[str] = []

    def get(self, *_args, **kwargs):
        instrument = kwargs.get("params", {}).get("code")
        self.requested.append(instrument)
        return FakeResponse(self.payloads[instrument])


def minute_payload(instrument: str, price: str) -> bytes:
    return (
        '{"code":0,"data":{"%s":{"data":{"date":"20260729",'
        '"data":["0930 %s 10 1000"]}}}}'
    ).encode("utf-8") % (instrument.encode(), price.encode())


def test_fetch_minutes_by_index_keeps_independent_series() -> None:
    client = IndexedMinuteClient({
        "sh000001": minute_payload("sh000001", "3200.00"),
        "sz399001": minute_payload("sz399001", "10000.00"),
        "sz399006": minute_payload("sz399006", "2000.00"),
    })
    source = TencentOverviewSource(client)

    series, warnings = source.fetch_minutes_by_index()

    assert warnings == ()
    assert client.requested == ["sh000001", "sz399001", "sz399006"]
    assert set(series) == {"sh000001", "sz399001", "sz399006"}
    assert [series[key][0].price for key in ("sh000001", "sz399001", "sz399006")] == [
        Decimal("3200.00"), Decimal("10000.00"), Decimal("2000.00"),
    ]


def test_fetch_minutes_by_index_reports_only_failed_index() -> None:
    class FailingIndexedMinuteClient(IndexedMinuteClient):
        def get(self, *_args, **kwargs):
            instrument = kwargs.get("params", {}).get("code")
            self.requested.append(instrument)
            if instrument == "sz399001":
                raise OSError("offline")
            return FakeResponse(self.payloads[instrument])

    client = FailingIndexedMinuteClient({
        "sh000001": minute_payload("sh000001", "3200.00"),
        "sz399001": minute_payload("sz399001", "10000.00"),
        "sz399006": minute_payload("sz399006", "2000.00"),
    })
    source = TencentOverviewSource(client)

    series, warnings = source.fetch_minutes_by_index()

    assert series["sh000001"] and series["sz399006"]
    assert series["sz399001"] == ()
    assert "minute_series_unavailable:sz399001" in warnings


def test_fetch_stock_minutes_builds_real_points_and_drops_post_close_rows() -> None:
    minute = b'''{"code":0,"data":{"sh600519":{"data":{"date":"20260729","data":["0930 100.00 10 1000","1500 101.00 20 2020","1530 101.00 20 2020"]}}}}'''
    fields = [""] * 50
    fields[1] = "测试股"
    fields[2] = "600519"
    fields[3] = "101.00"
    fields[4] = "99.00"
    fields[30] = "20260729150000"
    quote = f'v_sh600519="{"~".join(fields)}";'.encode("gbk")

    source = TencentOverviewSource(FakeClient(minute, quote))
    points = source.fetch_stock_minutes(
        "600519", cutoff=datetime.fromisoformat("2026-07-29T16:00:00+08:00")
    )

    assert len(points) == 2
    assert points[-1].observed_at.isoformat() == "2026-07-29T15:00:00+08:00"
    assert points[-1].change == Decimal("2.00")
    assert points[-1].change_percent == Decimal("2.020202020202020202020202020")
