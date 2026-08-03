import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    EvidenceCitation,
    NewsArticle,
    NormalizedNewsEvent,
)
from qibao_api.gongbu.news_collection import deduplicate_articles


CHINA_TZ = timezone(timedelta(hours=8))
TONGHUASHUN_HOTSPOT_URL = (
    "http://zx.10jqka.com.cn/event/api/getharden/date/{trading_date}/"
    "orderby/date/orderway/desc/charset/GBK/"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36"
)
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class HotspotObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_record_id: str = Field(min_length=1)
    symbol: str
    name: str = Field(min_length=1)
    trading_date: date
    themes: tuple[str, ...] = Field(min_length=1)
    observed_at: AwareDatetime
    fetched_at: AwareDatetime
    source: Literal["tonghuashun-hotspot"] = "tonghuashun-hotspot"
    raw_snapshot: bytes = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return validate_a_share_code(value)


class HotspotSyncResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    fetched: int = Field(ge=0)
    inserted: int = Field(ge=0)
    clusters: int = Field(ge=0)
    events: int = Field(ge=0)


def parse_tonghuashun_hotspots(
    raw: bytes,
    *,
    trading_date: date,
    fetched_at: datetime,
) -> tuple[HotspotObservation, ...]:
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        raise ValueError("fetched_at must include a timezone")
    payload = _decode_payload(raw)
    error_code = payload.get("errocode", 0)
    if str(error_code) != "0":
        message = str(payload.get("errormsg") or f"upstream error {error_code}")
        raise ValueError(message)
    rows = payload.get("data") or []
    if not isinstance(rows, list):
        raise ValueError("hotspot data must be a list")

    china_fetched_at = fetched_at.astimezone(CHINA_TZ)
    market_close = datetime.combine(trading_date, time(15, 0), tzinfo=CHINA_TZ)
    observed_at = min(china_fetched_at, market_close)
    observations: list[HotspotObservation] = []
    seen_symbols: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("hotspot row must be an object")
        symbol = str(item.get("code") or "").strip()
        validate_a_share_code(symbol)
        if symbol in seen_symbols:
            raise ValueError(f"duplicate symbol in hotspot batch: {symbol}")
        seen_symbols.add(symbol)

        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError(f"hotspot name is empty for {symbol}")
        row_date = str(item.get("date") or "").strip()
        if row_date != trading_date.isoformat():
            raise ValueError(
                f"hotspot trading date mismatch for {symbol}: {row_date}"
            )
        themes = tuple(
            dict.fromkeys(
                theme
                for part in str(item.get("reason") or "").split("+")
                if (theme := part.strip())
            )
        )
        if not themes:
            raise ValueError(f"hotspot themes are empty for {symbol}")
        row_raw = json.dumps(
            item,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        observations.append(
            HotspotObservation(
                source_record_id=str(item.get("id") or symbol),
                symbol=symbol,
                name=name,
                trading_date=trading_date,
                themes=themes,
                observed_at=observed_at,
                fetched_at=fetched_at,
                raw_snapshot=row_raw,
            )
        )
    return tuple(observations)


def _decode_payload(raw: bytes) -> dict:
    errors: list[Exception] = []
    for encoding in ("utf-8-sig", "gbk"):
        try:
            value = json.loads(raw.decode(encoding, errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(error)
            continue
        if not isinstance(value, dict):
            raise ValueError("hotspot response must be a JSON object")
        return value
    raise ValueError("hotspot response is not valid UTF-8-SIG or GBK JSON") from errors[-1]


class TonghuashunHotspotSource:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def fetch(
        self,
        trading_date: date,
        *,
        fetched_at: datetime,
    ) -> tuple[HotspotObservation, ...]:
        url = TONGHUASHUN_HOTSPOT_URL.format(
            trading_date=trading_date.isoformat()
        )
        response: httpx.Response | None = None
        for attempt in range(2):
            try:
                response = self.client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
            except httpx.TransportError:
                if attempt == 1:
                    raise
                continue
            if response.status_code not in _TRANSIENT_STATUS_CODES:
                break
            if attempt == 1:
                raise OSError(
                    f"Tonghuashun hotspot status {response.status_code}"
                )
        if response is None:
            raise OSError("Tonghuashun hotspot response is unavailable")
        if response.status_code != 200:
            raise OSError(f"Tonghuashun hotspot status {response.status_code}")
        return parse_tonghuashun_hotspots(
            response.content,
            trading_date=trading_date,
            fetched_at=fetched_at,
        )


class HotspotIngestionService:
    def __init__(self, source, repository, compliance) -> None:
        self.source = source
        self.repository = repository
        self.compliance = compliance

    def sync(
        self,
        trading_date: date,
        *,
        fetched_at: datetime,
    ) -> HotspotSyncResult:
        self.compliance.require_feature_sources(
            "market_hotspots", AssetKind.A_SHARE
        )
        observations = self.source.fetch(trading_date, fetched_at=fetched_at)
        articles = tuple(_article_from_observation(item) for item in observations)
        clusters = deduplicate_articles(list(articles))
        inserted = self.repository.append_articles(articles)
        for cluster in clusters:
            self.repository.append_cluster(cluster)

        stored_articles = {
            article.article_id: article
            for article in self.repository.articles_by_ids(
                tuple(article.article_id for article in articles)
            )
        }
        events = 0
        for observation, candidate in zip(observations, articles, strict=True):
            article = stored_articles[candidate.article_id]
            event = _event_from_observation(observation, article)
            event_inserted, _ = self.repository.reconcile_event(event)
            events += int(event_inserted)
        return HotspotSyncResult(
            fetched=len(observations),
            inserted=inserted,
            clusters=len(clusters),
            events=events,
        )


def _semantic_digest(observation: HotspotObservation) -> str:
    semantic = json.dumps(
        {
            "name": observation.name,
            "symbol": observation.symbol,
            "themes": observation.themes,
            "trading_date": observation.trading_date.isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(semantic).hexdigest()


def _article_from_observation(observation: HotspotObservation) -> NewsArticle:
    digest = _semantic_digest(observation)
    article_id = (
        f"tonghuashun-hotspot-{observation.trading_date.isoformat()}-"
        f"{observation.symbol}-{digest[:16]}"
    )
    themes_text = "+".join(observation.themes)
    return NewsArticle(
        article_id=article_id,
        canonical_url=(
            TONGHUASHUN_HOTSPOT_URL.format(
                trading_date=observation.trading_date.isoformat()
            )
            + f"#{observation.source_record_id}-{observation.symbol}"
        ),
        publisher="同花顺",
        title=f"{observation.symbol} {observation.name} 题材热点：{themes_text}",
        summary=themes_text,
        published_at=observation.observed_at,
        fetched_at=observation.fetched_at,
        content_hash=digest,
        raw_snapshot=observation.raw_snapshot,
        source_verified=True,
    )


def _event_from_observation(
    observation: HotspotObservation,
    article: NewsArticle,
) -> NormalizedNewsEvent:
    digest = _semantic_digest(observation)
    citation = EvidenceCitation(
        citation_id=f"citation-{article.article_id}",
        article_id=article.article_id,
        canonical_url=article.canonical_url,
        publisher=article.publisher,
        published_at=article.published_at,
        quoted_text="+".join(observation.themes),
        content_hash=article.content_hash,
    )
    return NormalizedNewsEvent(
        event_id=(
            f"market-hotspot-{observation.trading_date.isoformat()}-"
            f"{observation.symbol}-{digest[:16]}"
        ),
        event_type="market_hotspot",
        headline=article.title,
        occurred_at=article.published_at,
        normalized_at=article.fetched_at,
        affected_instruments=((AssetKind.A_SHARE, observation.symbol),),
        themes=observation.themes,
        citations=(citation,),
        association_confidence=Decimal("1"),
        review_state="verified",
    )
