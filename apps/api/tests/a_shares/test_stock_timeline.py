from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.a_shares.stock_timeline import StockTimelineService
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    AIInterpretation,
    EvidenceCitation,
    InterpretationStatement,
    NormalizedNewsEvent,
)
from qibao_api.gongbu.market_feed import MarketFeedSnapshot


CHINA_TZ = timezone(timedelta(hours=8))
CUTOFF = datetime(2026, 7, 28, 15, 30, tzinfo=CHINA_TZ)


def bar(trade_date: date, close: str) -> DailyBar:
    return DailyBar(
        symbol="600519",
        trade_date=trade_date,
        open=Decimal("1400"),
        high=Decimal("1450"),
        low=Decimal("1380"),
        close=Decimal(close),
        volume=100,
        amount=Decimal("140000"),
        source="local-daily-bars",
    )


def event(
    event_id: str,
    occurred_at: datetime,
    *,
    event_type: str = "market_news",
    review_state: str = "verified",
    symbol: str = "600519",
    themes: tuple[str, ...] = ("白酒",),
) -> NormalizedNewsEvent:
    citation = EvidenceCitation(
        citation_id=f"citation-{event_id}",
        article_id=f"article-{event_id}",
        canonical_url=f"https://news.example/{event_id}",
        publisher="证券时报",
        published_at=occurred_at,
        quoted_text=f"{event_id} 标题",
        content_hash="1" * 64,
    )
    return NormalizedNewsEvent(
        event_id=event_id,
        event_type=event_type,
        headline=f"{event_id} 完整新闻标题",
        occurred_at=occurred_at,
        normalized_at=occurred_at + timedelta(minutes=1),
        affected_instruments=((AssetKind.A_SHARE, symbol),),
        industries=("食品饮料",),
        themes=themes,
        citations=(citation,),
        association_confidence=Decimal("0.95"),
        association_kind="direct",
        association_reasons=(f"security_code:{symbol}",),
        review_state=review_state,
    )


def interpretation(
    event_id: str,
    generated_at: datetime,
    direction: str,
    confidence: str,
) -> AIInterpretation:
    return AIInterpretation(
        interpretation_id=f"interpretation-{event_id}-{generated_at.timestamp()}",
        event_id=event_id,
        generated_at=generated_at,
        provider="fixture",
        model="fixture",
        prompt_version="v1",
        impact_direction=direction,
        confidence=Decimal(confidence),
        statements=(InterpretationStatement(
            statement_id=f"statement-{event_id}-{generated_at.timestamp()}",
            kind="interpretation",
            text="仅用于测试影响方向",
        ),),
    )


class Bars:
    def latest(self, symbol, limit, *, cutoff=None):
        assert symbol == "600519"
        assert limit == 120
        assert cutoff == CUTOFF
        return [
            bar(date(2026, 7, 28), "1430"),
            bar(date(2026, 7, 24), "1410"),
            bar(date(2026, 7, 27), "1390"),
        ]


class News:
    def __init__(self):
        self.weekend = event(
            "weekend", datetime(2026, 7, 25, 9, 0, tzinfo=CHINA_TZ),
            themes=("消费",),
        )
        self.intraday = event(
            "intraday", datetime(2026, 7, 27, 10, 18, tzinfo=CHINA_TZ),
        )
        self.events = [
            self.intraday,
            event("announcement", datetime(2026, 7, 28, 9, 5, tzinfo=CHINA_TZ), event_type="market_announcement"),
            event("batch-hotspot", datetime(2026, 7, 27, 10, 20, tzinfo=CHINA_TZ), event_type="market_hotspot"),
            event("pending", datetime(2026, 7, 27, 10, 30, tzinfo=CHINA_TZ), review_state="pending"),
            event("wrong-symbol", datetime(2026, 7, 27, 10, 40, tzinfo=CHINA_TZ), symbol="000001"),
            self.weekend,
        ]
        self.articles = {
            "article-intraday": SimpleNamespace(
                article_id="article-intraday", publisher="证券时报",
                canonical_url="https://source-a.example/intraday", source_verified=True,
            ),
            "article-intraday-2": SimpleNamespace(
                article_id="article-intraday-2", publisher="上交所",
                canonical_url="https://source-b.example/intraday", source_verified=True,
            ),
            "article-weekend": SimpleNamespace(
                article_id="article-weekend", publisher="证券时报",
                canonical_url="https://source-a.example/weekend", source_verified=True,
            ),
            "article-announcement": SimpleNamespace(
                article_id="article-announcement", publisher="巨潮资讯",
                canonical_url="https://source-a.example/announcement", source_verified=True,
            ),
        }

    def events_for_symbol(self, symbol, *, cutoff=None, since=None, limit=None):
        assert symbol == "600519"
        assert cutoff == CUTOFF
        assert since == datetime(2026, 7, 24, 0, 0, tzinfo=CHINA_TZ)
        assert limit == 480
        return list(self.events)

    def effective_events_for_symbol(self, symbol, *, cutoff=None):
        raise AssertionError("timeline must use the bounded symbol query")

    def effective_events(self, *, cutoff=None):
        raise AssertionError("timeline must not scan all effective news after symbol filtering")

    def latest_interpretations_by_event(self, event_ids, cutoff):
        values = self.interpretations_for_events(
            tuple(event_id for event_id in ("weekend", "intraday") if event_id in event_ids),
            cutoff=cutoff,
        )
        latest = {}
        for item in values:
            if item.generated_at <= cutoff:
                latest[item.event_id] = item
        return latest

    def cluster_for_article(self, article_id):
        if article_id == "article-intraday":
            return SimpleNamespace(article_ids=("article-intraday", "article-intraday-2"))
        return SimpleNamespace(article_ids=(article_id,))

    def articles_by_ids(self, article_ids):
        return [self.articles[article_id] for article_id in article_ids if article_id in self.articles]

    def interpretations_for_events(self, event_ids, *, cutoff=None):
        assert event_ids in (("weekend", "intraday"), ("weekend", "intraday", "announcement"))
        assert cutoff == CUTOFF
        return [
            interpretation(
                "intraday", datetime(2026, 7, 27, 10, 30, tzinfo=CHINA_TZ),
                "negative", "0.55",
            ),
            interpretation(
                "intraday", datetime(2026, 7, 27, 11, 0, tzinfo=CHINA_TZ),
                "positive", "0.82",
            ),
            interpretation(
                "intraday", CUTOFF + timedelta(minutes=1),
                "negative", "0.99",
            ),
        ]


def minute_snapshot(observed_at: datetime, price: str, snapshot_id: str) -> MarketFeedSnapshot:
    return MarketFeedSnapshot(
        symbol="600519",
        price=Decimal(price),
        change=Decimal("1.5"),
        change_percent=Decimal("0.11"),
        volume=Decimal("1200"),
        source="tencent-realtime",
        observed_at=observed_at,
        fetched_at=observed_at + timedelta(seconds=1),
        quality="ready",
        source_snapshot_id=snapshot_id,
    )


class IntradaySnapshots:
    def intraday_snapshots(self, symbol, trading_date, *, cutoff):
        assert symbol == "600519"
        assert trading_date == date(2026, 7, 28)
        assert cutoff == CUTOFF
        return (
            minute_snapshot(datetime(2026, 7, 28, 10, 2, tzinfo=CHINA_TZ), "1432", "minute-2"),
            minute_snapshot(datetime(2026, 7, 28, 9, 31, tzinfo=CHINA_TZ), "1430", "minute-1"),
        )


class TradingCalendar:
    def is_trading_day(self, value):
        return value.weekday() < 5


def test_timeline_reuses_symbol_candidates_without_global_alert_scan() -> None:
    result = StockTimelineService(Bars(), News()).get(
        "600519", date(2026, 7, 28), CUTOFF
    )

    assert [item.event_id for item in result.events] == ["weekend", "intraday", "announcement"]


def test_timeline_uses_real_bars_and_only_verified_timestamped_stock_news() -> None:
    result = StockTimelineService(Bars(), News()).get(
        "600519", date(2026, 7, 28), CUTOFF
    )

    assert [item.trade_date for item in result.bars] == [
        date(2026, 7, 24), date(2026, 7, 27), date(2026, 7, 28),
    ]
    assert [item.event_id for item in result.events] == ["weekend", "intraday", "announcement"]
    assert result.events[0].mapped_trade_date is None
    assert result.events[0].label == "消费"
    assert result.events[0].direction == "uncertain"
    assert result.events[1].mapped_trade_date == date(2026, 7, 27)
    assert result.events[1].direction == "positive"
    assert result.events[1].confidence == Decimal("0.82")
    assert result.events[1].publisher == "证券时报"
    assert result.events[1].source_url == "https://news.example/intraday"
    assert result.events[1].association_kind == "direct"
    assert result.events[1].association_reasons == ("security_code:600519",)
    assert result.events[1].verification_state == "multi_source_confirmed"
    assert result.events[1].urgency == "tracking"
    assert result.events[1].source_count == 2
    assert result.events[1].category == "industry_sector"
    assert result.events[1].strength == "medium"
    assert result.events[1].duration == "unknown"
    assert result.events[1].price_reflection == "unknown"
    assert result.events[1].follow_up_indicators == (
        "观察板块成交额、涨停扩散和龙头持续性",
    )
    assert result.sources == ("local-daily-bars", "verified-market-news")


def test_timeline_includes_sorted_real_intraday_snapshots_for_selected_date() -> None:
    result = StockTimelineService(
        Bars(),
        News(),
        poll_state_repository=IntradaySnapshots(),
        trading_calendar=TradingCalendar(),
    ).get("600519", date(2026, 7, 28), CUTOFF)

    assert result.intraday_status == "ready"
    assert [item.source_snapshot_id for item in result.intraday_points] == [
        "minute-1",
        "minute-2",
    ]
    assert result.intraday_sources == ("tencent-realtime",)
    assert result.intraday_warnings == ()
    assert result.status == "ready"
    assert result.bars


class EmptyIntradaySnapshots:
    def intraday_snapshots(self, symbol, trading_date, *, cutoff):
        return ()


class LiveIntradayFallback:
    def snapshot_many(self, symbols, *, cutoff=None):
        assert symbols == ("600519",)
        return (minute_snapshot(
            datetime(2026, 7, 28, 14, 59, tzinfo=CHINA_TZ), "1435", "live-minute"),)


class HistoricalMinuteSource:
    def fetch_stock_minutes(self, symbol, *, cutoff=None):
        assert symbol == "600519"
        assert cutoff == CUTOFF
        return (
            minute_snapshot(datetime(2026, 7, 28, 9, 30, tzinfo=CHINA_TZ), "1428", "tencent-minute-1"),
            minute_snapshot(datetime(2026, 7, 28, 10, 2, tzinfo=CHINA_TZ), "1432", "tencent-minute-2"),
        )


def test_current_day_merges_real_minute_history_when_archive_has_only_one_point() -> None:
    class OneArchivedSnapshot:
        def intraday_snapshots(self, symbol, trading_date, *, cutoff):
            return (minute_snapshot(
                datetime(2026, 7, 28, 10, 2, tzinfo=CHINA_TZ), "1432", "archived-latest"),)

    result = StockTimelineService(
        Bars(),
        News(),
        poll_state_repository=OneArchivedSnapshot(),
        trading_calendar=TradingCalendar(),
        minute_source=HistoricalMinuteSource(),
    ).get("600519", date(2026, 7, 28), CUTOFF)

    assert result.intraday_status == "ready"
    assert [item.observed_at for item in result.intraday_points] == [
        datetime(2026, 7, 28, 9, 30, tzinfo=CHINA_TZ),
        datetime(2026, 7, 28, 10, 2, tzinfo=CHINA_TZ),
    ]
    assert [item.source_snapshot_id for item in result.intraday_points] == [
        "tencent-minute-1", "archived-latest",
    ]
    assert result.intraday_warnings == ()


def test_missing_intraday_snapshots_do_not_remove_daily_timeline() -> None:
    result = StockTimelineService(
        Bars(),
        News(),
        poll_state_repository=EmptyIntradaySnapshots(),
        trading_calendar=TradingCalendar(),
    ).get("600519", date(2026, 7, 28), CUTOFF)

    assert result.intraday_status == "unavailable"
    assert result.intraday_points == ()
    assert result.intraday_warnings == ("intraday_snapshots_unavailable",)
    assert result.status == "ready"
    assert result.bars


def test_current_day_uses_real_live_snapshot_when_archive_is_empty() -> None:
    result = StockTimelineService(
        Bars(),
        News(),
        poll_state_repository=EmptyIntradaySnapshots(),
        trading_calendar=TradingCalendar(),
        live_feed=LiveIntradayFallback(),
    ).get("600519", date(2026, 7, 28), CUTOFF)

    assert result.intraday_status == "ready"
    assert [item.source_snapshot_id for item in result.intraday_points] == ["live-minute"]
    assert result.intraday_sources == ("tencent-realtime",)


class FailedIntradaySnapshots:
    def intraday_snapshots(self, symbol, trading_date, *, cutoff):
        raise RuntimeError("intraday store unavailable")


def test_intraday_read_failure_does_not_remove_daily_timeline() -> None:
    result = StockTimelineService(
        Bars(),
        News(),
        poll_state_repository=FailedIntradaySnapshots(),
        trading_calendar=TradingCalendar(),
    ).get("600519", date(2026, 7, 28), CUTOFF)

    assert result.intraday_status == "unavailable"
    assert result.intraday_points == ()
    assert result.intraday_warnings == ("intraday_snapshot_read_failed",)
    assert result.status == "ready"
    assert result.bars


class NoBars:
    def latest(self, symbol, limit, *, cutoff=None):
        return []


class UnusedNews:
    def events_for_symbol(self, symbol, *, cutoff=None, since=None, limit=None):
        raise AssertionError("news must not be queried without a chart range")


def test_timeline_reports_unavailable_without_inventing_bars() -> None:
    result = StockTimelineService(NoBars(), UnusedNews()).get(
        "600519", date(2026, 7, 28), CUTOFF
    )

    assert result.status == "unavailable"
    assert result.bars == ()
    assert result.events == ()
    assert result.warnings == ("local_daily_bars_unavailable",)
