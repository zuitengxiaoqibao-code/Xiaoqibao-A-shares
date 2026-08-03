from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.candidate_sentiment import (
    CandidateSentimentEvaluator,
    CandidateSentimentEvidence,
    sentiment_band,
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


def factor(symbol: str, *, liquidity: str = "100000000") -> FactorSnapshot:
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
        liquidity_amount_20d=Decimal(liquidity),
        source="local-daily-bars",
    )


def board(symbols: tuple[str, ...] = ("600000", "000001")) -> CandidateBoard:
    return CandidateBoard(
        snapshot_id="a-share-candidates-1",
        input_snapshot_hash="a" * 64,
        as_of=AS_OF,
        short_term=tuple(
            CandidateEntry(
                symbol=symbol,
                horizon="short_term",
                score=Decimal("60") - index,
                score_breakdown={"momentum": Decimal("20")},
                factor_snapshot=factor(symbol),
            )
            for index, symbol in enumerate(symbols)
        ),
        swing=(),
        exclusions=(),
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
    symbol: str = "600000",
    *,
    event_type: str = "market_news",
    occurred_at: datetime | None = None,
) -> NormalizedNewsEvent:
    evidence = citation(event_id)
    return NormalizedNewsEvent(
        event_id=event_id,
        event_type=event_type,
        headline=f"{event_id} 标题",
        occurred_at=occurred_at or CUTOFF - timedelta(hours=1),
        normalized_at=occurred_at or CUTOFF - timedelta(hours=1),
        affected_instruments=((AssetKind.A_SHARE, symbol),),
        themes=("先进制造",),
        citations=(evidence,),
        association_confidence=Decimal("0.9"),
        review_state="verified",
    )


def interpretation(
    source_event: NormalizedNewsEvent,
    direction: str,
    *,
    confidence: str = "0.8",
    generated_at: datetime | None = None,
    degraded: bool = False,
) -> AIInterpretation:
    return AIInterpretation(
        interpretation_id=(
            f"interpretation-{source_event.event_id}-{direction}-"
            f"{int((generated_at or CUTOFF).timestamp())}"
        ),
        event_id=source_event.event_id,
        generated_at=generated_at or CUTOFF,
        provider="test",
        model="test-model",
        prompt_version="news-v1",
        degraded=degraded,
        impact_direction=direction,
        confidence=Decimal(confidence),
        statements=(InterpretationStatement(
            statement_id=f"statement-{source_event.event_id}",
            kind="fact",
            text="已核验事实",
            citation_ids=(source_event.citations[0].citation_id,),
        ),),
        citations=source_event.citations,
    )


def fund(
    symbol: str,
    *,
    main_net_5d: str,
    intraday_main_net: str | None = None,
) -> FundFlowSnapshot:
    return FundFlowSnapshot(
        snapshot_id=f"fund-flow-{'1' * 24}",
        symbol=symbol,
        observed_at=CUTOFF - timedelta(minutes=1),
        latest_trade_date=date(2026, 7, 17),
        latest_main_net=Decimal("10000000"),
        latest_super_net=Decimal("5000000"),
        latest_large_net=Decimal("5000000"),
        main_net_5d=Decimal(main_net_5d),
        main_net_20d=Decimal(main_net_5d),
        intraday_main_net=(Decimal(intraday_main_net) if intraday_main_net is not None else None),
        daily_sample_count=20,
        intraday_sample_count=1 if intraday_main_net is not None else 0,
        flow_direction="inflow" if Decimal(main_net_5d) > 0 else "outflow",
        content_hash="c" * 64,
        raw_snapshot=b"{}",
    )


def test_partial_score_uses_available_weight_and_preserves_candidate_order() -> None:
    evaluator = CandidateSentimentEvaluator()
    result = evaluator.evaluate(
        board(),
        {
            "600000": CandidateSentimentEvidence(
                hotspot_sync_ready=True,
                hotspot_events=(event("hotspot-1", event_type="market_hotspot"),),
                fund_flow=fund("600000", main_net_5d="100000000"),
            ),
            "000001": CandidateSentimentEvidence(
                hotspot_sync_ready=True,
                fund_flow=fund("000001", main_net_5d="-100000000"),
            ),
        },
        cutoff=CUTOFF,
    )

    assert [item.symbol for item in result.items] == ["600000", "000001"]
    assert result.items[0].coverage_percent == Decimal("60")
    assert result.items[0].quality == "partial"
    assert result.items[0].score is not None
    assert result.items[0].score > result.items[1].score


def test_news_requires_frozen_cited_confident_interpretation_before_cutoff() -> None:
    source_event = event("news-1")
    evaluator = CandidateSentimentEvaluator()
    result = evaluator.evaluate(
        board(("600000",)),
        {"600000": CandidateSentimentEvidence(
            news_sync_ready=True,
            news_events=(source_event,),
            news_interpretations=(
                interpretation(source_event, "negative", confidence="0.64"),
                interpretation(source_event, "positive", generated_at=CUTOFF + timedelta(minutes=1)),
            ),
        )},
        cutoff=CUTOFF,
    )

    item = result.items[0]
    assert item.score is None
    assert item.band == "unavailable"
    assert item.components[0].status == "unavailable"


def test_successful_news_sync_without_direction_is_neutral_evidence() -> None:
    evaluator = CandidateSentimentEvaluator()
    item = evaluator.evaluate(
        board(("600000",)),
        {"600000": CandidateSentimentEvidence(news_sync_ready=True)},
        cutoff=CUTOFF,
    ).items[0]

    assert item.components[0].score == Decimal("50")
    assert item.components[0].summary == "未发现明确方向事件"
    assert item.coverage_percent == Decimal("40")
    assert item.score is None


def test_repeated_hotspot_and_positive_funds_create_overheated_risk() -> None:
    source_event = event("news-positive")
    hotspots = tuple(
        event(f"hotspot-{index}", event_type="market_hotspot", occurred_at=CUTOFF - timedelta(minutes=index))
        for index in range(3)
    )
    item = CandidateSentimentEvaluator().evaluate(
        board(("600000",)),
        {"600000": CandidateSentimentEvidence(
            news_sync_ready=True,
            news_events=(source_event,),
            news_interpretations=(interpretation(source_event, "positive", confidence="1"),),
            hotspot_sync_ready=True,
            hotspot_events=hotspots,
            fund_flow=fund("600000", main_net_5d="100000000", intraday_main_net="1"),
        )},
        cutoff=CUTOFF,
    ).items[0]

    assert item.quality == "ready"
    assert item.band == "overheated"
    assert item.score is not None and item.score >= Decimal("80")
    assert "追涨" in item.primary_risk


def test_fund_flow_normalizes_against_five_day_liquidity_and_caps_adjustment() -> None:
    item = CandidateSentimentEvaluator().evaluate(
        board(("600000",)),
        {"600000": CandidateSentimentEvidence(
            hotspot_sync_ready=True,
            fund_flow=fund("600000", main_net_5d="500000000", intraday_main_net="999999999"),
        )},
        cutoff=CUTOFF,
    ).items[0]
    fund_component = item.components[2]

    assert fund_component.score == Decimal("85")


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        ("0", "strongly_bearish"),
        ("20", "cautious"),
        ("40", "neutral"),
        ("60", "positive"),
        ("80", "overheated"),
        ("100", "overheated"),
    ],
)
def test_sentiment_band_boundaries(score: str, expected: str) -> None:
    assert sentiment_band(Decimal(score)) == expected
