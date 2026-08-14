from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import AIInterpretation, NormalizedNewsEvent
from qibao_api.contracts.unified_event import (
    ImpactStrength,
    UnifiedDecisionEvent,
    UnifiedEventCategory,
)


_CATEGORY_FOLLOW_UP: dict[UnifiedEventCategory, tuple[str, ...]] = {
    "policy_macro": ("观察政策落地文件、市场成交额与风险偏好",),
    "industry_sector": ("观察板块成交额、涨停扩散和龙头持续性",),
    "company_announcement": ("核对公告执行进度、后续公告和交易所问询",),
    "earnings_financial": ("核对财报原文、现金流、利润质量和后续指引",),
    "capital_dragon_tiger": ("观察龙虎榜席位、主力净流向和次日承接",),
    "price_volume_anomaly": ("观察量价持续性、回落幅度和板块联动",),
    "risk_event": ("核对监管公告、风险进展和交易限制变化",),
    "rumor_unverified": ("等待权威来源或公司公告核验，不据此形成方向判断",),
}


def _event_text(event: NormalizedNewsEvent) -> str:
    return " ".join((
        event.event_type, event.headline, *event.industries, *event.themes,
    )).lower()


def _category(event: NormalizedNewsEvent) -> tuple[UnifiedEventCategory, str]:
    text = _event_text(event)
    if event.review_state != "verified" or any(
        word in text for word in ("传闻", "rumor", "待核验", "未经证实")
    ):
        return "rumor_unverified", f"review_state:{event.review_state}"
    if event.event_type in {"risk_event", "credit_risk", "regulatory_risk"} or any(
        word in text for word in ("风险", "立案", "处罚", "诉讼", "退市", "违约")
    ):
        return "risk_event", f"event_type:{event.event_type}"
    if any(word in text for word in ("龙虎榜", "大宗交易", "主力资金", "北向资金")):
        return "capital_dragon_tiger", "capital_flow_keyword"
    if any(word in text for word in ("异动", "涨停", "跌停", "放量", "成交量", "换手")):
        return "price_volume_anomaly", "price_volume_keyword"
    if any(word in text for word in ("业绩", "财报", "净利润", "营业收入", "现金流", "分红")):
        return "earnings_financial", "financial_keyword"
    if event.event_type in {
        "company_announcement", "market_announcement", "announcement"
    } or "公告" in text:
        return "company_announcement", f"event_type:{event.event_type}"
    if event.event_type in {"macro_policy", "policy_macro"} or any(
        word in text for word in ("国务院", "央行", "财政部", "宏观政策")
    ):
        return "policy_macro", f"event_type:{event.event_type}"
    return "industry_sector", f"event_type:{event.event_type}"


def _strength(confidence: Decimal) -> ImpactStrength:
    if confidence >= Decimal("0.85"):
        return "high"
    if confidence >= Decimal("0.70"):
        return "medium"
    return "low"


class UnifiedEventProjectionService:
    def project(
        self,
        events: Iterable[NormalizedNewsEvent],
        interpretations: Iterable[AIInterpretation],
        *,
        cutoff: datetime,
    ) -> tuple[UnifiedDecisionEvent, ...]:
        effective_events: dict[str, NormalizedNewsEvent] = {}
        for event in events:
            if event.occurred_at > cutoff or event.normalized_at > cutoff:
                continue
            current = effective_events.get(event.event_id)
            if current is None or event.normalized_at > current.normalized_at:
                effective_events[event.event_id] = event

        latest_interpretations: dict[str, AIInterpretation] = {}
        for item in interpretations:
            if item.generated_at > cutoff or item.event_id not in effective_events:
                continue
            current = latest_interpretations.get(item.event_id)
            if current is None or item.generated_at > current.generated_at:
                latest_interpretations[item.event_id] = item

        projected = [
            self._project_one(event, latest_interpretations.get(event.event_id))
            for event in effective_events.values()
        ]
        return tuple(sorted(projected, key=lambda item: (item.occurred_at, item.event_id)))

    @staticmethod
    def _project_one(
        event: NormalizedNewsEvent,
        interpretation: AIInterpretation | None,
    ) -> UnifiedDecisionEvent:
        category, category_reason = _category(event)
        publishers = {
            citation.publisher.strip()
            for citation in event.citations if citation.publisher.strip()
        }
        source_count = max(1, len(publishers))
        credibility = (
            "rejected" if event.review_state == "rejected"
            else "pending" if event.review_state != "verified"
            else "multi_source_verified" if source_count > 1
            else "verified"
        )
        eligible_interpretation = (
            interpretation
            if interpretation is not None
            and not interpretation.degraded
            and interpretation.confidence >= Decimal("0.70")
            and interpretation.impact_direction in {"positive", "negative", "neutral"}
            else None
        )
        return UnifiedDecisionEvent(
            event_id=event.event_id,
            source_event_type=event.event_type,
            category=category,
            category_reason=category_reason,
            headline=event.headline,
            occurred_at=event.occurred_at,
            affected_symbols=tuple(
                symbol for asset, symbol in event.affected_instruments
                if asset is AssetKind.A_SHARE
            ),
            industries=event.industries,
            themes=event.themes,
            direction=(
                eligible_interpretation.impact_direction
                if eligible_interpretation is not None else "uncertain"
            ),
            direction_confidence=(
                eligible_interpretation.confidence
                if eligible_interpretation is not None else None
            ),
            strength=(
                _strength(eligible_interpretation.confidence)
                if eligible_interpretation is not None else "unknown"
            ),
            credibility=credibility,
            source_count=source_count,
            duration="unknown",
            price_reflection="unknown",
            follow_up_indicators=_CATEGORY_FOLLOW_UP[category],
            interpretation_id=(
                eligible_interpretation.interpretation_id
                if eligible_interpretation is not None else None
            ),
            evidence_ids=tuple(dict.fromkeys(
                str(
                    getattr(citation, "citation_id", None)
                    or getattr(citation, "article_id", None)
                    or event.event_id
                )
                for citation in event.citations
            )) or (event.event_id,),
        )
