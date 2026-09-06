from datetime import datetime
from decimal import Decimal

import httpx
import pytest

from qibao_api.gongbu.overseas_market import (
    INDEX_SYMBOLS,
    MAG7_SYMBOLS,
    OVERSEAS_INSTRUMENTS,
    TencentOverseasMarketService,
    _market_state,
    parse_tencent_overseas_payload,
)


def _payload(name: str, ticker: str, price: str, previous: str, observed: str, change: str, change_percent: str) -> str:
    fields = [""] * 33
    fields[1] = name
    fields[2] = ticker
    fields[3] = price
    fields[4] = previous
    fields[30] = observed
    fields[31] = change
    fields[32] = change_percent
    return "~".join(fields)


def test_parse_tencent_overseas_payload_uses_gbk_and_source_timestamp() -> None:
    quote = parse_tencent_overseas_payload(
        _payload("苹果", "AAPL", "227.16", "226.01", "20260902160000", "1.15", "0.51"),
        symbol="usAAPL",
    )

    assert quote.name == "苹果"
    assert quote.ticker == "AAPL"
    assert quote.price == Decimal("227.16")
    assert quote.change == Decimal("1.15")
    assert quote.change_percent == Decimal("0.51")
    assert quote.observed_at == datetime.fromisoformat("2026-09-02T16:00:00-04:00")


def test_parse_tencent_overseas_payload_accepts_compact_timestamp() -> None:
    quote = parse_tencent_overseas_payload(
        _payload("苹果", "AAPL", "227.16", "226.01", "20260902160000", "1.15", "0.51"),
        symbol="usAAPL",
    )
    assert quote.observed_at.isoformat() == "2026-09-02T16:00:00-04:00"


def test_market_state_uses_new_york_session_and_observation_date() -> None:
    observed = datetime.fromisoformat("2026-09-04T13:45:00-04:00")
    assert _market_state(observed, datetime.fromisoformat("2026-09-04T14:00:00-04:00"), market="us") == "盘中"
    assert _market_state(observed, datetime.fromisoformat("2026-09-04T17:00:00-04:00"), market="us") == "最近收盘"
    assert _market_state(observed, datetime.fromisoformat("2026-09-05T12:00:00-04:00"), market="us") == "休市中"


def test_market_state_uses_hong_kong_session_and_timezone() -> None:
    observed = datetime.fromisoformat("2026-09-04T10:00:00+08:00")
    assert _market_state(observed, datetime.fromisoformat("2026-09-04T11:00:00+08:00"), market="hk") == "盘中"
    assert _market_state(observed, datetime.fromisoformat("2026-09-04T12:30:00+08:00"), market="hk") == "最近收盘"
    assert _market_state(observed, datetime.fromisoformat("2026-09-05T12:00:00+08:00"), market="hk") == "休市中"


def test_market_state_marks_us_exchange_holiday_as_closed_even_during_session() -> None:
    observed = datetime.fromisoformat("2026-07-03T13:45:00-04:00")

    assert _market_state(
        observed,
        datetime.fromisoformat("2026-07-03T14:00:00-04:00"),
        market="us",
    ) == "休市中"


def test_market_state_marks_hong_kong_exchange_holiday_as_closed_even_during_session() -> None:
    observed = datetime.fromisoformat("2026-10-01T10:45:00+08:00")

    assert _market_state(
        observed,
        datetime.fromisoformat("2026-10-01T11:00:00+08:00"),
        market="hk",
    ) == "休市中"


@pytest.mark.asyncio
async def test_service_fetches_all_overseas_instruments_in_one_request() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        body = "".join(
            f'v_{symbol}="{_payload(symbol, symbol[2:], "100", "99", "20260902160000", "1", "1")}";'
            for symbol in OVERSEAS_INSTRUMENTS
        ).encode("gbk")
        return httpx.Response(200, content=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TencentOverseasMarketService(client, cache_ttl_seconds=0)
        snapshot = await service.current(datetime.fromisoformat("2026-09-02T17:00:00-04:00"))

    assert len(requested) == 1
    assert len(snapshot.indices) == 3
    assert tuple(item.ticker for item in snapshot.mag7) == tuple(item[2] for item in MAG7_SYMBOLS)
    assert tuple(item.ticker for item in snapshot.mag7[-2:]) == ("TSLA", "AVGO")
    assert snapshot.mag7[-1].name == "博通"
    assert snapshot.quality == "ready"
    assert snapshot.trading_label == "美股 2026-09-02 最近收盘"


@pytest.mark.asyncio
async def test_service_keeps_last_good_snapshot_as_stale_on_refresh_failure() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            body = "".join(
                f'v_{symbol}="{_payload(name, ticker, "40000", "39900", "2026-09-02 16:00:00", "1", "0.1")}";'
                for symbol, name, ticker in (*INDEX_SYMBOLS, *MAG7_SYMBOLS)
            ).encode("gbk")
            return httpx.Response(200, content=body)
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TencentOverseasMarketService(client, cache_ttl_seconds=0)
        first = await service.current()
        second = await service.current()

    assert first.quality == "ready"
    assert second.quality == "stale"
    assert second.reason == "腾讯海外行情刷新失败，显示最近一次有效快照"
    assert second.indices[0].price == first.indices[0].price
