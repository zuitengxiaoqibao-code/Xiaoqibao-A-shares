from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import time

import httpx

from qibao_api.a_shares.market_overview import MarketOverviewService
from qibao_api.contracts.market_overview import (
    OverviewBreadth,
    OverviewFeatureStock,
    OverviewIndexQuote,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewMarketSnapshot,
    OverviewMinutePoint,
    OverviewRegimeMetrics,
    OverviewStockQuote,
)
from qibao_api.contracts.market_sentiment import (
    MarketSentimentSnapshot,
    SentimentComponent,
)


NOW = datetime(2026, 7, 29, 2, 30, tzinfo=timezone.utc)


def component(name: str, metrics: dict) -> SentimentComponent:
    return SentimentComponent(
        name=name, score=Decimal("70"), weight=Decimal("15"),
        coverage_percent=Decimal("100"), metrics=metrics,
        evidence_ids=(f"evidence-{name}",),
    )


def sentiment() -> MarketSentimentSnapshot:
    return MarketSentimentSnapshot(
        snapshot_id="sentiment-1", previous_snapshot_id=None,
        trading_date=date(2026, 7, 29), phase="intraday", quality="ready",
        freshness="current", score=Decimal("76"), band="active",
        coverage_percent=Decimal("100"),
        components=(
            component("breadth", {
                "rising_count": 4439, "falling_count": 699,
                "flat_count": 20, "valid_count": 5158,
            }),
            component("limit_ecology", {
                "limit_up_count": 78, "limit_down_count": 6,
                "broken_limit_up_count": 19,
            }),
            component("activity", {
                "total_amount_wan": "158629600", "baseline_amount_wan": "194443900",
                "relative_amount": "0.82",
            }),
        ),
        drivers=("上涨股票覆盖扩大",), risks=(), beginner_guidance="市场活跃。",
        observed_at=NOW, generated_at=NOW,
        source_snapshot_ids=("source-1",), formula_version="a-share-sentiment-v2",
    )


class SentimentRepository:
    def __init__(self) -> None:
        self.latest_calls = []
        self.previous_calls = []

    def latest(self, **kwargs):
        self.latest_calls.append(kwargs)
        return sentiment()

    def previous_postclose(self, trading_date, **kwargs):
        self.previous_calls.append((trading_date, kwargs))
        return None


def event(
    index: int,
    *,
    theme: str = "电力体制改革",
    event_type: str = "market_hotspot",
    affected_instruments=(("a_share", "002310"),),
):
    return SimpleNamespace(
        event_id=f"event-{index}", event_type=event_type,
        headline=f"{theme}异动 {index}",
        occurred_at=NOW - timedelta(minutes=index),
        normalized_at=NOW - timedelta(minutes=index) + timedelta(seconds=2),
        affected_instruments=affected_instruments,
        industries=(), themes=(theme,), citations=(SimpleNamespace(publisher="同花顺"),),
        review_state="verified",
    )


def test_overview_does_not_pin_batch_hotspot_fetch_time_to_the_minute_chart() -> None:
    batch_hotspot = event(0, event_type="market_hotspot")
    timestamped_news = event(0, event_type="market_news")
    outside_minute_window = event(5, event_type="market_news")
    minute = OverviewMinutePoint(
        observed_at=NOW,
        price=Decimal("3823.73"),
        volume=Decimal("100"),
        amount=Decimal("1000"),
    )

    result = MarketOverviewService._anomalies(
        (batch_hotspot, timestamped_news, outside_minute_window),
        (minute,),
    )

    assert [item.anomaly_id for item in result] == [timestamped_news.event_id]


class NewsRepository:
    def __init__(self, events=None):
        self.events = events

    def effective_events(self, **_kwargs):
        return self.events if self.events is not None else [event(index) for index in range(35)]


class FirstLimitRepository:
    def latest_scan(self, **_kwargs):
        return SimpleNamespace(candidates=())


class Source:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def fetch_indices(self):
        self.calls += 1
        if self.fail:
            raise OSError("index down")
        return ((OverviewIndexQuote(
            instrument="sh000001", name="上证指数", value=Decimal("3823.73"),
            change=Decimal("9.53"), change_percent=Decimal("0.25"),
            observed_at=NOW, source="tencent", quality="ready",
        ),), ())

    def fetch_minutes(self):
        if self.fail:
            raise OSError("minute down")
        return ((OverviewMinutePoint(
            observed_at=NOW, price=Decimal("3823.73"), volume=Decimal("100"),
            amount=Decimal("1000"),
        ),), ())

    def fetch_stocks(self, symbols):
        return ((OverviewStockQuote(
            symbol="002310", name="东方新能", change_percent=Decimal("10"),
            amount_yi=Decimal("12.65"), market_cap_yi=Decimal("106.02"),
            observed_at=NOW,
        ),), ()) if symbols else ((), ())


class OfflineHttpSource:
    def fetch_indices(self):
        raise httpx.ConnectError("offline")

    def fetch_minutes(self):
        raise httpx.ConnectError("offline")

    def fetch_stocks(self, symbols):
        raise httpx.ConnectError("offline")


class BlockingSource(Source):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()

    def fetch_indices(self):
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=5)
        raise OSError("refresh blocked")

    def fetch_minutes(self):
        raise OSError("refresh blocked")


class LocalMarketSource:
    def current(self):
        return OverviewMarketSnapshot(
            observed_at=NOW,
            source="tdx-local-rpc",
            quality="ready",
            quote_count=5200,
            universe_count=5300,
            breadth=OverviewBreadth(
                rising_count=3000, falling_count=2100,
                flat_count=100, valid_count=5200,
            ),
            limit_ecology=OverviewLimitEcology(
                limit_up_count=66, limit_down_count=9,
                broken_limit_up_count=22, seal_rate_percent=Decimal("75"),
            ),
            liquidity=OverviewLiquidity(total_amount_yi=Decimal("12345.67")),
            regime_metrics=OverviewRegimeMetrics(
                up_ratio=Decimal("57.69"), zt_ratio=Decimal("1.27"),
                dt_ratio=Decimal("0.17"), median_ret=Decimal("0.52"),
                strong_close_ratio=Decimal("62"), weak_close_ratio=Decimal("18"),
                limit_fail_ratio=Decimal("25"), panic_ratio=Decimal("3"),
                amp_ratio=Decimal("14"), net_positive_ratio=None,
                large_amount_strong_close_ratio=Decimal("68"),
                factor_coverage_percent=Decimal("90.91"),
            ),
            market_stocks=(OverviewFeatureStock(
                symbol="600001", name="示例涨停", price=Decimal("11"),
                previous_close=Decimal("10"), open=Decimal("10.2"),
                high=Decimal("11"), low=Decimal("10.1"), volume=Decimal("1000"),
                amount_yi=Decimal("3.2"), change_percent=Decimal("10"),
                state="limit_up", observed_at=NOW, source="tdx-local-rpc",
                quality="ready",
            ),),
        )


def test_overview_labels_previous_close_snapshot_before_open() -> None:
    premarket = datetime(2026, 7, 30, 0, 30, tzinfo=timezone.utc)
    result = service(
        Source(),
        clock=lambda: premarket,
        local_market_source=LocalMarketSource(),
    ).current(premarket)

    assert result.market_data.phase == "premarket"
    assert result.market_data.freshness == "previous_close"
    assert result.market_data.quality == "ready"


def test_overview_labels_same_day_snapshot_as_live_during_session() -> None:
    intraday = datetime(2026, 7, 29, 2, 30, tzinfo=timezone.utc)
    result = service(
        Source(),
        clock=lambda: intraday,
        local_market_source=LocalMarketSource(),
    ).current(intraday)

    assert result.market_data.phase == "intraday"
    assert result.market_data.freshness == "live"


def test_overview_marks_old_same_day_snapshot_stale_during_session() -> None:
    current = NOW + timedelta(minutes=6)
    result = service(
        Source(),
        clock=lambda: current,
        local_market_source=LocalMarketSource(),
    ).current(current)

    assert result.market_data.phase == "intraday"
    assert result.market_data.freshness == "stale"


def test_overview_labels_same_day_snapshot_as_final_after_close() -> None:
    postclose = datetime(2026, 7, 29, 8, 30, tzinfo=timezone.utc)
    result = service(
        Source(),
        clock=lambda: postclose,
        local_market_source=LocalMarketSource(),
    ).current(postclose)

    assert result.market_data.phase == "postclose"
    assert result.market_data.freshness == "final"


def service(
    source: Source,
    clock=lambda: NOW,
    local_market_source=None,
    news_repository=None,
    **kwargs,
) -> MarketOverviewService:
    return MarketOverviewService(
        sentiment_repository=SentimentRepository(),
        news_repository=news_repository or NewsRepository(),
        first_limit_up_repository=FirstLimitRepository(), source=source, clock=clock,
        local_market_source=local_market_source,
        **kwargs,
    )


def test_overview_combines_local_sentiment_news_and_tencent_market_data() -> None:
    overview = service(Source())
    result = overview.current(NOW)

    assert result.status == "ready"
    assert result.sentiment.score == Decimal("76")
    assert result.breadth.rising_count == 4439
    assert result.limit_ecology.seal_rate_percent == Decimal("80.41")
    assert len(result.live_feed) == 30
    assert result.sectors[0].name == "电力体制改革"
    assert result.sector_stocks[result.sectors[0].sector_id][0].name == "东方新能"
    assert overview.sentiment_repository.latest_calls == [{
        "trading_date": date(2026, 7, 29),
        "formula_version": "a-share-sentiment-v2",
    }]


def test_overview_excludes_news_without_verified_a_share_association() -> None:
    a_share_news = event(0, event_type="market_news")
    convertible_bond_news = event(
        1,
        theme="可转债",
        event_type="market_news",
        affected_instruments=(("convertible_bond", "113001"),),
    )
    unlinked_macro_news = event(
        2,
        theme="海外宏观",
        event_type="market_news",
        affected_instruments=(),
    )

    result = service(
        Source(),
        news_repository=NewsRepository([
            a_share_news,
            convertible_bond_news,
            unlinked_macro_news,
        ]),
    ).current(NOW)

    assert [item.event_id for item in result.live_feed] == [a_share_news.event_id]
    assert [item.anomaly_id for item in result.anomalies] == [a_share_news.event_id]
    assert [item.name for item in result.sectors] == ["电力体制改革"]


def test_overview_keeps_local_regions_when_tencent_is_unavailable() -> None:
    result = service(Source(fail=True)).current(NOW)

    assert result.status == "partial"
    assert result.indices == ()
    assert result.sentiment.score == Decimal("76")
    assert "index_quotes_unavailable" in result.warnings


def test_overview_degrades_all_http_connection_failures_without_raising() -> None:
    result = service(OfflineHttpSource()).current(NOW)

    assert result.status == "partial"
    assert result.indices == ()
    assert result.minute_series == ()
    assert "index_quotes_unavailable" in result.warnings
    assert "minute_series_unavailable" in result.warnings
    assert "sector_stock_quotes_unavailable" in result.warnings


def test_overview_reuses_snapshot_inside_five_second_window() -> None:
    source = Source()
    current = NOW
    overview = service(source, clock=lambda: current)

    first = overview.current(current)
    second = overview.current(current + timedelta(seconds=4))

    assert second is first
    assert source.calls == 1


def test_overview_prefers_independent_local_realtime_market_statistics() -> None:
    result = service(Source(), local_market_source=LocalMarketSource()).current(NOW)

    assert result.breadth.rising_count == 3000
    assert result.limit_ecology.limit_up_count == 66
    assert result.liquidity.total_amount_yi == Decimal("12345.67")
    assert result.liquidity.baseline_amount_yi == Decimal("19444.39")
    assert result.liquidity.relative_amount == Decimal("0.82")
    assert result.market_data.source == "tdx-local-rpc"
    assert result.market_data.quote_count == 5200
    assert result.market_stocks[0].state == "limit_up"
    assert result.regime.regime == "缩量混沌"
    assert result.regime.coverage_percent == Decimal("85.00")
    assert "net_positive_ratio" in result.regime.missing_factors
    assert result.regime.rule_matched is False
    assert "tdx-local-realtime" in result.sources


def test_overview_reuses_persisted_snapshot_while_latest_refresh_runs_in_background(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "market-overview.json"
    initial = service(Source(), clock=lambda: NOW, cache_path=cache_path)
    initial.current(NOW)
    initial.close()

    source = BlockingSource()
    cached = service(
        source,
        clock=lambda: NOW,
        cache_path=cache_path,
        defer_initial_refresh=True,
    )

    result = cached.current(NOW + timedelta(seconds=20))

    assert result.observed_at == NOW
    assert "market-overview-cache" in result.sources
    assert source.started.wait(timeout=1)

    source.release.set()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not source.calls:
        time.sleep(0.01)
    cached.close()
