import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from qibao_api.a_shares.candidate_sentiment import (
    CandidateSentimentEvaluator,
    CandidateSentimentEvidence,
)
from qibao_api.a_shares.candidate_sentiment_repository import (
    CandidateSentimentRepository,
)
from qibao_api.a_shares.models import CandidateBoard
from qibao_api.a_shares.repository import AShareResearchStoreError
from qibao_api.contracts.candidate_sentiment import CandidateSentimentBatch
from qibao_api.gongbu.fund_flow import FundFlowIntegrityError
from qibao_api.gongbu.news_repository import NewsIntegrityError
from qibao_api.libu_compliance.repository import SourceAuthorizationError


REFRESH_TTL = timedelta(minutes=15)
MAX_CANDIDATES = 20
MAX_SOURCE_CONCURRENCY = 4
_SOURCE_ERRORS = (
    SourceAuthorizationError,
    OSError,
    httpx.HTTPError,
    ValueError,
    NewsIntegrityError,
    FundFlowIntegrityError,
)


class CandidateSentimentInputError(ValueError):
    pass


class CandidateSnapshotNotFoundError(CandidateSentimentInputError):
    pass


class CandidateSentimentService:
    def __init__(
        self,
        *,
        research_repository,
        sentiment_repository: CandidateSentimentRepository,
        news_repository,
        fund_flow_repository,
        evaluator: CandidateSentimentEvaluator,
        news_ingestion_service=None,
        hotspot_ingestion_service=None,
        fund_flow_service=None,
    ) -> None:
        self.research_repository = research_repository
        self.sentiment_repository = sentiment_repository
        self.news_repository = news_repository
        self.fund_flow_repository = fund_flow_repository
        self.evaluator = evaluator
        self.news_ingestion_service = news_ingestion_service
        self.hotspot_ingestion_service = hotspot_ingestion_service
        self.fund_flow_service = fund_flow_service
        self._refresh_cache: dict[tuple[str, str], CandidateSentimentBatch] = {}
        self._refresh_lock = asyncio.Lock()

    def current(
        self,
        candidate_snapshot_id: str,
        cutoff: datetime,
    ) -> CandidateSentimentBatch:
        cutoff = self._normalized_cutoff(cutoff)
        board = self._candidate_board(candidate_snapshot_id)
        latest = self.sentiment_repository.latest(
            board.input_snapshot_hash,
            cutoff=cutoff,
        )
        if latest is not None and latest.candidate_snapshot_id == candidate_snapshot_id:
            return latest
        readiness = {
            item.symbol: (False, False)
            for item in board.short_term[:MAX_CANDIDATES]
        }
        return self._evaluate_and_store(board, cutoff, readiness)

    async def refresh(
        self,
        candidate_snapshot_id: str,
        cutoff: datetime,
    ) -> CandidateSentimentBatch:
        cutoff = self._normalized_cutoff(cutoff)
        board = self._candidate_board(candidate_snapshot_id)
        cache_key = (candidate_snapshot_id, board.input_snapshot_hash)
        async with self._refresh_lock:
            cached = self._refresh_cache.get(cache_key)
            if cached is not None and self._is_fresh(cached, cutoff):
                return cached

            hotspot_ready = await self._sync_hotspot(board, cutoff)
            readiness = await self._sync_symbols(board, hotspot_ready)
            result = self._evaluate_and_store(board, cutoff, readiness)
            self._refresh_cache[cache_key] = result
            return result

    def _candidate_board(self, candidate_snapshot_id: str) -> CandidateBoard:
        try:
            board = self.research_repository.get_candidate_board(candidate_snapshot_id)
        except KeyError as error:
            raise CandidateSnapshotNotFoundError(candidate_snapshot_id) from error
        except AShareResearchStoreError as error:
            if isinstance(error.__cause__, KeyError):
                raise CandidateSnapshotNotFoundError(candidate_snapshot_id) from error
            raise
        if board.snapshot_id != candidate_snapshot_id:
            raise CandidateSentimentInputError("candidate snapshot identity differs")
        if board.input_snapshot_hash is None:
            raise CandidateSentimentInputError("candidate snapshot is not frozen")
        return board

    async def _sync_hotspot(self, board: CandidateBoard, cutoff: datetime) -> bool:
        if self.hotspot_ingestion_service is None:
            return False
        try:
            await asyncio.to_thread(
                self.hotspot_ingestion_service.sync,
                board.as_of,
                fetched_at=cutoff,
            )
        except _SOURCE_ERRORS:
            return False
        return True

    async def _sync_symbols(
        self,
        board: CandidateBoard,
        hotspot_ready: bool,
    ) -> dict[str, tuple[bool, bool]]:
        symbols = [item.symbol for item in board.short_term[:MAX_CANDIDATES]]
        semaphore = asyncio.Semaphore(MAX_SOURCE_CONCURRENCY)
        work: list[Awaitable[tuple[str, str, bool]]] = []
        for symbol in symbols:
            if self.news_ingestion_service is not None:
                work.append(self._attempt_source(
                    "news",
                    symbol,
                    self.news_ingestion_service.sync_symbol,
                    semaphore,
                ))
            if self.fund_flow_service is not None:
                work.append(self._attempt_source(
                    "fund_flow",
                    symbol,
                    self.fund_flow_service.sync_symbol,
                    semaphore,
                ))
        results = await asyncio.gather(*work) if work else []
        news_ready = {symbol: False for symbol in symbols}
        for source, symbol, ready in results:
            if source == "news":
                news_ready[symbol] = ready
        return {
            symbol: (news_ready[symbol], hotspot_ready)
            for symbol in symbols
        }

    @staticmethod
    async def _attempt_source(
        source: str,
        symbol: str,
        sync: Callable[[str], Awaitable[Any]],
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, str, bool]:
        try:
            async with semaphore:
                await sync(symbol)
        except _SOURCE_ERRORS:
            return source, symbol, False
        return source, symbol, True

    def _evaluate_and_store(
        self,
        board: CandidateBoard,
        cutoff: datetime,
        readiness: dict[str, tuple[bool, bool]],
    ) -> CandidateSentimentBatch:
        evidence: dict[str, CandidateSentimentEvidence] = {}
        source_payload: dict[str, dict[str, Any]] = {}
        for entry in board.short_term[:MAX_CANDIDATES]:
            news_ready, hotspot_ready = readiness.get(entry.symbol, (False, False))
            events = ()
            event_read_ready = False
            try:
                events = tuple(self.news_repository.effective_events_for_symbol(
                    entry.symbol,
                    cutoff=cutoff,
                ))
                event_read_ready = True
            except _SOURCE_ERRORS:
                pass

            news_events = tuple(
                item for item in events if item.event_type != "market_hotspot"
            )
            hotspot_events = tuple(
                item for item in events if item.event_type == "market_hotspot"
            )
            interpretations = ()
            if news_events:
                try:
                    interpretations = tuple(
                        self.news_repository.interpretations_for_events(
                            tuple(item.event_id for item in news_events),
                            cutoff=cutoff,
                        )
                    )
                except _SOURCE_ERRORS:
                    news_ready = False

            fund_flow = None
            try:
                fund_flow = self.fund_flow_repository.latest(
                    entry.symbol,
                    board.as_of,
                    cutoff=cutoff,
                )
            except _SOURCE_ERRORS:
                pass

            effective_news_ready = news_ready and event_read_ready
            effective_hotspot_ready = hotspot_ready and event_read_ready
            evidence[entry.symbol] = CandidateSentimentEvidence(
                news_sync_ready=effective_news_ready,
                news_events=news_events,
                news_interpretations=interpretations,
                hotspot_sync_ready=effective_hotspot_ready,
                hotspot_events=hotspot_events,
                fund_flow=fund_flow,
            )
            source_payload[entry.symbol] = {
                "news_sync_ready": effective_news_ready,
                "news_event_ids": [item.event_id for item in news_events],
                "interpretation_ids": [
                    item.interpretation_id for item in interpretations
                ],
                "hotspot_sync_ready": effective_hotspot_ready,
                "hotspot_event_ids": [item.event_id for item in hotspot_events],
                "fund_flow_snapshot_id": (
                    fund_flow.snapshot_id if fund_flow is not None else None
                ),
            }

        batch = self.evaluator.evaluate(board, evidence, cutoff=cutoff)
        return self.sentiment_repository.append(
            batch,
            {
                "candidate_snapshot_id": board.snapshot_id,
                "candidate_input_hash": board.input_snapshot_hash,
                "cutoff": cutoff.isoformat(),
                "sources": source_payload,
            },
        )

    @staticmethod
    def _normalized_cutoff(cutoff: datetime) -> datetime:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise CandidateSentimentInputError("cutoff must include a timezone")
        return cutoff.astimezone(timezone.utc)

    @staticmethod
    def _is_fresh(batch: CandidateSentimentBatch, cutoff: datetime) -> bool:
        generated_at = batch.generated_at.astimezone(timezone.utc)
        return generated_at <= cutoff and cutoff - generated_at <= REFRESH_TTL
