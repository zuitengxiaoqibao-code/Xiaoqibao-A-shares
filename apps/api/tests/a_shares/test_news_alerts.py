import hashlib
from datetime import UTC, datetime, timedelta

from qibao_api.a_shares.news_alerts import BreakingNewsAlertService
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_collection import NewsCluster
from qibao_api.gongbu.news_linking import DeterministicNewsLinker
from qibao_api.gongbu.news_repository import NewsRepository


CUTOFF = datetime(2026, 7, 29, 2, 0, tzinfo=UTC)


def article(article_id: str, publisher: str, host: str) -> NewsArticle:
    raw = article_id.encode()
    return NewsArticle(
        article_id=article_id,
        canonical_url=f"https://{host}/{article_id}",
        publisher=publisher,
        title="贵州茅台发布重要经营公告",
        published_at=CUTOFF - timedelta(minutes=30),
        fetched_at=CUTOFF - timedelta(minutes=29),
        content_hash=hashlib.sha256(raw).hexdigest(),
        raw_snapshot=raw,
        source_verified=True,
    )


def test_multi_source_direct_event_becomes_breaking_alert(tmp_path) -> None:
    repository = NewsRepository(tmp_path / "news.sqlite3")
    first = article("news-1", "来源甲", "a.example")
    second = article("news-2", "来源乙", "b.example")
    repository.append_articles((first, second))
    repository.append_cluster(NewsCluster(
        primary_article_id=first.article_id,
        article_ids=(first.article_id, second.article_id),
        source_urls=(first.canonical_url, second.canonical_url),
    ))
    event = DeterministicNewsLinker(
        instrument_aliases={(AssetKind.A_SHARE, "600519"): ("贵州茅台",)},
        industry_keywords={}, theme_keywords={},
    ).link(first).model_copy(update={"review_state": "verified"})
    repository.append_event(event)

    alert = BreakingNewsAlertService(repository).current(CUTOFF, symbol="600519").alerts[0]
    assert alert.verification_state == "multi_source_confirmed"
    assert alert.urgency == "breaking"
    assert alert.source_count == 2
    assert alert.association_kind == "direct"
    assert alert.affected_symbols == ("600519",)


def test_theme_only_event_never_enters_symbol_alerts(tmp_path) -> None:
    repository = NewsRepository(tmp_path / "news.sqlite3")
    item = article("theme-1", "来源甲", "a.example")
    repository.append_articles((item,))
    event = DeterministicNewsLinker(
        instrument_aliases={}, industry_keywords={},
        theme_keywords={"人形机器人": ("贵州茅台",)},
    ).link(item)
    repository.append_event(event)

    assert BreakingNewsAlertService(repository).current(CUTOFF, symbol="600519").alerts == ()


def test_market_wide_alerts_exclude_news_without_a_share_association(tmp_path) -> None:
    repository = NewsRepository(tmp_path / "news.sqlite3")
    item = article("unlinked-1", "来源甲", "a.example")
    repository.append_articles((item,))
    event = DeterministicNewsLinker(
        instrument_aliases={}, industry_keywords={}, theme_keywords={},
    ).link(item).model_copy(update={"review_state": "verified"})
    repository.append_event(event)

    assert BreakingNewsAlertService(repository).current(CUTOFF).alerts == ()


def test_cutoff_excludes_future_events(tmp_path) -> None:
    repository = NewsRepository(tmp_path / "news.sqlite3")
    item = article("future-1", "来源甲", "a.example").model_copy(update={
        "published_at": CUTOFF + timedelta(minutes=1),
        "fetched_at": CUTOFF + timedelta(minutes=2),
    })
    repository.append_articles((item,))
    event = DeterministicNewsLinker(
        instrument_aliases={(AssetKind.A_SHARE, "600519"): ("贵州茅台",)},
        industry_keywords={}, theme_keywords={},
    ).link(item)
    repository.append_event(event)

    assert BreakingNewsAlertService(repository).current(CUTOFF).alerts == ()


def test_market_wide_limit_bounds_event_enrichment(tmp_path, monkeypatch) -> None:
    repository = NewsRepository(tmp_path / "news.sqlite3")
    events = []
    for index in range(3):
        item = article(f"bounded-{index}", f"来源{index}", f"{index}.example").model_copy(update={
            "published_at": CUTOFF - timedelta(minutes=30 + index),
            "fetched_at": CUTOFF - timedelta(minutes=29 + index),
        })
        repository.append_articles((item,))
        event = DeterministicNewsLinker(
            instrument_aliases={(AssetKind.A_SHARE, "600519"): ("贵州茅台",)},
            industry_keywords={}, theme_keywords={},
        ).link(item).model_copy(update={"review_state": "verified"})
        repository.append_event(event)
        events.append(event)

    interpretation_queries = []
    original = repository.latest_interpretations_by_event

    def record_query(event_ids, cutoff):
        interpretation_queries.append(event_ids)
        return original(event_ids, cutoff)

    monkeypatch.setattr(repository, "latest_interpretations_by_event", record_query)

    response = BreakingNewsAlertService(repository).current(CUTOFF, limit=1)

    assert len(response.alerts) == 1
    assert interpretation_queries == [(events[0].event_id,)]
