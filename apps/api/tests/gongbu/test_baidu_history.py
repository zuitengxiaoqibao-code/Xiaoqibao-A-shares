import httpx
import pytest

from qibao_api.gongbu.baidu_history import BaiduHistorySource
from qibao_api.gongbu.tdx_history import DataSourceUnavailable


KEYS = [
    "timestamp", "time", "open", "close",
    "volume", "high", "low", "amount",
]


def baidu_client(payload):
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        )
    )


def market_payload(*rows: str, keys=KEYS):
    return {
        "ResultCode": "0",
        "Result": {
            "newMarketData": {
                "keys": keys,
                "marketData": ";".join(rows),
            }
        },
    }


@pytest.mark.asyncio
async def test_baidu_history_parses_keyed_market_rows() -> None:
    payload = {
        "ResultCode": 0,
        "Result": {
            "newMarketData": {
                "keys": ["timestamp", "time", "open", "close", "volume", "high", "low", "amount"],
                "marketData": "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01,693325381.00",
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["code"] == "600000"
        return httpx.Response(200, json=payload)

    events = []
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bars = BaiduHistorySource(client, observer=events.append).fetch_daily("600000", 20)

    assert len(bars) == 1
    assert bars[0].source == "baidu"
    assert str(bars[0].close) == "9.19"
    assert events[0].status == "ready"
    assert events[0].metadata == {
        "field_count": 8,
        "latest_trade_date": "2026-07-13",
        "row_count": 1,
        "validation": "schema_ohlc_unique_dates",
    }


def test_baidu_history_rejects_missing_required_keys() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01",
        keys=KEYS[:-1],
    )

    events = []
    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="missing required keys"):
            BaiduHistorySource(client, observer=events.append).fetch_daily("600000", 20)
    assert events[0].status == "error"
    assert events[0].error_code == "DataSourceUnavailable"


def test_baidu_history_treats_null_result_as_unavailable() -> None:
    events = []
    with baidu_client({"ResultCode": "0", "Result": None}) as client:
        with pytest.raises(DataSourceUnavailable, match="no daily bars"):
            BaiduHistorySource(client, observer=events.append).fetch_daily(
                "000003",
                20,
            )

    assert events[0].status == "error"
    assert events[0].error_code == "DataSourceUnavailable"


def test_baidu_history_rejects_truncated_rows() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01"
    )

    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="row width"):
            BaiduHistorySource(client).fetch_daily("600000", 20)


def test_baidu_history_rejects_duplicate_dates() -> None:
    row = (
        "1783872000,2026-07-13,9.04,9.19,75761962,"
        "9.21,9.01,693325381.00"
    )
    payload = market_payload(row, row)

    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="duplicate trade date"):
            BaiduHistorySource(client).fetch_daily("600000", 20)


def test_baidu_history_rejects_entire_batch_when_later_ohlc_is_invalid() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01,693325381.00",
        "1783958400,2026-07-14,9.20,9.30,1000,9.10,9.00,9000.00",
    )

    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="invalid OHLC bounds"):
            BaiduHistorySource(client).fetch_daily("600000", 20)
