from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from qibao_api.a_shares.models import CandidateBoard, CandidateEntry
from qibao_api.contracts.candidate_sentiment import (
    CandidateSentimentBand,
    CandidateSentimentBatch,
    CandidateSentimentComponent,
    CandidateSentimentSnapshot,
)
from qibao_api.contracts.news import AIInterpretation, NormalizedNewsEvent
from qibao_api.gongbu.fund_flow import FundFlowSnapshot


NEWS_WEIGHT = Decimal("40")
HOTSPOT_WEIGHT = Decimal("30")
FUND_FLOW_WEIGHT = Decimal("30")
MINIMUM_COVERAGE = Decimal("60")
MINIMUM_NEWS_CONFIDENCE = Decimal("0.65")


@dataclass(frozen=True)
class CandidateSentimentEvidence:
    news_sync_ready: bool = False
    news_events: tuple[NormalizedNewsEvent, ...] = ()
    news_interpretations: tuple[AIInterpretation, ...] = ()
    hotspot_sync_ready: bool = False
    hotspot_events: tuple[NormalizedNewsEvent, ...] = ()
    fund_flow: FundFlowSnapshot | None = None


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def sentiment_band(score: Decimal) -> CandidateSentimentBand:
    if score < Decimal("20"):
        return "strongly_bearish"
    if score < Decimal("40"):
        return "cautious"
    if score < Decimal("60"):
        return "neutral"
    if score < Decimal("80"):
        return "positive"
    return "overheated"


class CandidateSentimentEvaluator:
    def evaluate(
        self,
        board: CandidateBoard,
        evidence: dict[str, CandidateSentimentEvidence],
        *,
        cutoff: datetime,
        window_start: datetime | None = None,
    ) -> CandidateSentimentBatch:
        if board.snapshot_id is None or board.input_snapshot_hash is None:
            raise ValueError("candidate sentiment requires a frozen candidate board")
        start = window_start or cutoff - timedelta(days=5)
        items = tuple(
            self._item(entry, board, evidence.get(entry.symbol, CandidateSentimentEvidence()), cutoff, start)
            for entry in board.short_term[:20]
        )
        quality: Literal["ready", "partial", "unavailable"] = (
            "ready" if items and all(item.quality == "ready" for item in items)
            else "partial" if any(item.score is not None for item in items)
            else "unavailable"
        )
        return CandidateSentimentBatch(
            candidate_snapshot_id=board.snapshot_id,
            candidate_input_hash=board.input_snapshot_hash,
            as_of=board.as_of,
            cutoff=cutoff,
            quality=quality,
            items=items,
            generated_at=cutoff,
        )

    def _item(
        self,
        entry: CandidateEntry,
        board: CandidateBoard,
        evidence: CandidateSentimentEvidence,
        cutoff: datetime,
        window_start: datetime,
    ) -> CandidateSentimentSnapshot:
        components = (
            self._news(entry.symbol, evidence, cutoff, window_start),
            self._hotspot(entry.symbol, evidence, cutoff, window_start),
            self._fund_flow(entry, evidence, cutoff),
        )
        ready = tuple(component for component in components if component.status == "ready")
        coverage = sum((component.weight for component in ready), Decimal("0"))
        score = None
        if coverage >= MINIMUM_COVERAGE:
            score = (
                sum((component.score * component.weight for component in ready if component.score is not None), Decimal("0"))
                / coverage
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        quality: Literal["ready", "partial", "unavailable"] = (
            "ready" if coverage == Decimal("100")
            else "partial" if score is not None
            else "unavailable"
        )
        band = sentiment_band(score) if score is not None else "unavailable"
        observed_times = [component.observed_at for component in ready if component.observed_at]
        observed_at = max(observed_times, default=cutoff)
        freshness = "stale" if observed_times and min(observed_times) < window_start else "current"
        primary_reason = self._reason(ready, score)
        primary_risk = self._risk(components, score)
        source_ids = tuple(dict.fromkeys(
            evidence_id for component in ready for evidence_id in component.evidence_ids
        ))
        return CandidateSentimentSnapshot(
            candidate_snapshot_id=board.snapshot_id,
            candidate_input_hash=board.input_snapshot_hash,
            symbol=entry.symbol,
            quality=quality,
            freshness=freshness,
            score=score,
            band=band,
            coverage_percent=coverage,
            components=components,
            primary_reason=primary_reason,
            primary_risk=primary_risk,
            beginner_guidance=self._guidance(band),
            observed_at=observed_at,
            generated_at=cutoff,
            source_snapshot_ids=source_ids,
        )

    @staticmethod
    def _valid_event(
        event: NormalizedNewsEvent,
        symbol: str,
        cutoff: datetime,
        window_start: datetime,
    ) -> bool:
        return (
            event.review_state == "verified"
            and event.occurred_at <= cutoff
            and event.normalized_at <= cutoff
            and event.occurred_at >= window_start
            and any(asset.value == "a_share" and code == symbol for asset, code in event.affected_instruments)
        )

    def _news(
        self,
        symbol: str,
        evidence: CandidateSentimentEvidence,
        cutoff: datetime,
        window_start: datetime,
    ) -> CandidateSentimentComponent:
        events = tuple(
            event for event in evidence.news_events
            if event.event_type != "market_hotspot" and self._valid_event(event, symbol, cutoff, window_start)
        )
        if not events:
            if evidence.news_sync_ready:
                return CandidateSentimentComponent(
                    name="news", status="ready", score=Decimal("50"), weight=NEWS_WEIGHT,
                    summary="未发现明确方向事件", observed_at=cutoff,
                )
            return self._unavailable("news", NEWS_WEIGHT, "新闻倾向数据不可用")

        event_ids = {event.event_id for event in events}
        latest: dict[str, AIInterpretation] = {}
        for item in evidence.news_interpretations:
            if (
                item.event_id not in event_ids
                or item.generated_at > cutoff
                or item.degraded
                or item.confidence < MINIMUM_NEWS_CONFIDENCE
                or item.impact_direction == "uncertain"
                or not item.citations
            ):
                continue
            previous = latest.get(item.event_id)
            if previous is None or item.generated_at > previous.generated_at:
                latest[item.event_id] = item
        if not latest:
            return self._unavailable("news", NEWS_WEIGHT, "新闻方向尚未通过置信度门禁")

        direction_scores = {
            "positive": Decimal("75"),
            "neutral": Decimal("50"),
            "negative": Decimal("25"),
        }
        weighted = Decimal("0")
        total_weight = Decimal("0")
        event_by_id = {event.event_id: event for event in events}
        for event_id, item in latest.items():
            age_days = max(0, (cutoff.date() - event_by_id[event_id].occurred_at.date()).days)
            recency = max(Decimal("0.25"), Decimal("1") - Decimal(age_days) * Decimal("0.25"))
            weight = item.confidence * recency
            weighted += direction_scores[item.impact_direction] * weight
            total_weight += weight
        score = (weighted / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        summary = (
            "已核验新闻解释整体偏正面" if score > Decimal("55")
            else "已核验新闻解释整体偏负面" if score < Decimal("45")
            else "已核验新闻解释整体中性"
        )
        ids = tuple(dict.fromkeys([
            *latest.keys(), *(item.interpretation_id for item in latest.values())
        ]))
        return CandidateSentimentComponent(
            name="news", status="ready", score=score, weight=NEWS_WEIGHT,
            summary=summary, observed_at=max(item.generated_at for item in latest.values()),
            evidence_ids=ids,
        )

    def _hotspot(
        self,
        symbol: str,
        evidence: CandidateSentimentEvidence,
        cutoff: datetime,
        window_start: datetime,
    ) -> CandidateSentimentComponent:
        events = tuple(
            event for event in evidence.hotspot_events
            if event.event_type == "market_hotspot" and self._valid_event(event, symbol, cutoff, window_start)
        )
        if not events and not evidence.hotspot_sync_ready:
            return self._unavailable("hotspot", HOTSPOT_WEIGHT, "题材热点数据不可用")
        score = (
            Decimal("40") if not events
            else Decimal("65") if len(events) == 1
            else Decimal("80") if len(events) == 2
            else Decimal("90")
        )
        summary = (
            "当前未进入已核验热点榜" if not events
            else "出现一次已核验题材热点" if len(events) == 1
            else "题材热点正在延续"
        )
        return CandidateSentimentComponent(
            name="hotspot", status="ready", score=score, weight=HOTSPOT_WEIGHT,
            summary=summary,
            observed_at=max((event.normalized_at for event in events), default=cutoff),
            evidence_ids=tuple(event.event_id for event in events),
        )

    def _fund_flow(
        self,
        entry: CandidateEntry,
        evidence: CandidateSentimentEvidence,
        cutoff: datetime,
    ) -> CandidateSentimentComponent:
        snapshot = evidence.fund_flow
        if (
            snapshot is None
            or snapshot.observed_at > cutoff
            or snapshot.latest_trade_date > entry.factor_snapshot.as_of
            or entry.factor_snapshot.liquidity_amount_20d <= 0
        ):
            return self._unavailable("fund_flow", FUND_FLOW_WEIGHT, "资金方向数据不可用")
        denominator = entry.factor_snapshot.liquidity_amount_20d * Decimal("5")
        ratio = _clamp(snapshot.main_net_5d / denominator, Decimal("-0.2"), Decimal("0.2"))
        adjustment = (
            Decimal("5") if snapshot.intraday_main_net is not None and snapshot.intraday_main_net > 0
            else Decimal("-5") if snapshot.intraday_main_net is not None and snapshot.intraday_main_net < 0
            else Decimal("0")
        )
        score = _clamp(Decimal("50") + ratio * Decimal("150") + adjustment, Decimal("0"), Decimal("100"))
        summary = (
            "近 5 日主力资金偏流入" if score > Decimal("55")
            else "近 5 日主力资金偏流出" if score < Decimal("45")
            else "近 5 日主力资金大致均衡"
        )
        return CandidateSentimentComponent(
            name="fund_flow", status="ready", score=score, weight=FUND_FLOW_WEIGHT,
            summary=summary, observed_at=snapshot.observed_at,
            evidence_ids=(snapshot.snapshot_id,),
        )

    @staticmethod
    def _unavailable(name, weight: Decimal, summary: str) -> CandidateSentimentComponent:
        return CandidateSentimentComponent(
            name=name, status="unavailable", score=None, weight=weight, summary=summary,
        )

    @staticmethod
    def _reason(components, score: Decimal | None) -> str:
        if not components:
            return "可验证情绪数据不足。"
        selected = (
            max(components, key=lambda component: component.score or Decimal("0"))
            if score is not None and score >= Decimal("60")
            else min(components, key=lambda component: component.score or Decimal("100"))
        )
        return selected.summary + "。"

    @staticmethod
    def _risk(components, score: Decimal | None) -> str:
        values = {component.name: component for component in components}
        hotspot = values["hotspot"]
        news = values["news"]
        funds = values["fund_flow"]
        if hotspot.score is not None and hotspot.score >= Decimal("80"):
            return "题材热度较高，追涨和拥挤风险上升。"
        if news.score is not None and news.score < Decimal("40"):
            return "冻结新闻解释偏负面，需观察事件是否继续发酵。"
        if funds.score is not None and funds.score < Decimal("40"):
            return "主力资金方向偏弱，短线承接可能不足。"
        if any(component.status == "unavailable" for component in components):
            return "部分情绪分项不可用，结论可信度受限。"
        if score is not None and score >= Decimal("80"):
            return "综合情绪过热，高分不代表低风险。"
        return "情绪可能快速变化，需结合价格和风险条件复核。"

    @staticmethod
    def _guidance(band: CandidateSentimentBand) -> str:
        return {
            "strongly_bearish": "先回避情绪冲击，等待负面证据减弱。",
            "cautious": "保持谨慎观察，不因单一热点追涨。",
            "neutral": "等待新闻、热点和资金形成一致方向。",
            "positive": "可继续观察，但必须同时核对风险和失效条件。",
            "overheated": "关注拥挤和回落风险，不把高热度当成安全。",
            "unavailable": "等待至少两类情绪数据完成核验。",
        }[band]
