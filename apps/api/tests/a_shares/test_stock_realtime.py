from datetime import datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.stock_realtime import StockRealtimeQuoteService
from qibao_api.gongbu.tencent_quotes import TencentMarketSnapshot


NOW = datetime(2026, 9, 3, 2, 30, tzinfo=timezone.utc)


def quote(symbol: str = "600519", price: str = "1500") -> TencentMarketSnapshot:
    return TencentMarketSnapshot(
        symbol=symbol,
        name="贵州茅台",
        price=Decimal(price),
        previous_close=Decimal("1490"),
        volume=Decimal("100"),
        observed_at=NOW,
        turnover_rate=Decimal("1.2"),
        market_cap_yi=Decimal("18000"),
        source="tencent",
    )


class Source:
    def __init__(self):
        self.calls = 0
        self.fail = False

    async def fetch_snapshots(self, symbols):
        self.calls += 1
        if self.fail:
            raise RuntimeError("upstream unavailable")
        return tuple(quote(symbol) for symbol in symbols)


@pytest.mark.asyncio
async def test_refresh_uses_one_shared_batch_and_cache():
    source = Source()
    service = StockRealtimeQuoteService(source, clock=lambda: NOW)
    await service.watch("600519")
    await service.watch("600519")
    await service.refresh_once()
    await service.refresh_once()
    assert source.calls == 2
    result = service.snapshot("600519")
    assert result.status == "ready"
    assert result.price == Decimal("1500")


@pytest.mark.asyncio
async def test_upstream_failure_keeps_last_quote_as_stale():
    source = Source()
    service = StockRealtimeQuoteService(source, stale_after_seconds=3, clock=lambda: NOW)
    await service.watch("600519")
    await service.refresh_once()
    source.fail = True
    await service.refresh_once()
    result = service.snapshot("600519")
    assert result.status == "stale"
    assert result.freshness == "stale"
    assert result.reason == "行情源暂不可用，保留最近一次有效快照"


@pytest.mark.asyncio
async def test_missing_quote_is_explicitly_unavailable():
    class EmptySource:
        async def fetch_snapshots(self, symbols):
            raise RuntimeError("no data")

    source = EmptySource()
    service = StockRealtimeQuoteService(source, clock=lambda: NOW)
    await service.watch("600519")
    await service.refresh_once()
    result = service.snapshot("600519")
    assert result.status == "unavailable"
    assert result.reason
