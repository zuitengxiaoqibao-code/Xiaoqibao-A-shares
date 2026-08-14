from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qibao_api.a_shares.unified_events import UnifiedEventProjectionService
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    AIInterpretation,
    EvidenceCitation,
    InterpretationStatement,
    NormalizedNewsEvent,
)


NOW = datetime(2026, 8, 12, 2, 30, tzinfo=UTC)


def citation(article_id: str, publisher: str = "上交所") -> EvidenceCitation:
    return EvidenceCitation(
        citation_id=f"citation-{article_id}", article_id=article_id,
        canonical_url=f"https://news.example/{article_id}", publisher=publisher,
        published_at=NOW, quoted_text="已核验原文", content_hash="a" * 64,
    )


def event(
    event_id: str, event_type: str, headline: str, *, review_state="verified",
    themes=(), citations=None,
) -> NormalizedNewsEvent:
    linked = ((AssetKind.A_SHARE, "600000"),)
    return NormalizedNewsEvent(
        event_id=event_id, event_type=event_type, headline=headline,
        occurred_at=NOW, normalized_at=NOW, affected_instruments=linked,
        industries=("银行",), themes=themes,
        citations=tuple(citations or (citation(event_id),)),
        association_confidence=Decimal("1"), association_kind="direct",
        association_reasons=("company_code:600000",), review_state=review_state,
    )


def interpretation(
    interpretation_id: str, event_id: str, direction: str, confidence: str,
    *, generated_at=NOW, degraded=False,
) -> AIInterpretation:
    source = citation(event_id).model_copy(update={"published_at": generated_at})
    return AIInterpretation(
        interpretation_id=interpretation_id, event_id=event_id,
        generated_at=generated_at, provider="configured-ai", model="verified-model",
        prompt_version="news-v1", degraded=degraded,
        impact_direction=direction, confidence=Decimal(confidence),
        statements=(InterpretationStatement(
            statement_id=f"statement-{interpretation_id}", kind="fact",
            text="已核验原文", citation_ids=(source.citation_id,),
        ),), citations=(source,),
    )


def test_projection_classifies_all_eight_event_categories_without_inventing_direction() -> None:
    inputs = (
        event("policy", "macro_policy", "国务院发布宏观政策"),
        event("industry", "industrial_policy", "银行行业政策更新"),
        event("announcement", "company_announcement", "公司重大事项公告"),
        event("earnings", "market_news", "公司披露年度净利润"),
        event("capital", "market_news", "公司登上龙虎榜"),
        event("price", "market_news", "公司股价放量异动"),
        event("risk", "risk_event", "公司被立案调查"),
        event("rumor", "market_news", "市场传闻待核验", review_state="pending"),
    )

    result = UnifiedEventProjectionService().project(inputs, (), cutoff=NOW)

    assert [item.category for item in result] == [
        "company_announcement", "capital_dragon_tiger", "earnings_financial",
        "industry_sector", "policy_macro", "price_volume_anomaly",
        "risk_event", "rumor_unverified",
    ]
    assert all(item.direction == "uncertain" for item in result)
    assert all(item.duration == "unknown" for item in result)
    assert all(item.price_reflection == "unknown" for item in result)


def test_projection_uses_latest_eligible_verified_interpretation_and_deduplicates_event_id() -> None:
    original = event(
        "announcement", "company_announcement", "公司公告",
        citations=(citation("official", "上交所"), citation("media", "证券时报")),
    )
    duplicate = original.model_copy(update={"normalized_at": NOW + timedelta(seconds=1)})
    interpretations = (
        interpretation("older", original.event_id, "neutral", "0.72", generated_at=NOW - timedelta(minutes=1)),
        interpretation("latest", original.event_id, "positive", "0.88"),
        interpretation("future", original.event_id, "negative", "0.99", generated_at=NOW + timedelta(minutes=1)),
    )

    result = UnifiedEventProjectionService().project(
        (original, duplicate), interpretations, cutoff=NOW
    )

    assert len(result) == 1
    projected = result[0]
    assert projected.event_id == original.event_id
    assert projected.direction == "positive"
    assert projected.direction_confidence == Decimal("0.88")
    assert projected.strength == "high"
    assert projected.credibility == "multi_source_verified"
    assert projected.source_count == 2
    assert projected.interpretation_id == "latest"


def test_projection_keeps_low_confidence_or_degraded_interpretation_pending() -> None:
    source = event("risk", "risk_event", "风险提示")

    low = UnifiedEventProjectionService().project(
        (source,), (interpretation("low", source.event_id, "negative", "0.69"),),
        cutoff=NOW,
    )[0]
    degraded = UnifiedEventProjectionService().project(
        (source,), (interpretation("degraded", source.event_id, "negative", "0.95", degraded=True),),
        cutoff=NOW,
    )[0]

    assert low.direction == degraded.direction == "uncertain"
    assert low.strength == degraded.strength == "unknown"
    assert low.interpretation_id is None
