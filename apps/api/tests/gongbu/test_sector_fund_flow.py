import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import httpx

from qibao_api.gongbu.sector_fund_flow import (
    EASTMONEY_SECTOR_FLOW_FALLBACK_URL,
    EASTMONEY_SECTOR_FLOW_URL,
    EastmoneySectorFundFlowSource,
    SectorFundFlowHttpResponse,
    SectorFundFlowRepository,
    SectorFundFlowService,
)
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus


NOW = datetime(2026, 8, 10, 2, 30, tzinfo=timezone.utc)


def response(payload: dict, status_code: int = 200) -> SectorFundFlowHttpResponse:
    return SectorFundFlowHttpResponse(
        status_code=status_code,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )


def payload() -> dict:
    return {
        "data": {
            "diff": [
                {"f12": "BK1036", "f14": "人工智能", "f3": 2.36, "f6": 38800000000, "f62": 2380000000, "f66": 1300000000, "f72": 1080000000, "f104": 71, "f105": 9},
                {"f12": "BK0475", "f14": "银行", "f3": -0.82, "f6": 12600000000, "f62": -960000000, "f66": -420000000, "f72": -540000000, "f104": 8, "f105": 34},
            ],
        },
    }


@pytest.mark.asyncio
async def test_source_parses_real_sector_net_flow_fields_without_turnover_proxy() -> None:
    async def transport(_url, params, _headers):
        assert "f62" in params["fields"]
        assert "f104" in params["fields"]
        assert params["fid"] == "f62"
        return response(payload())

    snapshot = await EastmoneySectorFundFlowSource(
        transport=transport,
        clock=lambda: NOW,
        minimum_interval=0,
    ).fetch()

    assert len(snapshot.items) == 2
    assert snapshot.items[0].sector_code == "BK1036"
    assert snapshot.items[0].main_net_yi == Decimal("23.80")
    assert snapshot.items[0].large_net_yi == Decimal("10.80")
    assert snapshot.items[0].super_net_yi == Decimal("13.00")
    assert snapshot.items[0].change_percent == Decimal("2.36")
    assert snapshot.items[0].amount_yi == Decimal("388.00")
    assert snapshot.items[0].rising_count == 71
    assert snapshot.items[0].falling_count == 9
    assert snapshot.items[1].main_net_yi == Decimal("-9.60")
    assert snapshot.source == "eastmoney-sector-fund-flow"


@pytest.mark.asyncio
async def test_source_fetches_opposite_sort_when_first_page_hides_outflows() -> None:
    positive_payload = {
        "data": {"diff": [
            {"f12": "BK0001", "f14": "流入板块", "f3": 1, "f6": 100000000, "f62": 10000000},
        ]},
    }
    outflow_payload = {
        "data": {"diff": [
            {"f12": "BK0002", "f14": "流出板块", "f3": -2, "f6": 80000000, "f62": -20000000},
        ]},
    }
    calls: list[str] = []

    async def transport(_url, params, _headers):
        calls.append(params["po"])
        return response(positive_payload if len(calls) == 1 else outflow_payload)

    snapshot = await EastmoneySectorFundFlowSource(transport=transport, clock=lambda: NOW, minimum_interval=0).fetch()

    assert calls == ["1", "0"]
    assert {item.sector_code for item in snapshot.items} == {"BK0001", "BK0002"}
    assert next(item for item in snapshot.items if item.sector_code == "BK0002").main_net_yi == Decimal("-0.20")


@pytest.mark.asyncio
async def test_source_switches_host_when_primary_endpoint_disconnects(monkeypatch) -> None:
    attempts: list[dict] = []
    urls: list[str] = []

    class Client:
        def __init__(self, **kwargs):
            attempts.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **_kwargs):
            urls.append(url)
            if len(attempts) == 1:
                raise httpx.RemoteProtocolError("proxy disconnected")
            return httpx.Response(200, content=response(payload()).body)

    monkeypatch.setattr(httpx, "AsyncClient", Client)

    snapshot = await EastmoneySectorFundFlowSource(
        clock=lambda: NOW,
        minimum_interval=0,
    ).fetch()

    assert snapshot.items
    assert attempts == [{"timeout": 15}, {"timeout": 15}]
    assert urls == [EASTMONEY_SECTOR_FLOW_URL, EASTMONEY_SECTOR_FLOW_FALLBACK_URL]


@pytest.mark.asyncio
async def test_source_switches_to_working_sector_endpoint_and_reuses_it(monkeypatch) -> None:
    calls: list[str] = []

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **_kwargs):
            calls.append(url)
            if url == EASTMONEY_SECTOR_FLOW_URL:
                raise httpx.RemoteProtocolError("primary endpoint disconnected")
            return httpx.Response(200, content=response(payload()).body)

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    source = EastmoneySectorFundFlowSource(
        clock=lambda: NOW,
        minimum_interval=0,
    )

    first = await source.fetch()
    second = await source.fetch()

    assert first.items
    assert second.items
    assert calls == [
        EASTMONEY_SECTOR_FLOW_URL,
        EASTMONEY_SECTOR_FLOW_FALLBACK_URL,
        EASTMONEY_SECTOR_FLOW_FALLBACK_URL,
    ]


@pytest.mark.asyncio
async def test_source_rejects_empty_or_non_fund_flow_payloads() -> None:
    async def transport(_url, _params, _headers):
        return response({"data": {"diff": [{"f12": "BK1036", "f14": "人工智能", "f6": 999999}]}})

    with pytest.raises(ValueError, match="net flow"):
        await EastmoneySectorFundFlowSource(
            transport=transport,
            clock=lambda: NOW,
            minimum_interval=0,
        ).fetch()


@pytest.mark.asyncio
async def test_repository_keeps_real_time_series_in_observation_order(tmp_path) -> None:
    payloads = [response(payload()), response(payload())]

    async def transport(_url, _params, _headers):
        return payloads.pop(0)

    source = EastmoneySectorFundFlowSource(
        transport=transport,
        clock=lambda: NOW,
        minimum_interval=0,
    )
    repository = SectorFundFlowRepository(tmp_path / "sector-fund-flow.sqlite3")
    first = await source.fetch()
    source.clock = lambda: NOW + timedelta(minutes=1)
    second = await source.fetch()

    repository.append(first)
    repository.append(second)

    assert repository.latest() == second
    assert repository.history(limit=2) == (first, second)
    assert repository.count() == 2
    repository.close()


@pytest.mark.asyncio
async def test_service_publishes_sector_fund_flow_snapshot(tmp_path) -> None:
    async def transport(_url, _params, _headers):
        return response(payload())

    repository = SectorFundFlowRepository(tmp_path / "sector-fund-flow.sqlite3")
    bus = RealtimeSnapshotBus()
    service = SectorFundFlowService(
        EastmoneySectorFundFlowSource(transport=transport, clock=lambda: NOW, minimum_interval=0),
        repository,
        realtime_snapshot_bus=bus,
    )

    await service.sync()

    event = bus.latest("sector_fund_flow")
    assert event is not None
    assert event["payload"]["items"][0]["sector_code"] == "BK1036"
    repository.close()
