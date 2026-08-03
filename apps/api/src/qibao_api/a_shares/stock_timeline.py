from datetime import date, datetime
from zoneinfo import ZoneInfo

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.stock_timeline import (
    StockTimelineEvent,
    StockTimelineResponse,
)
from qibao_api.a_shares.news_alerts import BreakingNewsAlertService


CHINA_TZ = ZoneInfo("Asia/Shanghai")


class StockTimelineService:
    def __init__(self, bar_repository, news_repository) -> None:
        self.bar_repository = bar_repository
        self.news_repository = news_repository
        self.news_alert_service = BreakingNewsAlertService(news_repository)

    def get(
        self,
        symbol: str,
        as_of: date,
        cutoff: datetime,
        *,
        limit: int = 120,
    ) -> StockTimelineResponse:
        bars = tuple(sorted(
            (
                item for item in self.bar_repository.latest(
                    symbol, limit, cutoff=cutoff,
                )
                if item.trade_date <= as_of
            ),
            key=lambda item: item.trade_date,
        ))
        if not bars:
            return StockTimelineResponse(
                symbol=symbol,
                as_of=as_of,
                cutoff=cutoff,
                status="unavailable",
                bars=(),
                events=(),
                sources=(),
                warnings=("local_daily_bars_unavailable",),
            )

        first_date = bars[0].trade_date
        trade_dates = {item.trade_date for item in bars}
        candidates = [
            event
            for event in self.news_repository.effective_events_for_symbol(
                symbol, cutoff=cutoff,
            )
            if self._eligible_event(event, symbol, first_date, as_of, cutoff)
        ]
        candidates.sort(key=lambda item: (item.occurred_at, item.event_id))
        alert_response = self.news_alert_service.current(
            cutoff,
            symbol=symbol,
            limit=max(limit, len(candidates)),
        )
        alerts = {item.event_id: item for item in alert_response.alerts}
        candidates = [event for event in candidates if event.event_id in alerts]

        events = tuple(
            self._event_payload(
                event,
                mapped_trade_date=(
                    event.occurred_at.astimezone(CHINA_TZ).date()
                    if event.occurred_at.astimezone(CHINA_TZ).date() in trade_dates
                    else None
                ),
                alert=alerts[event.event_id],
            )
            for event in candidates
        )
        sources = tuple(dict.fromkeys((
            *(item.source for item in bars),
            "verified-market-news",
        )))
        warnings = tuple(
            f"event_without_matching_trade_date:{item.event_id}"
            for item in events
            if item.mapped_trade_date is None
        )
        if not events:
            warnings = ("verified_stock_events_unavailable",)
        return StockTimelineResponse(
            symbol=symbol,
            as_of=as_of,
            cutoff=cutoff,
            status="ready",
            bars=bars,
            events=events,
            sources=sources,
            warnings=warnings,
        )

    @staticmethod
    def _eligible_event(event, symbol, first_date, as_of, cutoff) -> bool:
        local_date = event.occurred_at.astimezone(CHINA_TZ).date()
        linked = (AssetKind.A_SHARE, symbol) in event.affected_instruments
        return (
            event.event_type == "market_news"
            and event.review_state == "verified"
            and linked
            and event.occurred_at <= cutoff
            and first_date <= local_date <= as_of
        )

    @staticmethod
    def _event_payload(event, *, mapped_trade_date, alert):
        citation = event.citations[0]
        label = next(iter(event.themes), None) or next(
            iter(event.industries), None
        ) or event.headline
        return StockTimelineEvent(
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            mapped_trade_date=mapped_trade_date,
            label=label,
            headline=event.headline,
            direction=alert.impact_direction,
            confidence=alert.impact_confidence,
            themes=event.themes,
            industries=event.industries,
            publisher=citation.publisher,
            source_url=citation.canonical_url,
            association_confidence=event.association_confidence,
            association_kind=alert.association_kind,
            association_reasons=alert.association_reasons,
            verification_state=alert.verification_state,
            source_count=alert.source_count,
            urgency=alert.urgency,
        )
