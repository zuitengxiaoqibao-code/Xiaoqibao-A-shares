from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news_alerts import BreakingNewsAlert, BreakingNewsAlertResponse


class BreakingNewsAlertService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def current(
        self,
        cutoff: datetime,
        *,
        symbol: str | None = None,
        limit: int = 30,
        events: list | tuple | None = None,
    ) -> BreakingNewsAlertResponse:
        normalized_cutoff = cutoff.astimezone(timezone.utc)
        source_events = (
            events
            if events is not None
            else self.repository.effective_events(cutoff=normalized_cutoff)
        )
        events = [
            event for event in source_events
            if event.occurred_at.astimezone(timezone.utc) <= normalized_cutoff
            and event.normalized_at.astimezone(timezone.utc) <= normalized_cutoff
            and event.review_state != "rejected"
        ]
        events.sort(key=lambda event: event.occurred_at, reverse=True)
        if symbol is None:
            events = [
                event for event in events
                if any(
                    asset is AssetKind.A_SHARE
                    for asset, _code in event.affected_instruments
                )
            ]
            events = events[:limit]
        interpretations = self.repository.latest_interpretations_by_event(
            tuple(event.event_id for event in events), normalized_cutoff
        )
        alerts: list[BreakingNewsAlert] = []
        for event in events:
            affected_symbols = tuple(
                code for asset, code in event.affected_instruments
                if asset is AssetKind.A_SHARE
            )
            if symbol is not None and symbol not in affected_symbols:
                continue
            articles = self._source_articles(event)
            verified_articles = [article for article in articles if article.source_verified]
            independent_sources = {
                (article.publisher.casefold(), (urlsplit(article.canonical_url).hostname or "").casefold())
                for article in verified_articles
            }
            if event.review_state == "pending":
                verification_state = "pending"
            elif not verified_articles:
                verification_state = "unverified"
            elif len(independent_sources) >= 2:
                verification_state = "multi_source_confirmed"
            else:
                verification_state = "verified"
            age = normalized_cutoff - event.occurred_at.astimezone(timezone.utc)
            stock_linked = event.association_kind in {"direct", "context"}
            confirmed = verification_state in {"verified", "multi_source_confirmed"}
            urgency = (
                "breaking" if stock_linked and confirmed and timedelta(0) <= age <= timedelta(minutes=120)
                else "tracking" if stock_linked
                else "normal"
            )
            if symbol is not None and (urgency == "normal" or verification_state == "unverified"):
                continue
            interpretation = interpretations.get(event.event_id)
            ai_degraded = interpretation is None or interpretation.degraded
            direction = "uncertain" if ai_degraded else interpretation.impact_direction
            confidence = None if ai_degraded else interpretation.confidence
            source_items = verified_articles or articles
            publishers = tuple(dict.fromkeys(article.publisher for article in source_items))
            source_urls = tuple(dict.fromkeys(article.canonical_url for article in source_items))
            alerts.append(BreakingNewsAlert(
                event_id=event.event_id,
                headline=event.headline,
                occurred_at=event.occurred_at,
                verification_state=verification_state,
                urgency=urgency,
                association_kind=event.association_kind,
                association_reasons=event.association_reasons,
                affected_symbols=affected_symbols,
                themes=event.themes,
                publishers=publishers,
                source_urls=source_urls,
                source_count=max(1, len(independent_sources)),
                impact_direction=direction,
                impact_confidence=confidence,
                ai_degraded=ai_degraded,
            ))
        alerts.sort(key=lambda item: item.occurred_at, reverse=True)
        selected = tuple(alerts[:limit])
        return BreakingNewsAlertResponse(
            status="ready" if selected else "empty",
            observed_at=normalized_cutoff,
            alerts=selected,
            sources=tuple(dict.fromkeys(publisher for item in selected for publisher in item.publishers)),
        )

    def _source_articles(self, event):
        article_ids: list[str] = []
        for citation in event.citations:
            cluster = self.repository.cluster_for_article(citation.article_id)
            article_ids.extend(cluster.article_ids if cluster else (citation.article_id,))
        return self.repository.articles_by_ids(tuple(dict.fromkeys(article_ids)))
