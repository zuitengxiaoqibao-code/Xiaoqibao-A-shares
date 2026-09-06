from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from qibao_api.gongbu.research_enrichment import (
    EastmoneyResearchEnrichmentSource,
    ResearchEnrichmentRepository,
)


NOW = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_research_enrichment_parses_reports_eps_unlock_margin_and_holders(tmp_path: Path) -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        if "reportapi" in str(request.url):
            calls.append(f"report:{query['qType']}")
            row = {
                "infoCode": f"r-{query['qType']}", "title": "真实研报", "publishDate": "2026-08-08",
                "orgSName": "测试机构", "emRatingName": "增持", "indvInduName": "软件开发",
                "indvInduCode": "1238", "predictThisYearEps": "1.2",
                "predictNextYearEps": "1.5", "predictNextTwoYearEps": "1.8",
            }
            return httpx.Response(200, json={"data": [row]})
        if "stock/get" in str(request.url):
            calls.append("stock-info")
            return httpx.Response(200, json={"data": {"f57": "600001", "f127": "软件开发"}})
        if "slist/get" in str(request.url):
            calls.append("stock-blocks")
            return httpx.Response(200, json={"data": {"diff": [
                {"f12": "BK0737", "f14": "软件开发"},
                {"f12": "BK0816", "f14": "人工智能"},
            ]}})
        if "clist/get" in str(request.url):
            calls.append("industry-peers")
            return httpx.Response(200, json={"data": {"diff": [
                {"f12": "600001", "f14": "测试股份", "f2": "20", "f3": "1.2", "f9": "25", "f20": "12000000000", "f23": "3.2"},
                {"f12": "600002", "f14": "同行甲", "f2": "18", "f3": "-0.5", "f9": "30", "f20": "9000000000", "f23": "2.8"},
                {"f12": "300001", "f14": "同行乙", "f2": "32", "f3": "2.1", "f9": "40", "f20": "18000000000", "f23": "4.1"},
            ]}})
        report = query["reportName"]
        calls.append(report)
        rows = {
            "RPT_LIFT_STAGE": [{"FREE_DATE": "2026-09-01", "FREE_SHARES_NUM": 1000, "FREE_RATIO": 2.5}],
            "RPTA_WEB_RZRQ_GGMX": [{"DATE": "2026-08-08", "RZYE": 2000, "RZMRE": 300, "RQYE": 20, "RZRQYE": 2020}],
            "RPT_HOLDERNUMLATEST": [{"END_DATE": "2026-06-30", "HOLDER_NUM": 50000, "HOLDER_NUM_RATIO": -3.2, "AVG_FREE_SHARES": 1200}],
        }[report]
        return httpx.Response(200, json={"result": {"data": rows}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = EastmoneyResearchEnrichmentSource(
            client, clock=lambda: NOW, minimum_interval=0,
        )
        snapshot = await source.fetch("600001")

    assert calls == [
        "report:0", "report:1", "stock-info", "stock-blocks", "industry-peers",
        "RPT_LIFT_STAGE", "RPTA_WEB_RZRQ_GGMX", "RPT_HOLDERNUMLATEST",
    ]
    assert snapshot.stock_reports[0].eps_next_year == 1.5
    assert snapshot.industry_reports[0].industry == "软件开发"
    assert snapshot.industry_name == "软件开发"
    assert snapshot.industry_board_code == "BK0737"
    assert snapshot.peer_candidates[1].symbol == "600002"
    assert snapshot.peer_candidates[1].industry == "计算机"
    assert snapshot.peer_candidates[1].pe_ttm == 30
    assert snapshot.unlocks[0].ratio_percent == 2.5
    assert snapshot.margin[0].financing_balance == 2000
    assert snapshot.holders[0].change_ratio_percent == Decimal("-3.2")

    repository = ResearchEnrichmentRepository(tmp_path / "research.sqlite3")
    repository.append(snapshot)
    assert repository.latest("600001") == snapshot
    repository.close()


@pytest.mark.asyncio
async def test_research_enrichment_keeps_reports_when_peer_lookup_is_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        if "reportapi" in str(request.url):
            return httpx.Response(200, json={"data": [{
                "infoCode": "r1", "title": "公司研报", "publishDate": "2026-08-08",
                "orgSName": "测试机构", "indvInduName": "软件开发",
                "indvInduCode": "1238", "predictNextYearEps": "1.5",
            }]})
        if "stock/get" in str(request.url):
            return httpx.Response(503, json={"error": "temporary"})
        rows = {
            "RPT_LIFT_STAGE": [],
            "RPTA_WEB_RZRQ_GGMX": [],
            "RPT_HOLDERNUMLATEST": [],
        }[query["reportName"]]
        return httpx.Response(200, json={"result": {"data": rows}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = EastmoneyResearchEnrichmentSource(client, clock=lambda: NOW, minimum_interval=0)
        snapshot = await source.fetch("600001")

    assert snapshot.stock_reports[0].title == "公司研报"
    assert snapshot.peer_candidates == ()
    assert "industry_peer_lookup_unavailable" in snapshot.warnings


@pytest.mark.asyncio
async def test_research_enrichment_does_not_promote_unmapped_board_members_to_peers() -> None:
    """Unknown data-source industries must stay evidence, not formal peers."""

    async def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        if "reportapi" in str(request.url):
            return httpx.Response(200, json={"data": [{
                "infoCode": "r-unmapped", "title": "公司研报", "publishDate": "2026-08-08",
                "orgSName": "测试机构", "indvInduName": "未收录行业",
                "indvInduCode": "UNMAPPED-1",
            }]})
        if "stock/get" in str(request.url):
            return httpx.Response(200, json={"data": {"f57": "600009", "f127": "未收录行业"}})
        if "slist/get" in str(request.url):
            return httpx.Response(200, json={"data": {"diff": [
                {"f12": "BK9999", "f14": "未收录行业"},
            ]}})
        if "clist/get" in str(request.url):
            return httpx.Response(200, json={"data": {"diff": [
                {"f12": "600010", "f14": "候选公司", "f2": "10", "f3": "1", "f9": "20", "f20": "1000000000", "f23": "2"},
            ]}})
        rows = {
            "RPT_LIFT_STAGE": [],
            "RPTA_WEB_RZRQ_GGMX": [],
            "RPT_HOLDERNUMLATEST": [],
        }[query["reportName"]]
        return httpx.Response(200, json={"result": {"data": rows}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = EastmoneyResearchEnrichmentSource(client, clock=lambda: NOW, minimum_interval=0)
        snapshot = await source.fetch("600009")

    assert snapshot.shenwan_industry is None
    assert snapshot.shenwan_mapping_status == "unmapped"
    assert snapshot.peer_candidates == ()
    assert "industry_peer_mapping_unverified" in snapshot.warnings
