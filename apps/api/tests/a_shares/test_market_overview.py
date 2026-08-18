from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import time

import httpx

from qibao_api.a_shares.market_overview import MarketOverviewService
from qibao_api.contracts.market_review import MarketReviewSnapshot
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


class RegimeSentimentRepository(SentimentRepository):
    def __init__(self):
        super().__init__()
        self.written = []

    def previous_regime_risk(self, trading_date, **kwargs):
        return Decimal("68") if trading_date > date(2026, 7, 28) else None

    def append_regime_risk(self, **kwargs):
        self.written.append(kwargs)


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


def test_overview_anomaly_reuses_unified_event_category_and_verified_direction() -> None:
    timestamped_news = event(0, event_type="market_news")
    minute = OverviewMinutePoint(
        observed_at=NOW,
        price=Decimal("3823.73"),
        volume=Decimal("100"),
        amount=Decimal("1000"),
    )
    projection = SimpleNamespace(
        category="industry_sector", direction="positive",
        strength="high", credibility="verified",
    )

    result = MarketOverviewService._anomalies(
        (timestamped_news,), (minute,),
        {timestamped_news.event_id: projection},
    )

    assert result[0].category == "industry_sector"
    assert result[0].direction == "positive"
    assert result[0].strength == "high"
    assert result[0].credibility == "verified"


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


class RefreshingSource(Source):
    def __init__(self) -> None:
        super().__init__()
        self.index_refreshed = Event()
        self.minute_refreshed = Event()

    def fetch_indices(self):
        self.calls += 1
        self.index_refreshed.set()
        return ((OverviewIndexQuote(
            instrument="sh000001", name="上证指数", value=Decimal("3835.73"),
            change=Decimal("21.53"), change_percent=Decimal("0.56"),
            observed_at=NOW + timedelta(minutes=31), source="tencent", quality="ready",
        ),), ())

    def fetch_minutes(self):
        self.minute_refreshed.set()
        return ((OverviewMinutePoint(
            observed_at=NOW + timedelta(minutes=31), price=Decimal("3835.73"),
            volume=Decimal("120"), amount=Decimal("1200"),
        ),), ())


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


class MutableLocalMarketSource:
    def __init__(self, snapshot: OverviewMarketSnapshot) -> None:
        self.snapshot = snapshot

    def current(self):
        return self.snapshot


def local_market_with_stock(
    *, observed_at: datetime, state: str, price: str, change_percent: str,
) -> OverviewMarketSnapshot:
    return OverviewMarketSnapshot(
        observed_at=observed_at,
        source="tdx-local-rpc",
        quality="ready",
        quote_count=5200,
        universe_count=5300,
        breadth=OverviewBreadth(
            rising_count=3000, falling_count=2100, flat_count=100, valid_count=5200,
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=1 if state == "limit_up" else 0,
            limit_down_count=1 if state == "limit_down" else 0,
            broken_limit_up_count=1 if state == "broken_limit_up" else 0,
        ),
        liquidity=OverviewLiquidity(total_amount_yi=Decimal("12345.67")),
        market_stocks=(OverviewFeatureStock(
            symbol="600001", name="示例股票", price=Decimal(price),
            previous_close=Decimal("10"), open=Decimal("10.1"),
            high=Decimal(price), low=Decimal("10"), volume=Decimal("1000"),
            amount_yi=Decimal("3.2"), change_percent=Decimal(change_percent),
            state=state, observed_at=observed_at, source="tdx-local-rpc",
            quality="ready",
        ),),
    )


class FundFlowRepository:
    def coverage_percent(self, as_of, *, cutoff, universe_count):
        return Decimal("0.02")

    def latest(self, symbol, as_of, *, cutoff=None):
        if symbol != "600001":
            return None
        return SimpleNamespace(
            symbol=symbol,
            observed_at=NOW,
            latest_trade_date=date(2026, 7, 29),
            latest_main_net=Decimal("280000000"),
            latest_large_net=Decimal("150000000"),
            latest_super_net=Decimal("130000000"),
            source="eastmoney-fund-flow",
        )


class SectorFundFlowRepository:
    def history(self, *, limit=60):
        first = SimpleNamespace(
            observed_at=NOW - timedelta(minutes=1),
            source="eastmoney-sector-fund-flow",
            items=(
                SimpleNamespace(sector_code="BK1036", sector_name="人工智能", main_net_yi=Decimal("20.00"), large_net_yi=Decimal("9.00"), super_net_yi=Decimal("11.00")),
                SimpleNamespace(sector_code="BK0475", sector_name="银行", main_net_yi=Decimal("-8.00"), large_net_yi=Decimal("-4.00"), super_net_yi=Decimal("-4.00")),
            ),
        )
        second = SimpleNamespace(
            observed_at=NOW,
            source="eastmoney-sector-fund-flow",
            items=(
                SimpleNamespace(sector_code="BK1036", sector_name="人工智能", main_net_yi=Decimal("23.80"), large_net_yi=Decimal("10.80"), super_net_yi=Decimal("13.00")),
                SimpleNamespace(sector_code="BK0475", sector_name="银行", main_net_yi=Decimal("-9.60"), large_net_yi=Decimal("-5.40"), super_net_yi=Decimal("-4.20")),
            ),
        )
        return (first, second)


class OfficialCalendarSource:
    def fetch(self):
        return (
            SimpleNamespace(
                code="732001", name="测试新股", kind="新股申购",
                subscription_date=date(2026, 7, 29), listing_date=date(2026, 8, 6),
                allotment_date=date(2026, 7, 31), fetched_at=NOW,
                source="tdx-local-rpc",
            ),
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
    sentiment_repository=None,
    **kwargs,
) -> MarketOverviewService:
    return MarketOverviewService(
        sentiment_repository=sentiment_repository or SentimentRepository(),
        news_repository=news_repository or NewsRepository(),
        first_limit_up_repository=FirstLimitRepository(), source=source, clock=clock,
        local_market_source=local_market_source,
        **kwargs,
    )


def test_overview_uses_and_persists_verified_previous_regime_risk() -> None:
    repository = RegimeSentimentRepository()
    result = service(
        Source(), local_market_source=LocalMarketSource(),
        sentiment_repository=repository,
    ).current(NOW)

    assert result.regime.previous_risk_score == Decimal("68")
    assert repository.written
    assert repository.written[-1]["formula_version"] == "a-share-short-regime-v2.0"


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


def test_overview_registers_four_shared_snapshots_and_marks_cache_reuse() -> None:
    class SnapshotRegistry:
        def __init__(self) -> None:
            self.calls = []

        def record(self, kind, **payload):
            self.calls.append((kind, payload))

    registry = SnapshotRegistry()
    overview = service(Source(), shared_snapshot_registry=registry)

    overview.current(NOW)
    overview.current(NOW + timedelta(seconds=1))

    expected = [
        "market_cross_section", "limit_events", "sector_strength", "stock_fund_flow",
    ]
    assert [kind for kind, _payload in registry.calls[:4]] == expected
    assert [kind for kind, _payload in registry.calls[4:]] == expected
    assert all(payload["reused"] is False for _kind, payload in registry.calls[:4])
    assert all(payload["reused"] is True for _kind, payload in registry.calls[4:])
    assert all(len(payload["content_hash"]) == 64 for _kind, payload in registry.calls)
    assert registry.calls[0][1]["trade_date"] == date(2026, 7, 29)


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
    result = service(
        Source(), local_market_source=LocalMarketSource(),
        fund_flow_repository=FundFlowRepository(),
    ).current(NOW)

    assert result.breadth.rising_count == 3000
    assert result.limit_ecology.limit_up_count == 66
    assert result.liquidity.total_amount_yi == Decimal("12345.67")
    assert result.liquidity.baseline_amount_yi == Decimal("19444.39")
    assert result.liquidity.relative_amount == Decimal("0.82")
    assert result.market_data.source == "tdx-local-rpc"
    assert result.market_data.quote_count == 5200
    assert result.market_stocks[0].state == "limit_up"
    assert result.data_scope.market_aggregate == "full_a_share_market"
    assert result.data_scope.market_quote_count == 5200
    assert result.data_scope.stock_sample == "representative"
    assert result.data_scope.stock_sample_count == len(result.market_stocks)
    assert result.data_scope.sector_sample == "strong_sector"
    assert result.data_scope.sector_sample_count == len(result.sectors)
    assert result.regime.regime == "缩量混沌"
    assert result.regime.coverage_percent == Decimal("85.00")
    assert "net_positive_ratio" in result.regime.missing_factors
    assert result.regime.rule_matched is False
    assert result.regime_metrics.net_positive_ratio_coverage_percent == Decimal("0.02")
    assert "tdx-local-realtime" in result.sources
    evidence = {item.field_path: item for item in result.field_evidence}
    assert evidence["breadth.rising_count"].value == 3000
    assert evidence["breadth.rising_count"].source == "tdx-local-rpc"
    assert evidence["breadth.rising_count"].status == "live"
    assert evidence["breadth.rising_count"].coverage_percent == Decimal("98.11")
    assert evidence["sentiment.score"].derived is True
    assert evidence["sentiment.score"].formula == "a-share-sentiment-v2"
    assert evidence["regime.emotion_score"].derived is True
    assert evidence["regime.emotion_score"].formula == "a-share-short-regime-v2.0"
    assert evidence["regime_metrics.net_positive_ratio"].status == "missing"
    assert evidence["regime_metrics.net_positive_ratio"].limitations == (
        "全市场资金流覆盖不足",
    )


def test_overview_marks_unavailable_market_fields_as_missing_evidence() -> None:
    result = service(Source()).current(NOW)

    evidence = {item.field_path: item for item in result.field_evidence}
    assert evidence["regime.emotion_score"].status == "missing"
    assert evidence["regime.emotion_score"].value is None
    assert evidence["regime.emotion_score"].limitations == ("tdx_local_market_unavailable",)


def test_overview_exposes_cached_real_large_order_direction_without_amount_proxy() -> None:
    result = service(
        Source(),
        local_market_source=LocalMarketSource(),
        fund_flow_repository=FundFlowRepository(),
    ).current(NOW)

    assert len(result.large_order_flows) == 1
    flow = result.large_order_flows[0]
    assert flow.symbol == "600001"
    assert flow.main_net_yi == Decimal("2.80")
    assert flow.large_net_yi == Decimal("1.50")
    assert flow.super_net_yi == Decimal("1.30")
    assert flow.direction == "inflow"
    assert flow.source == "eastmoney-fund-flow"
    assert result.data_scope.large_order_sample_count == 1


def test_overview_exposes_real_sector_net_flow_time_series_with_sample_scope() -> None:
    result = service(
        Source(),
        local_market_source=LocalMarketSource(),
        sector_fund_flow_repository=SectorFundFlowRepository(),
    ).current(NOW)

    assert len(result.sector_fund_flow) == 4
    assert result.sector_fund_flow[0].sector_code == "BK1036"
    assert result.sector_fund_flow[-1].main_net_yi == Decimal("-9.60")
    assert result.sector_fund_flow[-1].quality == "ready"
    assert result.data_scope.sector_fund_flow_sample_count == 2
    assert result.data_scope.sector_fund_flow_snapshot_count == 2


def test_overview_separates_official_calendar_dates_from_news_timestamps() -> None:
    result = service(
        Source(),
        official_calendar_source=OfficialCalendarSource(),
    ).current(NOW)

    assert [(item.event_type, item.event_date) for item in result.official_events] == [
        ("subscription", date(2026, 7, 29)),
        ("allotment", date(2026, 7, 31)),
        ("listing", date(2026, 8, 6)),
    ]
    assert all(item.source == "tdx-local-rpc" for item in result.official_events)
    assert result.live_feed[0].occurred_at == NOW


def test_overview_marks_lagging_review_stale_without_dropping_real_rows() -> None:
    review = MarketReviewSnapshot(
        as_of=date(2026, 7, 28),
        observed_at=NOW,
        latest_trade_date=date(2026, 7, 28),
        source="market-db",
        quality="ready",
        universe_count=5300,
        history_ready_count=5200,
    )

    class ReviewSource:
        def current(self):
            return review

    result = service(
        Source(),
        local_market_source=LocalMarketSource(),
        market_review_source=ReviewSource(),
    ).current(NOW)

    assert result.review is not None
    assert result.review.quality == "stale"
    assert result.review.latest_trade_date == date(2026, 7, 28)
    assert result.review.history_ready_count == 5200
    assert "market_review_stale" in result.warnings


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


def test_overview_refreshes_intraday_core_while_extended_build_is_blocked(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "market-overview.json"
    initial = service(Source(), clock=lambda: NOW, cache_path=cache_path)
    initial.current(NOW)
    initial.close()

    source = RefreshingSource()
    fresh_news = event(0, event_type="market_news")
    fresh_news.occurred_at = NOW + timedelta(minutes=31)
    cached = service(
        source,
        clock=lambda: NOW + timedelta(minutes=31),
        cache_path=cache_path,
        defer_initial_refresh=True,
        news_repository=NewsRepository([fresh_news]),
    )
    build_started = Event()
    build_release = Event()

    def blocked_build(_now):
        build_started.set()
        build_release.wait(timeout=5)
        return initial.current(NOW)

    cached._build = blocked_build
    stale = cached.current(NOW + timedelta(minutes=31))
    assert stale.indices[0].value == Decimal("3823.73")
    assert build_started.wait(timeout=1)
    assert source.index_refreshed.wait(timeout=1)

    deadline = time.monotonic() + 2
    refreshed = stale
    while time.monotonic() < deadline:
        refreshed = cached.current(NOW + timedelta(minutes=31, seconds=6))
        if (
            refreshed.indices
            and refreshed.indices[0].value == Decimal("3835.73")
            and refreshed.anomalies
        ):
            break
        time.sleep(0.01)

    build_release.set()
    if cached._core_refresh_future is not None and cached._core_refresh_future.done():
        assert cached._core_refresh_future.exception() is None
    if cached._refresh_future is not None:
        cached._refresh_future.result(timeout=1)
    final = cached.current(NOW + timedelta(minutes=31, seconds=12))
    cached.close()
    assert final.indices[0].value == Decimal("3835.73")
    assert final.minute_series[-1].price == Decimal("3835.73")
    assert final.anomalies[0].anomaly_id == fresh_news.event_id


def test_overview_records_verified_local_quote_state_change_without_news(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "market-overview.json"
    local_source = MutableLocalMarketSource(local_market_with_stock(
        observed_at=NOW, state="active", price="10.50", change_percent="5.00",
    ))
    initial = service(
        Source(), clock=lambda: NOW, cache_path=cache_path,
        local_market_source=local_source, news_repository=NewsRepository([]),
    )
    first = initial.current(NOW)
    initial.close()
    assert first.anomalies == ()

    local_source.snapshot = local_market_with_stock(
        observed_at=NOW + timedelta(minutes=31), state="limit_up",
        price="11.00", change_percent="10.00",
    )
    source = RefreshingSource()
    cached = service(
        source, clock=lambda: NOW + timedelta(minutes=31, seconds=6), cache_path=cache_path,
        defer_initial_refresh=True, local_market_source=local_source,
        news_repository=NewsRepository([]),
    )
    cached.current(NOW + timedelta(minutes=31))

    deadline = time.monotonic() + 2
    refreshed = cached.current(NOW + timedelta(minutes=31, seconds=6))
    while time.monotonic() < deadline and not refreshed.anomalies:
        time.sleep(0.01)
        refreshed = cached.current(NOW + timedelta(minutes=31, seconds=6))

    cached.close()
    assert refreshed.anomalies[0].label == "涨停封板"
    assert refreshed.anomalies[0].symbols == ("600001",)
    assert refreshed.anomalies[0].credibility == "verified"


def test_overview_gives_cached_response_a_grace_period_before_background_refresh(
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
        initial_refresh_delay_seconds=0.05,
    )

    result = cached.current(NOW + timedelta(seconds=20))

    assert result.observed_at == NOW
    assert not source.started.wait(timeout=0.01)
    assert source.started.wait(timeout=1)
    source.release.set()
    cached.close()


def test_overview_does_not_expose_review_from_stale_disk_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "market-overview.json"
    base = service(Source()).current(NOW)
    stale_review = MarketReviewSnapshot(
        as_of=date(2026, 7, 17),
        observed_at=NOW,
        latest_trade_date=date(2026, 7, 17),
        source="market-db",
        quality="ready",
    )
    cache_path.write_text(
        base.model_copy(update={"review": stale_review}).model_dump_json(),
        encoding="utf-8",
    )

    class StaleReviewSource:
        def cache_is_stale(self):
            return True

        def current(self):
            return None

    overview = service(
        Source(),
        cache_path=cache_path,
        market_review_source=StaleReviewSource(),
        defer_initial_refresh=True,
    )

    result = overview.current(NOW + timedelta(seconds=20))

    assert result.review is None
    assert "market_review_cache_stale" in result.warnings
    overview.close()
