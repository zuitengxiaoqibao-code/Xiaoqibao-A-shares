from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.a_shares.event_impact import EventImpactService
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.event_impact import EventImpactWindow
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import EvidenceCitation, NormalizedNewsEvent
from qibao_api.gongbu.news_collection import NewsCluster


UTC = timezone.utc
PUBLISHED = datetime(2026, 8, 4, 2, tzinfo=UTC)


def citation(article_id: str, published_at: datetime) -> EvidenceCitation:
    return EvidenceCitation(
        citation_id=f"citation-{article_id}",
        article_id=article_id,
        canonical_url=f"https://example.com/{article_id}",
        publisher="Verified publisher",
        published_at=published_at,
        quoted_text="Verified source text.",
        content_hash=(article_id[-1] * 64),
    )


def event(*, confidence: str = "0.95") -> NormalizedNewsEvent:
    return NormalizedNewsEvent(
        event_id="event-1",
        event_type="company_announcement",
        headline="Company publishes an announcement",
        occurred_at=PUBLISHED + timedelta(minutes=10),
        normalized_at=PUBLISHED + timedelta(hours=1),
        affected_instruments=((AssetKind.A_SHARE, "600519"),),
        industries=("Beverages",),
        themes=("Consumer",),
        citations=(
            citation("article-b", PUBLISHED + timedelta(minutes=5)),
            citation("article-a", PUBLISHED),
        ),
        association_confidence=Decimal(confidence),
        association_kind="direct",
        association_reasons=("The announcement names the listed company.",),
        review_state="verified",
    )


def bar(day: int, close: str) -> DailyBar:
    price = Decimal(close)
    return DailyBar(
        symbol="600519",
        trade_date=date(2026, 8, day),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1,
        amount=price,
        source="local-daily-bars",
    )


class News:
    def __init__(self, value: NormalizedNewsEvent) -> None:
        self.value = value

    def effective_events(self, *, cutoff):
        assert cutoff == datetime(2026, 8, 6, 10, tzinfo=UTC)
        return [self.value]

    def cluster_for_article(self, article_id: str):
        if article_id not in {"article-a", "article-b"}:
            return None
        return NewsCluster(
            primary_article_id="article-a",
            article_ids=("article-a", "article-b"),
            source_urls=("https://example.com/article-a", "https://example.com/article-b"),
        )


class Bars:
    def latest_many(self, symbols, limit, as_of, *, cutoff):
        assert symbols == ["600519"]
        assert limit == 21
        assert as_of == date(2026, 8, 6)
        return {"600519": [
            bar(3, "100"),
            bar(4, "105"),
            bar(5, "102"),
            bar(6, "110"),
        ]}


def test_event_impact_uses_first_publication_and_real_trading_windows() -> None:
    report = EventImpactService(News(event()), Bars()).report(
        "event-1", cutoff=datetime(2026, 8, 6, 10, tzinfo=UTC)
    )

    assert report.first_published_at == PUBLISHED
    assert report.event_type == "company_announcement"
    assert report.affected_symbols == ("600519",)
    assert report.related_sectors == ("Beverages", "Consumer")
    assert report.duplicate_status == "duplicate_cluster"
    assert report.duplicate_article_count == 2
    target = report.targets[0]
    windows = {item.horizon_days: item for item in target.windows}
    assert windows[1].status == "ready"
    assert windows[1].return_percent == Decimal("5.00")
    assert windows[3].status == "ready"
    assert windows[3].return_percent == Decimal("10.00")
    assert windows[5].status == "unavailable"
    assert windows[5].return_percent is None
    assert windows[20].status == "unavailable"
    assert target.status == "partial"
    assert report.status == "partial"


def test_event_impact_marks_low_confidence_and_sector_returns_without_proxies() -> None:
    report = EventImpactService(News(event(confidence="0.69")), Bars()).report(
        "event-1", cutoff=datetime(2026, 8, 6, 10, tzinfo=UTC)
    )

    assert report.association_status == "low_confidence"
    assert "low_confidence_association" in report.limitations
    sector_targets = [item for item in report.targets if item.target_type == "sector"]
    assert {item.target_id for item in sector_targets} == {"Beverages", "Consumer"}
    assert all(item.status == "unavailable" for item in sector_targets)
    assert all(
        window.status == "unavailable" and window.return_percent is None
        for target in sector_targets
        for window in target.windows
    )


def test_event_impact_window_rejects_claimed_return_without_market_window() -> None:
    with pytest.raises(ValidationError, match="unavailable window cannot claim prices or return"):
        EventImpactWindow(
            horizon_days=5,
            status="unavailable",
            return_percent=Decimal("8.88"),
            reason="Market window is missing.",
        )
