from datetime import UTC, datetime, timedelta

from qibao_api.contracts.news import EvidenceCitation, NormalizedNewsEvent
from qibao_api.contracts.market import AssetKind
from qibao_api.gongbu.news_retention import NewsRetentionPolicy


NOW = datetime(2026, 8, 20, 1, 0, tzinfo=UTC)


def event(event_type: str, headline: str, occurred_at: datetime) -> NormalizedNewsEvent:
    citation = EvidenceCitation(
        citation_id="c-1", article_id="a-1", canonical_url="https://news.example/1",
        publisher="测试来源", published_at=occurred_at, quoted_text=headline,
        content_hash="a" * 64,
    )
    return NormalizedNewsEvent(
        event_id=f"event-{event_type}", event_type=event_type, headline=headline,
        occurred_at=occurred_at, normalized_at=occurred_at,
        affected_instruments=((AssetKind.A_SHARE, "600000"),), citations=(citation,),
        association_confidence="1", association_kind="direct",
        association_reasons=("test",), review_state="verified",
    )


def test_retention_keeps_regulatory_and_earnings_events_longer_than_intraday_news() -> None:
    policy = NewsRetentionPolicy()
    old = NOW - timedelta(days=10)

    intraday = policy.expiry_for(event("intraday_alert", "盘中异动", old))
    earnings = policy.expiry_for(event("market_news", "发布年度业绩预告", old))
    regulatory = policy.expiry_for(event("market_news", "收到监管问询函", old))

    assert intraday < NOW
    assert earnings > NOW
    assert regulatory > NOW
