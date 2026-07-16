from datetime import datetime, timezone
import hashlib

from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_linking import DeterministicNewsLinker
from qibao_api.gongbu.news_taxonomy import (
    DEFAULT_INDUSTRY_KEYWORDS,
    DEFAULT_THEME_KEYWORDS,
)


def test_default_taxonomy_labels_high_signal_news_without_verifying_it() -> None:
    raw = b"bank industry and AI policy"
    article = NewsArticle(
        article_id="article-taxonomy-1",
        canonical_url="https://example.com/taxonomy-1",
        publisher="测试来源",
        title="银行业迎来人工智能与算力政策支持",
        published_at=datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 7, 17, 8, 1, tzinfo=timezone.utc),
        content_hash=hashlib.sha256(raw).hexdigest(),
        raw_snapshot=raw,
        source_verified=True,
    )

    event = DeterministicNewsLinker(
        instrument_aliases={},
        industry_keywords=DEFAULT_INDUSTRY_KEYWORDS,
        theme_keywords=DEFAULT_THEME_KEYWORDS,
    ).link(article)

    assert "银行" in event.industries
    assert "人工智能" in event.themes
    assert event.review_state == "pending"
