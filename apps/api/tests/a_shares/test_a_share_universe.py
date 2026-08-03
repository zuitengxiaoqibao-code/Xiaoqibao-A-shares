import json
from datetime import datetime, timezone

import pytest

from qibao_api.a_shares.instrument_directory import AShareInstrumentDirectory
from qibao_api.gongbu import a_share_universe as universe_module
from qibao_api.gongbu.a_share_universe import (
    EastmoneyAShareUniverseSource,
    RawUniverseResponse,
    parse_eastmoney_a_share_universe,
)


OBSERVED_AT = datetime(2026, 7, 17, tzinfo=timezone.utc)


def listed_instrument(symbol: str, name: str) -> universe_module.AShareInstrument:
    return universe_module.AShareInstrument(
        symbol=symbol,
        name=name,
        exchange=universe_module.market_prefix(symbol),
        observed_at=OBSERVED_AT,
        quote_quality="unavailable",
    )


def universe_payload() -> bytes:
    return json.dumps(
        {
            "data": {
                "total": 4,
                "diff": {
                    "0": {"f12": "000001", "f13": 0, "f14": "平安银行"},
                    "1": {"f12": "600000", "f13": 1, "f14": "浦发银行"},
                    "2": {"f12": "000300", "f13": 1, "f14": "沪深300"},
                    "3": {"f12": "113065", "f13": 1, "f14": "转债"},
                },
            }
        },
        ensure_ascii=False,
    ).encode("utf-8")


def cninfo_payload() -> bytes:
    return json.dumps(
        {
            "stockList": [
                {"code": "000001", "category": "A股", "zwjc": "平安银行"},
                {"code": "600000", "category": "A股", "zwjc": "浦发银行"},
                {"code": "200002", "category": "B股", "zwjc": "万科B"},
                {"code": "920680", "category": "A股", "zwjc": "广道退"},
                {"code": "113065", "category": "债券", "zwjc": "转债"},
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")


def test_parse_eastmoney_a_share_universe_keeps_equities_only() -> None:
    items = parse_eastmoney_a_share_universe(universe_payload(), observed_at=OBSERVED_AT)

    assert [item.symbol for item in items] == ["000001", "600000"]
    assert [item.name for item in items] == ["平安银行", "浦发银行"]
    assert all(item.quote_quality == "unavailable" for item in items)


def test_parse_cninfo_a_share_universe_keeps_active_equities_only() -> None:
    items = universe_module.parse_cninfo_a_share_universe(
        cninfo_payload(), observed_at=OBSERVED_AT
    )

    assert [item.symbol for item in items] == ["000001", "600000"]
    assert [item.name for item in items] == ["平安银行", "浦发银行"]
    assert all(item.quote_quality == "unavailable" for item in items)


@pytest.mark.asyncio
async def test_cninfo_universe_source_reads_official_stock_list() -> None:
    seen: list[tuple[str, dict[str, str], dict[str, str]]] = []

    async def transport(url, params, headers):
        seen.append((url, params, headers))
        return RawUniverseResponse(200, cninfo_payload())

    source = universe_module.CninfoAShareUniverseSource(
        transport=transport, clock=lambda: OBSERVED_AT
    )

    items = await source.fetch()

    assert [item.symbol for item in items] == ["000001", "600000"]
    assert seen[0][0] == universe_module.CNINFO_A_SHARE_UNIVERSE_URL
    assert seen[0][1] == {}
    assert seen[0][2]["Referer"].startswith("https://www.cninfo.com.cn/")


@pytest.mark.asyncio
async def test_universe_source_fetches_pages_and_rejects_upstream_errors() -> None:
    seen: list[dict[str, str]] = []

    async def transport(_: str, params: dict[str, str], __: dict[str, str]) -> RawUniverseResponse:
        seen.append(params)
        if params["pn"] == "1":
            payload = json.loads(universe_payload())
            payload["data"]["total"] = 6
            return RawUniverseResponse(200, json.dumps(payload, ensure_ascii=False).encode())
        return RawUniverseResponse(200, universe_payload())

    source = EastmoneyAShareUniverseSource(
        transport=transport, clock=lambda: OBSERVED_AT, page_size=4
    )
    items = await source.fetch()

    assert [params["pn"] for params in seen] == ["1", "2"]
    assert [item.symbol for item in items] == ["000001", "600000"]

    async def unavailable(_: str, __: dict[str, str], ___: dict[str, str]) -> RawUniverseResponse:
        return RawUniverseResponse(503, b"unavailable")

    with pytest.raises(ValueError, match="status 503"):
        await EastmoneyAShareUniverseSource(transport=unavailable).fetch()


@pytest.mark.asyncio
async def test_universe_source_falls_back_to_cninfo_without_hiding_total_failure() -> None:
    class BrokenPrimary:
        source_name = "eastmoney-a-share-universe"

        async def fetch(self):
            raise ValueError("primary unavailable")

    class OfficialFallback:
        source_name = "cninfo-a-share-universe"

        async def fetch(self):
            return universe_module.parse_cninfo_a_share_universe(
                cninfo_payload(), observed_at=OBSERVED_AT
            )

    source = universe_module.FallbackAShareUniverseSource(
        BrokenPrimary(), OfficialFallback(), minimum_instrument_count=2
    )

    items = await source.fetch()

    assert [item.symbol for item in items] == ["000001", "600000"]
    assert source.last_source == "cninfo-a-share-universe"

    class BrokenFallback(OfficialFallback):
        async def fetch(self):
            raise ValueError("fallback unavailable")

    broken = universe_module.FallbackAShareUniverseSource(
        BrokenPrimary(), BrokenFallback(), minimum_instrument_count=2
    )
    with pytest.raises(ValueError, match="all A-share universe sources unavailable"):
        await broken.fetch()


@pytest.mark.asyncio
async def test_universe_source_rejects_single_exchange_snapshot_and_uses_fallback() -> None:
    class ShenzhenOnlyPrimary:
        source_name = "eastmoney-a-share-universe"

        async def fetch(self):
            return (
                listed_instrument("000001", "平安银行"),
                listed_instrument("000002", "万科A"),
            )

    class CompleteFallback:
        source_name = "cninfo-a-share-universe"

        async def fetch(self):
            return (
                listed_instrument("000001", "平安银行"),
                listed_instrument("600000", "浦发银行"),
            )

    source = universe_module.FallbackAShareUniverseSource(
        ShenzhenOnlyPrimary(), CompleteFallback(), minimum_instrument_count=2
    )

    items = await source.fetch()

    assert {item.exchange for item in items} == {"sh", "sz"}
    assert source.last_source == "cninfo-a-share-universe"


@pytest.mark.asyncio
async def test_universe_source_rejects_snapshot_below_minimum_count() -> None:
    class TooSmallPrimary:
        source_name = "eastmoney-a-share-universe"

        async def fetch(self):
            return (
                listed_instrument("000001", "平安银行"),
                listed_instrument("600000", "浦发银行"),
            )

    class CompleteFallback:
        source_name = "cninfo-a-share-universe"

        async def fetch(self):
            return (
                listed_instrument("000001", "平安银行"),
                listed_instrument("600000", "浦发银行"),
                listed_instrument("600519", "贵州茅台"),
            )

    source = universe_module.FallbackAShareUniverseSource(
        TooSmallPrimary(), CompleteFallback(), minimum_instrument_count=3
    )

    items = await source.fetch()

    assert len(items) == 3
    assert source.last_source == "cninfo-a-share-universe"


def test_directory_bulk_observation_makes_name_search_available(tmp_path) -> None:
    directory = AShareInstrumentDirectory(tmp_path / "instruments.sqlite3")
    directory.observe_many(parse_eastmoney_a_share_universe(universe_payload(), observed_at=OBSERVED_AT))

    assert [item.symbol for item in directory.search("浦发", 10)] == ["600000"]
    assert directory.resolve("600000").name == "浦发银行"
    directory.close()
