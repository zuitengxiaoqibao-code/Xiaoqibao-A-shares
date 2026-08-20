from datetime import UTC, datetime
import hashlib

from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_linking import DeterministicNewsLinker
from qibao_api.gongbu.news_quality_policy import NewsQualityPolicy


NOW = datetime(2026, 8, 20, 1, 0, tzinfo=UTC)


def article(title: str, summary: str | None = None) -> NewsArticle:
    raw = title.encode()
    return NewsArticle(
        article_id=hashlib.sha256(raw).hexdigest()[:24],
        canonical_url="https://news.example/item",
        publisher="测试来源",
        title=title,
        summary=summary,
        published_at=NOW,
        fetched_at=NOW,
        content_hash=hashlib.sha256(raw).hexdigest(),
        raw_snapshot=raw,
        source_verified=True,
    )


def linker() -> DeterministicNewsLinker:
    return DeterministicNewsLinker(
        instrument_aliases={},
        industry_keywords={"先进制造": ("先进制造",)},
        theme_keywords={"政策支持": ("政策",)},
    )


def test_policy_keeps_a_share_relevant_article_and_rejects_unrelated_content() -> None:
    policy = NewsQualityPolicy()
    relevant_item = article("600000获得先进制造政策支持")
    relevant = policy.evaluate(relevant_item, linker().link(relevant_item))
    unrelated_item = article("周末抽奖活动，点击领取福利")
    unrelated = policy.evaluate(unrelated_item, linker().link(unrelated_item))

    assert relevant.accepted is True
    assert relevant.reason == "a_share_relevant"
    assert unrelated.accepted is False
    assert unrelated.reason == "unrelated_or_low_information"


def test_policy_rejects_advertising_even_when_text_contains_a_share_code() -> None:
    policy = NewsQualityPolicy()
    item = article("600000开户链接，扫码领取优惠")

    decision = policy.evaluate(item, linker().link(item))

    assert decision.accepted is False
    assert decision.reason == "advertising"
