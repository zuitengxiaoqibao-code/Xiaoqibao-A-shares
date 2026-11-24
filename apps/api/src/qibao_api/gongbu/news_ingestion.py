import asyncio
import hashlib
import json
from datetime import datetime, timezone

from qibao_api.contracts.market import AssetKind
from qibao_api.gongbu.news_collection import deduplicate_articles
from qibao_api.gongbu.news_quality_policy import NewsQualityPolicy


class NewsIngestionService:
    def __init__(
        self, source, repository, linker, compliance, ai_gateway=None, *,
        stock_source=None, max_ai_interpretations_per_sync=10,
        realtime_snapshot_bus=None,
    ) -> None:
        self.source = source
        self.stock_source = stock_source
        self.repository = repository
        self.linker = linker
        self.compliance = compliance
        self.ai_gateway = ai_gateway
        self.quality_policy = NewsQualityPolicy()
        self.max_ai_interpretations_per_sync = max_ai_interpretations_per_sync
        self.realtime_snapshot_bus = realtime_snapshot_bus

    async def sync(self) -> dict[str, int]:
        await asyncio.to_thread(self.compliance.require_feature_sources, "market_news", AssetKind.A_SHARE)
        articles = await self.source.fetch()
        return await self._ingest(articles)

    async def sync_symbol(self, symbol: str) -> dict[str, int]:
        await asyncio.to_thread(self.compliance.require_feature_sources, "market_news", AssetKind.A_SHARE)
        if self.stock_source is None:
            return {
                "fetched": 0, "inserted": 0, "clusters": 0, "events": 0,
                "interpretations": 0,
            }
        articles = await self.stock_source.fetch(symbol)
        return await self._ingest(
            articles,
            context_instruments=((AssetKind.A_SHARE, symbol),),
        )

    async def _ingest(
        self,
        articles,
        *,
        context_instruments: tuple[tuple[AssetKind, str], ...] = (),
    ) -> dict[str, int]:
        accepted_articles = []
        for article in articles:
            # Linking reads the instrument directory, which may be locked by
            # a concurrent data repair. Keep that wait off the API event loop.
            event = await asyncio.to_thread(
                self.linker.link, article, context_instruments=context_instruments,
            )
            if self.quality_policy.evaluate(article, event).accepted:
                accepted_articles.append(article)
        clusters = deduplicate_articles(accepted_articles)
        inserted = await asyncio.to_thread(self.repository.append_articles, tuple(accepted_articles))
        for cluster in clusters:
            await asyncio.to_thread(self.repository.append_cluster, cluster)
        article_ids = tuple(article.article_id for article in accepted_articles)
        article_by_id = {
            article.article_id: article
            for article in await asyncio.to_thread(self.repository.articles_by_ids, article_ids)
        }
        event_count = 0
        interpretation_count = 0
        generated_count = 0
        interpretations = tuple(await asyncio.to_thread(self.repository.interpretations))
        for cluster in clusters:
            primary = article_by_id[cluster.primary_article_id]
            event = await asyncio.to_thread(
                self.linker.link, primary, context_instruments=context_instruments,
            )
            event_inserted, event_corrected = await asyncio.to_thread(self.repository.reconcile_event, event)
            event_count += int(event_inserted)
            needs_interpretation = False
            if self.ai_gateway is not None:
                checker = getattr(self.ai_gateway, "needs_interpretation", None)
                needs_interpretation = bool(
                    checker is not None
                    and checker(event.event_id, interpretations)
                )
            should_interpret = (
                self.ai_gateway is not None
                and generated_count < self.max_ai_interpretations_per_sync
                and (event_inserted or event_corrected or needs_interpretation)
            )
            if should_interpret:
                generated_count += 1
                interpretation = await self.ai_gateway.interpret(event)
                appended = await asyncio.to_thread(self.repository.append_interpretation, interpretation)
                interpretation_count += int(appended)
                if appended:
                    interpretations = (*interpretations, interpretation)
        archive_expired = getattr(self.repository, "archive_expired", None)
        if callable(archive_expired):
            await asyncio.to_thread(archive_expired, now=articles[0].fetched_at if articles else None)
        result = {
            "fetched": len(articles),
            "inserted": inserted,
            "clusters": len(clusters),
            "events": event_count,
            "interpretations": interpretation_count,
        }
        await asyncio.to_thread(self._publish_realtime_snapshot)
        return result

    def _publish_realtime_snapshot(self) -> None:
        bus = self.realtime_snapshot_bus
        if bus is None or not hasattr(bus, "publish"):
            return
        events = tuple(
            event for event in self.repository.effective_events(cutoff=datetime.now(timezone.utc))
            if event.review_state == "verified"
        )
        encoded = json.dumps(
            [event.model_dump(mode="json") for event in events],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        snapshot_id = hashlib.sha256(encoded).hexdigest()
        latest = bus.latest("news_events") if hasattr(bus, "latest") else None
        previous = latest.get("payload") if isinstance(latest, dict) else None
        if isinstance(previous, dict) and previous.get("snapshot_id") == snapshot_id:
            return
        observed = max((event.normalized_at for event in events), default=datetime.now(timezone.utc))
        bus.publish(
            "news_events",
            {
                "snapshot_id": snapshot_id,
                "events": [event.model_dump(mode="json") for event in events[-50:]],
                "event_count": len(events),
                "verified_count": len(events),
            },
            observed_at=observed,
            source="news-repository",
            freshness="verified",
        )
