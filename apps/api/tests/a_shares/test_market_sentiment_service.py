from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from qibao_api.a_shares.market_sentiment import (
    MarketSentimentEvaluator,
    MarketSentimentService,
)
from qibao_api.a_shares.market_sentiment_repository import MarketSentimentRepository
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.market_sentiment import MarketBreadthObservation
from qibao_api.gongbu.tencent_market_sentiment import MarketSentimentFetchResult


PREMARKET_NOW = datetime(2026, 7, 18, 0, 30, tzinfo=timezone.utc)
INTRADAY_NOW = datetime(2026, 7, 18, 2, 30, tzinfo=timezone.utc)
POSTCLOSE_NOW = datetime(2026, 7, 18, 7, 30, tzinfo=timezone.utc)
WEEKEND_NOW = datetime(2026, 7, 19, 2, 30, tzinfo=timezone.utc)


class Calendar:
    def is_trading_day(self, value: date) -> bool:
        return value in {date(2026, 7, 17), date(2026, 7, 18)}


class Source:
    def __init__(self) -> None:
        self.cutoffs = []

    def fetch(self, *, cutoff: datetime) -> MarketSentimentFetchResult:
        self.cutoffs.append(cutoff)
        return MarketSentimentFetchResult(
            observation=MarketBreadthObservation(
                requested_count=100,
                valid_count=100,
                rising_count=70,
                falling_count=25,
                flat_count=5,
                median_change_percent=Decimal("1.2"),
                total_amount_wan=Decimal("1500"),
                limit_up_count=30,
                limit_down_count=2,
                broken_limit_up_count=4,
                max_limit_streak=5,
                observed_at=cutoff - timedelta(seconds=5),
                fetched_at=cutoff,
                source_snapshot_ids=("tencent-market-batch",),
            ),
            raw_batches=(),
        )


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    occurred_at: datetime
    normalized_at: datetime
    affected_instruments: tuple
    themes: tuple[str, ...]
    review_state: str = "verified"


class NewsRepository:
    def __init__(self, events=()) -> None:
        self._events = list(events)
        self.cutoffs = []

    def effective_events(self, *, cutoff=None):
        self.cutoffs.append(cutoff)
        return list(self._events)


def frozen_snapshot(
    trading_date: date,
    *,
    phase: str,
    generated_at: datetime,
    previous_snapshot_id: str | None = None,
):
    return MarketSentimentEvaluator().evaluate(
        observation=Source().fetch(cutoff=generated_at).observation,
        liquidity_baseline=None,
        hotspot=None,
        trading_date=trading_date,
        phase=phase,
        generated_at=generated_at,
        previous_snapshot_id=previous_snapshot_id,
    )


def service(repository, *, source=None, news_repository=None):
    return MarketSentimentService(
        repository=repository,
        source=source or Source(),
        evaluator=MarketSentimentEvaluator(),
        trading_calendar=Calendar(),
        news_repository=news_repository,
    )


def test_premarket_uses_previous_postclose_as_labeled_baseline(tmp_path: Path) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    previous = frozen_snapshot(
        date(2026, 7, 17),
        phase="postclose",
        generated_at=datetime(2026, 7, 17, 7, 30, tzinfo=timezone.utc),
    )
    repository.append(previous, ())
    source = Source()

    response = service(repository, source=source).current(PREMARKET_NOW)

    assert response.current is None
    assert response.previous_close.score == previous.score
    assert response.previous_close.freshness == "stale"
    assert response.display_mode == "previous_close_baseline"
    assert source.cutoffs == []
    repository.close()


def test_nontrading_day_uses_latest_postclose_without_fetching(tmp_path: Path) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    previous = frozen_snapshot(
        date(2026, 7, 17),
        phase="postclose",
        generated_at=datetime(2026, 7, 17, 7, 30, tzinfo=timezone.utc),
    )
    repository.append(previous, ())
    source = Source()

    response = service(repository, source=source).current(WEEKEND_NOW)

    assert response.trading_date == date(2026, 7, 17)
    assert response.phase == "postclose"
    assert response.current is None
    assert response.previous_close.snapshot_id == previous.snapshot_id
    assert response.previous_close.freshness == "stale"
    assert response.display_mode == "previous_close_baseline"
    assert source.cutoffs == []
    repository.close()


def test_premarket_does_not_expose_a_snapshot_from_another_formula(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    previous_formula = frozen_snapshot(
        date(2026, 7, 17),
        phase="postclose",
        generated_at=datetime(2026, 7, 17, 7, 30, tzinfo=timezone.utc),
    ).model_copy(update={"formula_version": "a-share-sentiment-v1"})
    repository.append(previous_formula, ())

    response = service(repository).current(PREMARKET_NOW)

    assert response.display_mode == "unavailable"
    assert response.previous_close is None
    assert response.trajectory == ()
    repository.close()


def test_intraday_refresh_freezes_current_snapshot_and_cutoff_verified_hotspots(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    events = (
        Event(
            event_id="hotspot-a",
            event_type="market_hotspot",
            occurred_at=INTRADAY_NOW - timedelta(hours=1),
            normalized_at=INTRADAY_NOW - timedelta(minutes=50),
            affected_instruments=((AssetKind.A_SHARE, "600000"),),
            themes=("robotics",),
        ),
        Event(
            event_id="hotspot-b",
            event_type="market_hotspot",
            occurred_at=INTRADAY_NOW - timedelta(minutes=30),
            normalized_at=INTRADAY_NOW - timedelta(minutes=20),
            affected_instruments=((AssetKind.A_SHARE, "000001"),),
            themes=("robotics", "finance"),
        ),
        Event(
            event_id="future-hotspot",
            event_type="market_hotspot",
            occurred_at=INTRADAY_NOW + timedelta(minutes=1),
            normalized_at=INTRADAY_NOW + timedelta(minutes=2),
            affected_instruments=((AssetKind.A_SHARE, "300750"),),
            themes=("future",),
        ),
        Event(
            event_id="pending-hotspot",
            event_type="market_hotspot",
            occurred_at=INTRADAY_NOW - timedelta(minutes=10),
            normalized_at=INTRADAY_NOW - timedelta(minutes=5),
            affected_instruments=((AssetKind.A_SHARE, "300750"),),
            themes=("pending",),
            review_state="pending",
        ),
    )
    news = NewsRepository(events)
    source = Source()
    sentiment_service = service(
        repository, source=source, news_repository=news
    )

    stored = sentiment_service.refresh(INTRADAY_NOW)
    response = sentiment_service.current(INTRADAY_NOW + timedelta(minutes=1))

    assert stored.phase == "intraday"
    assert source.cutoffs == [INTRADAY_NOW]
    assert news.cutoffs == [INTRADAY_NOW]
    assert "hotspot-a" in stored.source_snapshot_ids
    assert "hotspot-b" in stored.source_snapshot_ids
    assert response.current.snapshot_id == stored.snapshot_id
    assert response.display_mode == "current"
    repository.close()


def test_postclose_refresh_is_final_and_old_intraday_snapshot_is_stale(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    sentiment_service = service(repository)
    intraday = sentiment_service.refresh(INTRADAY_NOW)

    stale = sentiment_service.current(INTRADAY_NOW + timedelta(minutes=30))
    postclose = sentiment_service.refresh(POSTCLOSE_NOW)
    final = sentiment_service.current(POSTCLOSE_NOW + timedelta(minutes=1))

    assert stale.current.snapshot_id == intraday.snapshot_id
    assert stale.current.freshness == "stale"
    assert postclose.phase == "postclose"
    assert postclose.previous_snapshot_id == intraday.snapshot_id
    assert final.current.snapshot_id == postclose.snapshot_id
    assert [item.snapshot_id for item in final.trajectory] == [
        intraday.snapshot_id,
        postclose.snapshot_id,
    ]
    repository.close()
