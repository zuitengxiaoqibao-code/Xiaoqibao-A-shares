import asyncio
import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.candidate_sentiment import CandidateSentimentEvaluator
from qibao_api.a_shares.candidate_sentiment_repository import CandidateSentimentRepository
from qibao_api.a_shares.candidate_sentiment_service import (
    CandidateSentimentInputError,
    CandidateSentimentService,
    CandidateSnapshotNotFoundError,
)
from qibao_api.a_shares.models import CandidateBoard, CandidateEntry, FactorSnapshot
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    AIInterpretation,
    EvidenceCitation,
    InterpretationStatement,
    NormalizedNewsEvent,
)
from qibao_api.gongbu.fund_flow import FundFlowSnapshot


CUTOFF = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)
AS_OF = date(2026, 7, 18)
SNAPSHOT_ID = "a-share-candidates-service-test"


def factor(symbol: str) -> FactorSnapshot:
    return FactorSnapshot(
        symbol=symbol,
        as_of=AS_OF,
        latest_trade_date=date(2026, 7, 17),
        close=Decimal("10"),
        return_5d=Decimal("0.02"),
        return_20d=Decimal("0.05"),
        distance_ma20=Decimal("0.03"),
        volume_ratio_5_20=Decimal("1.2"),
        volatility_20d=Decimal("0.18"),
        drawdown_60d=Decimal("-0.08"),
        liquidity_amount_20d=Decimal("100000000"),
        source="local-daily-bars",
    )


def entry(symbol: str, horizon: str = "short_term") -> CandidateEntry:
    return CandidateEntry(
        symbol=symbol,
        horizon=horizon,
        score=Decimal("60"),
        score_breakdown={"momentum": Decimal("20")},
        factor_snapshot=factor(symbol),
    )


def board(
    symbols: tuple[str, ...] = ("600000", "000001"),
    *,
    snapshot_id: str = SNAPSHOT_ID,
) -> CandidateBoard:
    return CandidateBoard(
        snapshot_id=snapshot_id,
        input_snapshot_hash="a" * 64,
        as_of=AS_OF,
        short_term=[entry(symbol) for symbol in symbols],
        swing=[entry("300999", "swing")],
        exclusions=[],
    )


def citation(event_id: str) -> EvidenceCitation:
    return EvidenceCitation(
        citation_id=f"citation-{event_id}",
        article_id=f"article-{event_id}",
        canonical_url=f"https://example.com/{event_id}",
        publisher="测试来源",
        published_at=CUTOFF - timedelta(hours=2),
        quoted_text="已核验内容",
        content_hash="b" * 64,
    )


def event(
    event_id: str,
    symbol: str,
    *,
    event_type: str = "market_news",
    occurred_at: datetime | None = None,
) -> NormalizedNewsEvent:
    observed_at = occurred_at or CUTOFF - timedelta(hours=1)
    evidence = citation(event_id)
    return NormalizedNewsEvent(
        event_id=event_id,
        event_type=event_type,
        headline=f"{event_id} 标题",
        occurred_at=observed_at,
        normalized_at=observed_at,
        affected_instruments=((AssetKind.A_SHARE, symbol),),
        themes=("先进制造",),
        citations=(evidence,),
        association_confidence=Decimal("0.9"),
        review_state="verified",
    )


def interpretation(
    source_event: NormalizedNewsEvent,
    direction: str,
    generated_at: datetime,
) -> AIInterpretation:
    return AIInterpretation(
        interpretation_id=(
            f"interpretation-{source_event.event_id}-{direction}-"
            f"{int(generated_at.timestamp())}"
        ),
        event_id=source_event.event_id,
        generated_at=generated_at,
        provider="test",
        model="test-model",
        prompt_version="news-v1",
        degraded=False,
        impact_direction=direction,
        confidence=Decimal("0.8"),
        statements=(InterpretationStatement(
            statement_id=f"statement-{source_event.event_id}-{direction}",
            kind="fact",
            text="已核验事实",
            citation_ids=(source_event.citations[0].citation_id,),
        ),),
        citations=source_event.citations,
    )


def fund(symbol: str, observed_at: datetime = CUTOFF) -> FundFlowSnapshot:
    identity = hashlib.sha256(f"{symbol}-{observed_at.isoformat()}".encode()).hexdigest()
    return FundFlowSnapshot(
        snapshot_id=f"fund-flow-{identity[:24]}",
        symbol=symbol,
        observed_at=observed_at,
        latest_trade_date=date(2026, 7, 17),
        latest_main_net=Decimal("10000000"),
        latest_super_net=Decimal("5000000"),
        latest_large_net=Decimal("5000000"),
        main_net_5d=Decimal("100000000"),
        main_net_20d=Decimal("100000000"),
        intraday_main_net=Decimal("1000000"),
        daily_sample_count=20,
        intraday_sample_count=1,
        flow_direction="inflow",
        content_hash="c" * 64,
        raw_snapshot=b"{}",
    )


class FakeResearchRepository:
    def __init__(self, value: CandidateBoard | Exception) -> None:
        self.value = value

    def get_candidate_board(self, snapshot_id: str) -> CandidateBoard:
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class FakeNewsRepository:
    def __init__(
        self,
        events: tuple[NormalizedNewsEvent, ...] = (),
        interpretations: tuple[AIInterpretation, ...] = (),
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self.events = events
        self.interpretation_values = interpretations
        self.failed_symbols = set(failed_symbols)
        self.event_calls: list[tuple[str, datetime | None]] = []
        self.interpretation_calls: list[tuple[tuple[str, ...], datetime | None]] = []

    def effective_events_for_symbol(
        self, symbol: str, *, cutoff: datetime | None = None
    ) -> list[NormalizedNewsEvent]:
        self.event_calls.append((symbol, cutoff))
        if symbol in self.failed_symbols:
            raise OSError("news store unavailable")
        return [
            item for item in self.events
            if (AssetKind.A_SHARE, symbol) in item.affected_instruments
            and (cutoff is None or item.normalized_at <= cutoff)
            and (cutoff is None or item.occurred_at <= cutoff)
        ]

    def interpretations_for_events(
        self, event_ids: tuple[str, ...], *, cutoff: datetime | None = None
    ) -> list[AIInterpretation]:
        self.interpretation_calls.append((event_ids, cutoff))
        return [
            item for item in self.interpretation_values
            if item.event_id in event_ids
            and (cutoff is None or item.generated_at <= cutoff)
        ]


class FakeFundFlowRepository:
    def __init__(
        self,
        snapshots: dict[str, FundFlowSnapshot] | None = None,
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self.snapshots = snapshots or {}
        self.failed_symbols = set(failed_symbols)
        self.calls: list[tuple[str, date, datetime | None]] = []

    def latest(
        self, symbol: str, as_of: date, *, cutoff: datetime | None = None
    ) -> FundFlowSnapshot | None:
        self.calls.append((symbol, as_of, cutoff))
        if symbol in self.failed_symbols:
            raise OSError("fund-flow store unavailable")
        value = self.snapshots.get(symbol)
        if value is not None and cutoff is not None and value.observed_at > cutoff:
            return None
        return value


class ConcurrencyTracker:
    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0

    async def wait(self) -> None:
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0.001)
        self.active -= 1


class FakeNewsSync:
    def __init__(
        self,
        tracker: ConcurrencyTracker | None = None,
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self.tracker = tracker or ConcurrencyTracker()
        self.failed_symbols = set(failed_symbols)
        self.calls: list[str] = []

    async def sync_symbol(self, symbol: str) -> dict[str, int]:
        self.calls.append(symbol)
        await self.tracker.wait()
        if symbol in self.failed_symbols:
            raise OSError("news source offline")
        return {"fetched": 0, "inserted": 0, "clusters": 0, "events": 0}


class FakeFundSync:
    def __init__(
        self,
        repository: FakeFundFlowRepository,
        tracker: ConcurrencyTracker | None = None,
        *,
        failed_symbols: tuple[str, ...] = (),
    ) -> None:
        self.repository = repository
        self.tracker = tracker or ConcurrencyTracker()
        self.failed_symbols = set(failed_symbols)
        self.calls: list[str] = []

    async def sync_symbol(self, symbol: str) -> FundFlowSnapshot:
        self.calls.append(symbol)
        await self.tracker.wait()
        if symbol in self.failed_symbols:
            raise ValueError("fund source malformed")
        snapshot = fund(symbol)
        self.repository.snapshots[symbol] = snapshot
        return snapshot


class FakeHotspotSync:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[date, datetime]] = []

    def sync(self, trading_date: date, *, fetched_at: datetime):
        self.calls.append((trading_date, fetched_at))
        if self.error is not None:
            raise self.error
        return {"fetched": 0, "inserted": 0, "clusters": 0, "events": 0}


def make_service(
    tmp_path,
    candidate_board: CandidateBoard | Exception,
    *,
    news_repository: FakeNewsRepository | None = None,
    fund_repository: FakeFundFlowRepository | None = None,
    news_sync=None,
    hotspot_sync=None,
    fund_sync=None,
) -> CandidateSentimentService:
    return CandidateSentimentService(
        research_repository=FakeResearchRepository(candidate_board),
        sentiment_repository=CandidateSentimentRepository(
            tmp_path / "candidate-sentiment.sqlite3"
        ),
        news_repository=news_repository or FakeNewsRepository(),
        fund_flow_repository=fund_repository or FakeFundFlowRepository(),
        evaluator=CandidateSentimentEvaluator(),
        news_ingestion_service=news_sync,
        hotspot_ingestion_service=hotspot_sync,
        fund_flow_service=fund_sync,
    )


def test_current_reads_cutoff_bounded_frozen_evidence_without_syncing(tmp_path) -> None:
    source_event = event("news-1", "600000")
    latest = interpretation(source_event, "negative", CUTOFF - timedelta(minutes=10))
    future = interpretation(source_event, "positive", CUTOFF + timedelta(minutes=1))
    news_repository = FakeNewsRepository(
        (source_event,),
        (
            interpretation(source_event, "positive", CUTOFF - timedelta(minutes=20)),
            latest,
            future,
        ),
    )
    fund_repository = FakeFundFlowRepository({"600000": fund("600000")})
    service = make_service(
        tmp_path,
        board(("600000",)),
        news_repository=news_repository,
        fund_repository=fund_repository,
    )

    result = service.current(SNAPSHOT_ID, CUTOFF)

    assert [item.symbol for item in result.items] == ["600000"]
    assert result.items[0].components[0].score == Decimal("25.00")
    assert latest.interpretation_id in result.items[0].components[0].evidence_ids
    assert future.interpretation_id not in result.items[0].components[0].evidence_ids
    assert news_repository.event_calls == [("600000", CUTOFF)]
    assert news_repository.interpretation_calls == [((source_event.event_id,), CUTOFF)]
    assert fund_repository.calls == [("600000", AS_OF, CUTOFF)]


def test_current_rejects_unknown_or_mismatched_candidate_snapshot(tmp_path) -> None:
    missing = make_service(tmp_path, KeyError("missing"))
    with pytest.raises(CandidateSnapshotNotFoundError):
        missing.current("missing", CUTOFF)

    mismatched = make_service(tmp_path, board(("600000",), snapshot_id="different"))
    with pytest.raises(CandidateSentimentInputError, match="identity"):
        mismatched.current(SNAPSHOT_ID, CUTOFF)


@pytest.mark.asyncio
async def test_refresh_limits_work_to_twenty_short_term_symbols_and_four_calls(
    tmp_path,
) -> None:
    symbols = tuple(f"{600000 + index:06d}" for index in range(22))
    candidate_board = board(symbols)
    tracker = ConcurrencyTracker()
    news_sync = FakeNewsSync(tracker)
    fund_repository = FakeFundFlowRepository()
    fund_sync = FakeFundSync(fund_repository, tracker)
    hotspot_sync = FakeHotspotSync()
    service = make_service(
        tmp_path,
        candidate_board,
        fund_repository=fund_repository,
        news_sync=news_sync,
        hotspot_sync=hotspot_sync,
        fund_sync=fund_sync,
    )

    result = await service.refresh(SNAPSHOT_ID, CUTOFF)

    expected = list(symbols[:20])
    assert [item.symbol for item in result.items] == expected
    assert news_sync.calls == expected
    assert fund_sync.calls == expected
    assert "300999" not in news_sync.calls
    assert tracker.maximum <= 4
    assert hotspot_sync.calls == [(AS_OF, CUTOFF)]


@pytest.mark.asyncio
async def test_refresh_keeps_other_sources_and_symbols_when_one_fails(tmp_path) -> None:
    candidate_board = board()
    news_sync = FakeNewsSync(failed_symbols=("600000",))
    fund_repository = FakeFundFlowRepository()
    fund_sync = FakeFundSync(fund_repository)
    hotspot_sync = FakeHotspotSync()
    service = make_service(
        tmp_path,
        candidate_board,
        fund_repository=fund_repository,
        news_sync=news_sync,
        hotspot_sync=hotspot_sync,
        fund_sync=fund_sync,
    )

    result = await service.refresh(SNAPSHOT_ID, CUTOFF)

    assert [item.symbol for item in result.items] == ["600000", "000001"]
    assert result.items[0].quality == "partial"
    assert result.items[0].coverage_percent == Decimal("60")
    assert result.items[1].quality == "ready"
    assert result.items[1].score is not None
    assert hotspot_sync.calls == [(AS_OF, CUTOFF)]


def test_current_degrades_repository_failures_per_symbol_and_source(tmp_path) -> None:
    positive_event = event("news-positive", "000001")
    hotspot = event("hotspot-1", "000001", event_type="market_hotspot")
    news_repository = FakeNewsRepository(
        (positive_event, hotspot),
        (interpretation(positive_event, "positive", CUTOFF - timedelta(minutes=1)),),
        failed_symbols=("600000",),
    )
    fund_repository = FakeFundFlowRepository(
        {"600000": fund("600000")},
        failed_symbols=("000001",),
    )
    service = make_service(
        tmp_path,
        board(),
        news_repository=news_repository,
        fund_repository=fund_repository,
    )

    result = service.current(SNAPSHOT_ID, CUTOFF)

    assert result.items[0].quality == "unavailable"
    assert result.items[1].quality == "partial"
    assert result.items[1].coverage_percent == Decimal("70")


@pytest.mark.asyncio
async def test_refresh_reuses_result_for_fifteen_minutes(tmp_path) -> None:
    candidate_board = board(("600000",))
    news_sync = FakeNewsSync()
    fund_repository = FakeFundFlowRepository()
    fund_sync = FakeFundSync(fund_repository)
    hotspot_sync = FakeHotspotSync()
    service = make_service(
        tmp_path,
        candidate_board,
        fund_repository=fund_repository,
        news_sync=news_sync,
        hotspot_sync=hotspot_sync,
        fund_sync=fund_sync,
    )

    first = await service.refresh(SNAPSHOT_ID, CUTOFF)
    reused = await service.refresh(SNAPSHOT_ID, CUTOFF + timedelta(minutes=10))
    refreshed = await service.refresh(SNAPSHOT_ID, CUTOFF + timedelta(minutes=16))

    assert reused.snapshot_id == first.snapshot_id
    assert refreshed.snapshot_id != first.snapshot_id
    assert news_sync.calls == ["600000", "600000"]
    assert fund_sync.calls == ["600000", "600000"]
    assert len(hotspot_sync.calls) == 2
