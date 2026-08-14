import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qibao_api.gongbu.sector_fund_flow import (
    EastmoneySectorFundFlowSource,
    SectorFundFlowHttpResponse,
    SectorFundFlowRepository,
)


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
                {"f12": "BK1036", "f14": "人工智能", "f62": 2380000000, "f66": 1300000000, "f72": 1080000000},
                {"f12": "BK0475", "f14": "银行", "f62": -960000000, "f66": -420000000, "f72": -540000000},
            ],
        },
    }


@pytest.mark.asyncio
async def test_source_parses_real_sector_net_flow_fields_without_turnover_proxy() -> None:
    async def transport(_url, params, _headers):
        assert "f62" in params["fields"]
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
    assert snapshot.items[1].main_net_yi == Decimal("-9.60")
    assert snapshot.source == "eastmoney-sector-fund-flow"


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
