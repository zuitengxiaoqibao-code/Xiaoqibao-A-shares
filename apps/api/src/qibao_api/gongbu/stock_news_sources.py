import hashlib
import html
import json
import re
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_collection import NewsHttpResponse, USER_AGENT


TENCENT_STOCK_NEWS_URL = (
    "https://proxy.finance.qq.com/ifzqgtimg/appstock/news/HyNews/getBySymbol"
)
CNINFO_ORG_MAP_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_ANNOUNCEMENT_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CHINA_TZ = timezone(timedelta(hours=8))

StockNewsTransport = Callable[
    [str, str, dict[str, str], dict[str, str]], Awaitable[NewsHttpResponse]
]


def _market_symbol(symbol: str) -> str:
    if symbol.startswith("6"):
        return f"sh{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return f"sz{symbol}"


def _plain_text(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _semantic_identity(
    *, title: str, summary: str | None, published_at: datetime, url: str, publisher: str
) -> tuple[str, bytes]:
    snapshot = json.dumps(
        {
            "published_at": published_at.isoformat(),
            "publisher": publisher,
            "summary": summary,
            "title": title,
            "url": url,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(snapshot).hexdigest(), snapshot


def _verified_host(url: str, allowed: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == item or host.endswith(f".{item}") for item in allowed)


class TencentStockNewsSource:
    source_name = "tencent-stock-news"

    def __init__(
        self,
        transport: StockNewsTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock

    async def fetch(self, symbol: str, page_size: int = 20) -> list[NewsArticle]:
        symbol = validate_a_share_code(symbol)
        if not 1 <= page_size <= 50:
            raise ValueError("page_size must be between 1 and 50")
        market_symbol = _market_symbol(symbol)
        values = {"symbol": market_symbol, "page": "1", "num": str(page_size)}
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": f"https://gu.qq.com/{market_symbol}/gp/hyxw",
        }
        response = await self._request("GET", TENCENT_STOCK_NEWS_URL, values, headers)
        if response.status_code != 200:
            raise OSError(f"Tencent stock news status {response.status_code}")
        return self._parse(response.body)

    async def _request(
        self, method: str, url: str, values: dict[str, str], headers: dict[str, str]
    ) -> NewsHttpResponse:
        if self.transport is not None:
            return await self.transport(method, url, values, headers)
        if self.client is not None:
            result = await self.client.get(url, params=values, headers=headers, timeout=12)
            return NewsHttpResponse(result.status_code, result.content)
        async with httpx.AsyncClient(timeout=12) as client:
            result = await client.get(url, params=values, headers=headers)
            return NewsHttpResponse(result.status_code, result.content)

    def _parse(self, raw: bytes) -> list[NewsArticle]:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Tencent stock news response is not valid JSON") from error
        if str(payload.get("code")) != "0":
            raise OSError(str(payload.get("msg") or "Tencent stock news request failed"))
        rows = (payload.get("data") or {}).get("news") or []
        if not isinstance(rows, list):
            raise ValueError("Tencent stock news rows are invalid")
        fetched_at = self.clock()
        articles: list[NewsArticle] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = _plain_text(row.get("title"))
            url = str(row.get("url") or "").strip()
            published = row.get("pub_time") or row.get("publish_time") or row.get("time")
            if not title or not url or not published:
                continue
            try:
                published_at = datetime.fromisoformat(str(published))
            except ValueError:
                continue
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=CHINA_TZ)
            summary = _plain_text(row.get("summary") or row.get("digest")) or None
            content_hash, _ = _semantic_identity(
                title=title,
                summary=summary,
                published_at=published_at,
                url=url,
                publisher="腾讯财经",
            )
            provider_match = re.search(r"(?:[?&]|#.*[?&])id=([A-Za-z0-9_-]+)", url)
            provider_id = provider_match.group(1) if provider_match else content_hash[:16]
            row_raw = json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            articles.append(NewsArticle(
                article_id=f"tencent-{provider_id}-{content_hash[:12]}",
                canonical_url=url,
                publisher="腾讯财经",
                title=title,
                summary=summary,
                published_at=published_at,
                fetched_at=fetched_at,
                content_hash=content_hash,
                raw_snapshot=row_raw,
                source_verified=_verified_host(url, ("qq.com",)),
            ))
        if rows and not articles:
            raise ValueError("Tencent stock news rows contain no verifiable articles")
        return articles


class CninfoAnnouncementSource:
    source_name = "cninfo-announcements"

    def __init__(
        self,
        transport: StockNewsTransport | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.transport = transport
        self.client = client
        self.clock = clock
        self._org_ids: dict[str, str] | None = None

    async def fetch(self, symbol: str, page_size: int = 20) -> list[NewsArticle]:
        symbol = validate_a_share_code(symbol)
        if not 1 <= page_size <= 50:
            raise ValueError("page_size must be between 1 and 50")
        org_id = await self._org_id(symbol)
        values = {
            "stock": f"{symbol},{org_id}",
            "tabName": "fulltext",
            "pageSize": str(page_size),
            "pageNum": "1",
            "column": "",
            "category": "",
            "plate": "",
            "seDate": "",
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.cninfo.com.cn/new/disclosure",
            "Origin": "https://www.cninfo.com.cn",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = await self._request("POST", CNINFO_ANNOUNCEMENT_URL, values, headers)
        if response.status_code != 200:
            raise OSError(f"CNINFO announcement status {response.status_code}")
        return self._parse(response.body)

    async def _org_id(self, symbol: str) -> str:
        if self._org_ids is None:
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch",
            }
            response = await self._request("GET", CNINFO_ORG_MAP_URL, {}, headers)
            if response.status_code != 200:
                raise OSError(f"CNINFO organization map status {response.status_code}")
            try:
                payload = json.loads(response.body)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("CNINFO organization map is not valid JSON") from error
            rows = payload.get("stockList") or []
            if not isinstance(rows, list):
                raise ValueError("CNINFO organization map rows are invalid")
            self._org_ids = {
                str(row.get("code")): str(row.get("orgId"))
                for row in rows
                if isinstance(row, dict) and row.get("code") and row.get("orgId")
            }
        org_id = self._org_ids.get(symbol)
        if org_id:
            return org_id
        if symbol.startswith("6"):
            return f"gssh0{symbol}"
        if symbol.startswith(("4", "8")):
            return f"gsbj0{symbol}"
        return f"gssz0{symbol}"

    async def _request(
        self, method: str, url: str, values: dict[str, str], headers: dict[str, str]
    ) -> NewsHttpResponse:
        if self.transport is not None:
            return await self.transport(method, url, values, headers)
        if self.client is not None:
            if method == "POST":
                result = await self.client.post(url, data=values, headers=headers, timeout=15)
            else:
                result = await self.client.get(url, params=values, headers=headers, timeout=15)
            return NewsHttpResponse(result.status_code, result.content)
        async with httpx.AsyncClient(timeout=15) as client:
            if method == "POST":
                result = await client.post(url, data=values, headers=headers)
            else:
                result = await client.get(url, params=values, headers=headers)
            return NewsHttpResponse(result.status_code, result.content)

    def _parse(self, raw: bytes) -> list[NewsArticle]:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("CNINFO announcement response is not valid JSON") from error
        rows = payload.get("announcements") or []
        if not isinstance(rows, list):
            raise ValueError("CNINFO announcement rows are invalid")
        fetched_at = self.clock()
        articles: list[NewsArticle] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = _plain_text(row.get("announcementTitle"))
            announcement_id = str(row.get("announcementId") or "").strip()
            timestamp = row.get("announcementTime")
            if not title or not announcement_id or timestamp is None:
                continue
            try:
                if isinstance(timestamp, (int, float)):
                    published_at = datetime.fromtimestamp(timestamp / 1000, tz=CHINA_TZ)
                else:
                    published_at = datetime.fromisoformat(str(timestamp))
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=CHINA_TZ)
            except (ValueError, OSError, OverflowError):
                continue
            adjunct_url = str(row.get("adjunctUrl") or "").strip().lstrip("/")
            url = (
                f"https://static.cninfo.com.cn/{adjunct_url}"
                if adjunct_url
                else (
                    "https://www.cninfo.com.cn/new/disclosure/detail"
                    f"?annoId={announcement_id}"
                )
            )
            summary = _plain_text(
                row.get("announcementTypeName") or row.get("categoryName")
            ) or None
            content_hash, _ = _semantic_identity(
                title=title,
                summary=summary,
                published_at=published_at,
                url=url,
                publisher="巨潮资讯",
            )
            row_raw = json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            articles.append(NewsArticle(
                article_id=f"cninfo-{announcement_id}-{content_hash[:12]}",
                canonical_url=url,
                publisher="巨潮资讯",
                title=title,
                summary=summary,
                published_at=published_at,
                fetched_at=fetched_at,
                content_hash=content_hash,
                raw_snapshot=row_raw,
                source_verified=_verified_host(url, ("cninfo.com.cn",)),
            ))
        if rows and not articles:
            raise ValueError("CNINFO announcement rows contain no verifiable articles")
        return articles


class CompositeStockNewsSource:
    source_name = "composite-stock-news"

    def __init__(self, sources: Sequence[object]) -> None:
        if not sources:
            raise ValueError("at least one stock news source is required")
        self.sources = tuple(sources)
        self.last_successful_sources: tuple[str, ...] = ()
        self.last_failures: tuple[str, ...] = ()

    async def fetch(self, symbol: str, page_size: int = 20) -> list[NewsArticle]:
        symbol = validate_a_share_code(symbol)
        successful: list[str] = []
        failures: list[str] = []
        merged: list[NewsArticle] = []
        for source in self.sources:
            name = str(getattr(source, "source_name", source.__class__.__name__))
            try:
                articles = await source.fetch(symbol, page_size=page_size)
            except (OSError, ValueError, httpx.HTTPError) as error:
                failures.append(f"{name}: {error}")
                continue
            successful.append(name)
            merged.extend(articles)
        self.last_successful_sources = tuple(successful)
        self.last_failures = tuple(failures)
        if not successful:
            raise OSError(f"all stock news sources failed: {'; '.join(failures)}")

        unique: list[NewsArticle] = []
        identities: set[tuple[str, str, str]] = set()
        for article in merged:
            identity = (
                article.article_id,
                article.canonical_url,
                article.content_hash,
            )
            if identity in identities:
                continue
            identities.add(identity)
            unique.append(article)
        return unique
