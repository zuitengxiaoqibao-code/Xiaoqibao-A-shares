from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.stock_timeline import (
    StockTimelineEvent,
    StockTimelineMinutePoint,
    StockTimelineResponse,
)
from qibao_api.a_shares.news_alerts import BreakingNewsAlertService
from qibao_api.a_shares.unified_events import UnifiedEventProjectionService


CHINA_TZ = ZoneInfo("Asia/Shanghai")


class StockTimelineService:
    def __init__(
        self,
        bar_repository,
        news_repository,
        *,
        poll_state_repository=None,
        trading_calendar=None,
        live_feed=None,
        minute_source=None,
    ) -> None:
        self.bar_repository = bar_repository
        self.news_repository = news_repository
        self.news_alert_service = BreakingNewsAlertService(news_repository)
        self.poll_state_repository = poll_state_repository
        self.trading_calendar = trading_calendar
        self.live_feed = live_feed
        # A live quote is only a single observation.  The optional minute
        # source supplies the real session history needed to draw a curve.
        self.minute_source = minute_source

    def get(
        self,
        symbol: str,
        as_of: date,
        cutoff: datetime,
        *,
        limit: int = 120,
    ) -> StockTimelineResponse:
        (
            intraday_status,
            intraday_points,
            intraday_sources,
            intraday_warnings,
        ) = self._intraday(symbol, as_of, cutoff)
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
                intraday_status=intraday_status,
                intraday_points=intraday_points,
                intraday_sources=intraday_sources,
                intraday_warnings=intraday_warnings,
            )

        first_date = bars[0].trade_date
        trade_dates = {item.trade_date for item in bars}
        candidates = [
            event
            for event in self.news_repository.events_for_symbol(
                symbol,
                cutoff=cutoff,
                since=datetime.combine(first_date, time.min, tzinfo=CHINA_TZ),
                limit=max(1, limit * 4),
            )
            if self._eligible_event(event, symbol, first_date, as_of, cutoff)
        ]
        candidates.sort(key=lambda item: (item.occurred_at, item.event_id))
        alert_response = self.news_alert_service.current(
            cutoff,
            symbol=symbol,
            limit=max(limit, len(candidates)),
            events=candidates,
        )
        alerts = {item.event_id: item for item in alert_response.alerts}
        candidates = [event for event in candidates if event.event_id in alerts]
        interpretations = self.news_repository.interpretations_for_events(
            tuple(item.event_id for item in candidates), cutoff=cutoff,
        )
        projections = {
            item.event_id: item
            for item in UnifiedEventProjectionService().project(
                candidates, interpretations, cutoff=cutoff
            )
        }

        events = tuple(
            self._event_payload(
                event,
                mapped_trade_date=(
                    event.occurred_at.astimezone(CHINA_TZ).date()
                    if event.occurred_at.astimezone(CHINA_TZ).date() in trade_dates
                    else None
                ),
                alert=alerts[event.event_id],
                projection=projections[event.event_id],
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
            intraday_status=intraday_status,
            intraday_points=intraday_points,
            intraday_sources=intraday_sources,
            intraday_warnings=intraday_warnings,
        )

    def _intraday(self, symbol: str, as_of: date, cutoff: datetime):
        if self.poll_state_repository is None:
            return "unavailable", (), (), ("intraday_repository_unavailable",)
        try:
            snapshots = self.poll_state_repository.intraday_snapshots(
                symbol,
                as_of,
                cutoff=cutoff,
            )
        except Exception:
            return "unavailable", (), (), ("intraday_snapshot_read_failed",)
        points = tuple(
            StockTimelineMinutePoint.model_validate(item.model_dump())
            for item in sorted(snapshots, key=lambda item: item.observed_at)
        )
        local_cutoff = cutoff.astimezone(CHINA_TZ)
        trading_day = (
            self.trading_calendar is None
            or self.trading_calendar.is_trading_day(as_of)
        )
        if not trading_day:
            if points:
                sources = tuple(dict.fromkeys(item.source for item in points))
                return "ready", points, sources, ()
            return "unavailable", (), (), ("market_closed",)

        # The poll archive is intentionally sparse (one snapshot per polling
        # cycle).  On the current trading day, fill a sparse archive from the
        # real Tencent minute endpoint and merge by minute.  This never
        # fabricates intermediate prices and keeps an archived point when it
        # is newer than the remote response.
        if (
            self.minute_source is not None
            and as_of == local_cutoff.date()
            and len(points) < 5
        ):
            try:
                remote = self.minute_source.fetch_stock_minutes(
                    symbol, cutoff=cutoff,
                )
                remote_points = tuple(
                    StockTimelineMinutePoint.model_validate(item.model_dump())
                    for item in remote
                    if item.observed_at.astimezone(CHINA_TZ).date() == as_of
                )
            except Exception:
                remote_points = ()
            if remote_points:
                by_observed_at = {item.observed_at: item for item in remote_points}
                by_observed_at.update({item.observed_at: item for item in points})
                points = tuple(sorted(by_observed_at.values(), key=lambda item: item.observed_at))

        if points:
            sources = tuple(dict.fromkeys(item.source for item in points))
            return "ready", points, sources, ()

        if self.live_feed is not None and as_of == local_cutoff.date():
            try:
                live_snapshots = self.live_feed.snapshot_many((symbol,), cutoff=cutoff)
                live_points = tuple(
                    StockTimelineMinutePoint.model_validate(item.model_dump())
                    for item in live_snapshots
                    if item.observed_at.astimezone(CHINA_TZ).date() == as_of
                )
            except Exception:
                live_points = ()
            if live_points:
                live_points = tuple(sorted(live_points, key=lambda item: item.observed_at))
                sources = tuple(dict.fromkeys(item.source for item in live_points))
                return "ready", live_points, sources, ("intraday_live_snapshot",)
        if as_of != local_cutoff.date():
            return "unavailable", (), (), ("intraday_snapshots_unavailable",)
        if local_cutoff.time() < time(9, 30):
            return "waiting", (), (), ("market_not_open",)
        if local_cutoff.time() <= time(15, 0):
            return "waiting", (), (), ("intraday_waiting_for_first_snapshot",)
        return "unavailable", (), (), ("intraday_snapshots_unavailable",)

    @staticmethod
    def _eligible_event(event, symbol, first_date, as_of, cutoff) -> bool:
        local_date = event.occurred_at.astimezone(CHINA_TZ).date()
        linked = (AssetKind.A_SHARE, symbol) in event.affected_instruments
        return (
            event.event_type in {"market_news", "market_announcement", "company_announcement", "announcement"}
            and event.review_state == "verified"
            and linked
            and event.occurred_at <= cutoff
            and first_date <= local_date <= as_of
        )

    @staticmethod
    def _event_payload(event, *, mapped_trade_date, alert, projection):
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
            category=projection.category,
            strength=projection.strength,
            credibility=(
                "multi_source_verified" if alert.source_count > 1
                else projection.credibility
            ),
            duration=projection.duration,
            price_reflection=projection.price_reflection,
            follow_up_indicators=projection.follow_up_indicators,
        )
