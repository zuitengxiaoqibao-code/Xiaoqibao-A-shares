import json
from datetime import UTC, datetime

import pytest

from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_collection import NewsHttpResponse
from qibao_api.gongbu.stock_news_sources import (
    CninfoAnnouncementSource,
    CompositeStockNewsSource,
    TencentStockNewsSource,
)


NOW = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_tencent_stock_news_uses_market_symbol_and_preserves_evidence() -> None:
    requests = []

    async def transport(method, url, values, headers):
        requests.append((method, url, values, headers))
        raw = json.dumps({
            "code": 0,
            "msg": "success",
            "data": {"news": [{
                "title": "白酒板块成交活跃",
                "url": (
                    "https://gu.qq.com/resources/shy/news/detail-v2/"
                    "index.html#/index?id=verified-news"
                ),
                "pub_time": "2026-07-30 16:23:00",
            }]},
        }, ensure_ascii=False).encode("utf-8")
        return NewsHttpResponse(200, raw)

    source = TencentStockNewsSource(transport=transport, clock=lambda: NOW)
    articles = await source.fetch("600519", page_size=10)

    assert len(articles) == 1
    assert articles[0].publisher == "腾讯财经"
    assert articles[0].title == "白酒板块成交活跃"
    assert articles[0].published_at.isoformat() == "2026-07-30T16:23:00+08:00"
    assert articles[0].source_verified is True
    assert requests[0][0] == "GET"
    assert requests[0][2] == {"symbol": "sh600519", "page": "1", "num": "10"}


@pytest.mark.asyncio
async def test_cninfo_announcements_use_dynamic_org_id_and_official_pdf() -> None:
    requests = []

    async def transport(method, url, values, headers):
        requests.append((method, url, values, headers))
        if method == "GET":
            raw = json.dumps({"stockList": [{
                "code": "601318",
                "orgId": "9900002221",
                "zwjc": "中国平安",
            }]}, ensure_ascii=False).encode("utf-8")
            return NewsHttpResponse(200, raw)
        raw = json.dumps({"announcements": [{
            "announcementId": "1225431263",
            "announcementTitle": "中国平安重大事项公告",
            "announcementTime": 1784304000000,
            "adjunctUrl": "finalpage/2026-07-18/1225431263.PDF",
            "announcementTypeName": "重大事项",
        }]}, ensure_ascii=False).encode("utf-8")
        return NewsHttpResponse(200, raw)

    source = CninfoAnnouncementSource(transport=transport, clock=lambda: NOW)
    articles = await source.fetch("601318", page_size=20)

    assert len(articles) == 1
    assert articles[0].publisher == "巨潮资讯"
    assert articles[0].summary == "重大事项"
    assert articles[0].canonical_url == (
        "https://static.cninfo.com.cn/finalpage/2026-07-18/1225431263.PDF"
    )
    assert articles[0].source_verified is True
    assert requests[1][0] == "POST"
    assert requests[1][2]["stock"] == "601318,9900002221"


def _article(article_id: str, title: str, url: str) -> NewsArticle:
    import hashlib

    content_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
    return NewsArticle(
        article_id=article_id,
        canonical_url=url,
        publisher="测试来源",
        title=title,
        published_at=datetime(2026, 7, 30, 8, 0, tzinfo=UTC),
        fetched_at=NOW,
        content_hash=content_hash,
        raw_snapshot=title.encode("utf-8"),
        source_verified=True,
    )


@pytest.mark.asyncio
async def test_composite_stock_news_isolates_failures_and_removes_exact_duplicates() -> None:
    duplicate = _article("same", "同一条已核验新闻", "https://news.example/same")

    class FailedSource:
        source_name = "failed"

        async def fetch(self, _symbol, page_size=20):
            raise OSError("temporary failure")

    class WorkingSource:
        source_name = "working"

        async def fetch(self, _symbol, page_size=20):
            return [
                duplicate,
                duplicate,
                _article("newer", "另一条真实新闻", "https://news.example/newer"),
            ]

    source = CompositeStockNewsSource((FailedSource(), WorkingSource()))
    articles = await source.fetch("600519")

    assert [article.article_id for article in articles] == ["same", "newer"]
    assert source.last_successful_sources == ("working",)
    assert source.last_failures == ("failed: temporary failure",)


@pytest.mark.asyncio
async def test_composite_stock_news_raises_when_every_source_fails() -> None:
    class FailedSource:
        def __init__(self, source_name):
            self.source_name = source_name

        async def fetch(self, _symbol, page_size=20):
            raise OSError(f"{self.source_name} unavailable")

    source = CompositeStockNewsSource((FailedSource("tencent"), FailedSource("cninfo")))

    with pytest.raises(OSError, match="all stock news sources failed"):
        await source.fetch("600519")
    assert source.last_successful_sources == ()
    assert len(source.last_failures) == 2
