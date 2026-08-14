import hashlib
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

from qibao_api.a_shares.market_regime import assess_market_regime
from qibao_api.a_shares.unified_events import UnifiedEventProjectionService
from qibao_api.a_shares.market_sentiment import FORMULA_VERSION
from qibao_api.contracts.field_evidence import FieldEvidence
from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewAnomaly,
    OverviewBreadth,
    OverviewDataScope,
    OverviewLimitEcology,
    OverviewLargeOrderFlow,
    OverviewLiquidity,
    OverviewLiveFeedItem,
    OverviewMarketDataStatus,
    OverviewOfficialEvent,
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
    OverviewSector,
    OverviewSectorFundFlowPoint,
    OverviewSectorStock,
    OverviewSentiment,
)


HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")
CHINA_TZ = ZoneInfo("Asia/Shanghai")
LIVE_MAX_AGE = timedelta(minutes=2)


class MarketOverviewService:
    def __init__(
        self,
        *,
        sentiment_repository,
        news_repository,
        first_limit_up_repository,
        source,
        clock: Callable[[], datetime],
        local_market_source=None,
        market_review_source=None,
        fund_flow_repository=None,
        sector_fund_flow_repository=None,
        official_calendar_source=None,
        trading_calendar=None,
        cache_seconds: int = 5,
        cache_path: Path | None = None,
        defer_initial_refresh: bool = False,
        initial_refresh_delay_seconds: float = 0,
        shared_snapshot_registry=None,
    ) -> None:
        if initial_refresh_delay_seconds < 0:
            raise ValueError("initial_refresh_delay_seconds must not be negative")
        self.sentiment_repository = sentiment_repository
        self.news_repository = news_repository
        self.first_limit_up_repository = first_limit_up_repository
        self.source = source
        self.clock = clock
        self.local_market_source = local_market_source
        self.market_review_source = market_review_source
        self.fund_flow_repository = fund_flow_repository
        self.sector_fund_flow_repository = sector_fund_flow_repository
        self.official_calendar_source = official_calendar_source
        self._official_calendar_cached_at: datetime | None = None
        self._official_calendar_events: tuple[OverviewOfficialEvent, ...] = ()
        self.trading_calendar = trading_calendar
        self.cache_ttl = timedelta(seconds=cache_seconds)
        self.cache_path = cache_path
        self.defer_initial_refresh = defer_initial_refresh and cache_path is not None
        self.initial_refresh_delay_seconds = initial_refresh_delay_seconds
        self.shared_snapshot_registry = shared_snapshot_registry
        self._lock = threading.RLock()
        self._cached_at: datetime | None = None
        self._cached: MarketOverviewResponse | None = None
        self._refresh_future: Future | None = None
        self._refresh_executor = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-overview")
            if self.defer_initial_refresh else None
        )
        self._initial_refresh_timer: threading.Timer | None = None
        self._initial_refresh_delay_consumed = not (
            self.defer_initial_refresh and initial_refresh_delay_seconds > 0
        )
        self._closed = False

    def current(self, now: datetime) -> MarketOverviewResponse:
        started_at = datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("overview cutoff must include timezone")
        with self._lock:
            if (
                self._cached is not None
                and self._cached_at is not None
                and now - self._cached_at < self.cache_ttl
            ):
                self._record_shared_snapshots(
                    self._cached, reused=True, started_at=started_at
                )
                return self._cached
            if self._cached is None and self.cache_path is not None:
                cached = self._read_cache(now)
                if cached is not None:
                    self._cached = cached
                    self._cached_at = now
                    if self.defer_initial_refresh:
                        self._schedule_refresh_locked(now)
                    self._record_shared_snapshots(
                        cached, reused=True, started_at=started_at
                    )
                    return cached
            if self._cached is not None and self.defer_initial_refresh:
                self._schedule_refresh_locked(now)
                self._record_shared_snapshots(
                    self._cached, reused=True, started_at=started_at
                )
                return self._cached
            response = self._build(now)
            self._cached = response
            self._cached_at = now
            self._write_cache(response)
            self._record_shared_snapshots(
                response, reused=False, started_at=started_at
            )
            return response

    def close(self) -> None:
        executor = self._refresh_executor
        if executor is None:
            return
        with self._lock:
            self._closed = True
            timer = self._initial_refresh_timer
            self._initial_refresh_timer = None
            if timer is not None:
                timer.cancel()
            if self._refresh_future is not None:
                self._refresh_future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        self._refresh_executor = None

    def _schedule_refresh_locked(self, now: datetime) -> None:
        if self._closed or self._refresh_executor is None:
            return
        if not self._initial_refresh_delay_consumed:
            if self._initial_refresh_timer is None:
                timer = threading.Timer(
                    self.initial_refresh_delay_seconds,
                    self._submit_initial_refresh,
                    args=(now,),
                )
                timer.daemon = True
                self._initial_refresh_timer = timer
                timer.start()
            return
        if self._refresh_future is not None and not self._refresh_future.done():
            return
        self._refresh_future = self._refresh_executor.submit(
            self._refresh_cached_snapshot, now
        )

    def _submit_initial_refresh(self, now: datetime) -> None:
        with self._lock:
            self._initial_refresh_timer = None
            self._initial_refresh_delay_consumed = True
            if self._closed or self._refresh_executor is None:
                return
            if self._refresh_future is not None and not self._refresh_future.done():
                return
            self._refresh_future = self._refresh_executor.submit(
                self._refresh_cached_snapshot, now
            )

    def _refresh_cached_snapshot(self, now: datetime) -> None:
        started_at = datetime.now(timezone.utc)
        try:
            response = self._build(now)
        except Exception:
            with self._lock:
                if self._cached is not None:
                    self._cached = self._with_metadata(
                        self._cached,
                        warning="market_overview_refresh_failed",
                    )
                    self._cached_at = now
            return
        with self._lock:
            if self._closed:
                return
            self._cached = response
            self._cached_at = now
            self._write_cache(response)
            self._record_shared_snapshots(
                response, reused=False, started_at=started_at
            )

    def _record_shared_snapshots(
        self,
        response: MarketOverviewResponse,
        *,
        reused: bool,
        started_at: datetime,
    ) -> None:
        registry = self.shared_snapshot_registry
        if registry is None:
            return
        payload = response.model_dump(mode="json")
        projections = {
            "market_cross_section": {
                key: payload[key]
                for key in (
                    "breadth", "liquidity", "regime_metrics", "regime",
                    "indices", "market_stocks", "data_scope",
                )
            },
            "limit_events": {
                key: payload[key]
                for key in ("limit_ecology", "anomalies")
            },
            "sector_strength": {
                key: payload[key]
                for key in ("sectors", "sector_stocks")
            },
            "stock_fund_flow": {
                key: payload[key]
                for key in ("large_order_flows", "sector_fund_flow")
            },
        }
        observed_at = response.market_data.observed_at or response.observed_at
        quote_count = response.market_data.quote_count
        universe_count = response.market_data.universe_count
        coverage = (
            round(quote_count / universe_count * 100, 2)
            if universe_count > 0 else None
        )
        latency_ms = max(
            0,
            round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
        )
        try:
            for kind, projection in projections.items():
                encoded = json.dumps(
                    projection,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                registry.record(
                    kind,
                    content_hash=hashlib.sha256(encoded).hexdigest(),
                    trade_date=response.as_of,
                    observed_at=observed_at,
                    coverage_percent=coverage,
                    freshness=response.market_data.freshness,
                    source=response.market_data.source,
                    reused=reused,
                    latency_ms=latency_ms,
                )
        except Exception:
            return

    def _read_cache(self, now: datetime) -> MarketOverviewResponse | None:
        if self.cache_path is None or not self.cache_path.exists():
            return None
        try:
            response = MarketOverviewResponse.model_validate_json(
                self.cache_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None
        if self.market_review_source is not None and hasattr(
            self.market_review_source, "cache_is_stale"
        ):
            try:
                if self.market_review_source.cache_is_stale():
                    response = response.model_copy(update={
                        "review": None,
                        "warnings": tuple(dict.fromkeys((
                            *response.warnings,
                            "market_review_cache_stale",
                        ))),
                    })
            except (OSError, RuntimeError, ValueError):
                pass
        return self._with_metadata(response, now=now, source="market-overview-cache")

    def _write_cache(self, response: MarketOverviewResponse) -> None:
        if self.cache_path is None:
            return
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(response.model_dump_json(), encoding="utf-8")
            temporary.replace(self.cache_path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _with_metadata(
        self,
        response: MarketOverviewResponse,
        *,
        now: datetime | None = None,
        source: str | None = None,
        warning: str | None = None,
    ) -> MarketOverviewResponse:
        updates: dict[str, object] = {}
        if now is not None:
            local_now = now.astimezone(CHINA_TZ)
            market_data = response.market_data.model_copy(update={
                "phase": self._market_phase(local_now),
                "freshness": self._market_freshness(
                    response.market_data.observed_at,
                    response.market_data.quality,
                    local_now,
                ),
            })
            updates["market_data"] = market_data
        if source is not None:
            updates["sources"] = tuple(dict.fromkeys((*response.sources, source)))
        if warning is not None:
            updates["warnings"] = tuple(dict.fromkeys((*response.warnings, warning)))
        return response.model_copy(update=updates) if updates else response

    def _build(self, now: datetime) -> MarketOverviewResponse:
        local_now = now.astimezone(CHINA_TZ)
        as_of = local_now.date()
        market_phase = self._market_phase(local_now)
        warnings: list[str] = []
        sources: list[str] = []

        snapshot = self.sentiment_repository.latest(
            trading_date=as_of, formula_version=FORMULA_VERSION
        )
        if snapshot is None:
            snapshot = self.sentiment_repository.previous_postclose(
                as_of, formula_version=FORMULA_VERSION
            )
        if snapshot is None:
            sentiment = OverviewSentiment(
                score=None, band="unavailable", coverage_percent=Decimal("0"),
                quality="unavailable", observed_at=now,
            )
            breadth = OverviewBreadth(
                rising_count=0, falling_count=0, flat_count=0, valid_count=0,
            )
            limit_ecology = OverviewLimitEcology(
                limit_up_count=0, limit_down_count=0, broken_limit_up_count=0,
            )
            liquidity = OverviewLiquidity()
            warnings.append("market_sentiment_unavailable")
        else:
            sources.append("market-sentiment-cache")
            sentiment = OverviewSentiment(
                score=snapshot.score,
                band=snapshot.band,
                coverage_percent=snapshot.coverage_percent,
                quality=snapshot.quality,
                observed_at=snapshot.observed_at,
            )
            breadth = self._breadth(snapshot)
            limit_ecology = self._limit_ecology(snapshot)
            liquidity = self._liquidity(snapshot)

        local_market = None
        if self.local_market_source is not None:
            try:
                local_market = self.local_market_source.current()
            except (OSError, RuntimeError, ValueError):
                warnings.append("tdx_local_market_unavailable")
        if local_market is not None:
            breadth = local_market.breadth
            limit_ecology = local_market.limit_ecology
            liquidity = OverviewLiquidity(
                total_amount_yi=local_market.liquidity.total_amount_yi,
                baseline_amount_yi=liquidity.baseline_amount_yi,
                relative_amount=liquidity.relative_amount,
            )
            regime_metrics = local_market.regime_metrics.model_copy(update={
                "amt_heat": liquidity.relative_amount,
                "factor_coverage_percent": (
                    Decimal("90.91")
                    if liquidity.relative_amount is not None
                    else local_market.regime_metrics.factor_coverage_percent
                ),
            })
            sources.append("tdx-local-realtime")
            market_data = OverviewMarketDataStatus(
                source=local_market.source,
                quality=local_market.quality,
                observed_at=local_market.observed_at,
                quote_count=local_market.quote_count,
                universe_count=local_market.universe_count,
                phase=market_phase,
                freshness=self._market_freshness(
                    local_market.observed_at, local_market.quality, local_now,
                ),
            )
            market_stocks = local_market.market_stocks
        else:
            regime_metrics = OverviewRegimeMetrics()
            market_data = OverviewMarketDataStatus(
                source="market-sentiment-cache" if snapshot is not None else "unavailable",
                quality=(sentiment.quality if snapshot is not None else "unavailable"),
                observed_at=(sentiment.observed_at if snapshot is not None else None),
                quote_count=breadth.valid_count,
                universe_count=breadth.valid_count,
                phase=market_phase,
                freshness=self._market_freshness(
                    sentiment.observed_at if snapshot is not None else None,
                    sentiment.quality if snapshot is not None else "unavailable",
                    local_now,
                ),
            )
            if self.local_market_source is not None:
                warnings.append("tdx_local_market_warming_up")
            market_stocks = ()

        try:
            indices, index_warnings = self.source.fetch_indices()
            warnings.extend(index_warnings)
            if indices:
                sources.append("tencent-index")
        except (httpx.HTTPError, OSError, ValueError):
            indices = ()
            warnings.append("index_quotes_unavailable")
        try:
            minute_series, minute_warnings = self.source.fetch_minutes()
            warnings.extend(minute_warnings)
            if minute_series:
                sources.append("tencent-index-minute")
        except (httpx.HTTPError, OSError, ValueError):
            minute_series = ()
            warnings.append("minute_series_unavailable")

        if local_market is not None:
            regime = assess_market_regime(
                regime_metrics,
                max_index_change_percent=max(
                    (item.change_percent for item in indices), default=None
                ),
            )
        else:
            regime = OverviewRegimeAssessment()

        try:
            events = sorted(
                self.news_repository.effective_events(cutoff=now),
                key=lambda item: item.occurred_at,
                reverse=True,
            )
            sources.append("local-news-cache")
        except (OSError, ValueError):
            events = []
            warnings.append("news_events_unavailable")
        events = [event for event in events if self._event_symbols(event)]
        live_feed = self._live_feed(events[:30])
        try:
            interpretations = self.news_repository.interpretations_for_events(
                tuple(item.event_id for item in events), cutoff=now,
            )
        except (AttributeError, OSError, ValueError):
            interpretations = ()
        event_projections = {
            item.event_id: item
            for item in UnifiedEventProjectionService().project(
                events, interpretations, cutoff=now
            )
        }
        anomalies = self._anomalies(events, minute_series, event_projections)

        try:
            scan = self.first_limit_up_repository.latest_scan(as_of=as_of)
            first_limit_candidates = tuple(scan.candidates) if scan is not None else ()
            if scan is not None:
                sources.append("first-limit-up-cache")
        except (OSError, ValueError):
            first_limit_candidates = ()
            warnings.append("first_limit_up_unavailable")

        if local_market is not None and local_market.sectors:
            sectors = local_market.sectors
            stocks_by_sector = local_market.sector_stocks
        else:
            sector_names, sector_symbols = self._sector_members(events)
            requested_symbols = tuple(dict.fromkeys(
                symbol for name in sector_names for symbol in sector_symbols[name]
            ))[:80]
            try:
                stock_quotes, stock_warnings = self.source.fetch_stocks(requested_symbols)
                warnings.extend(stock_warnings)
                if stock_quotes:
                    sources.append("tencent-stock-batch")
            except (httpx.HTTPError, OSError, ValueError):
                stock_quotes = ()
                warnings.append("sector_stock_quotes_unavailable")
            sectors, stocks_by_sector = self._sectors(
                sector_names,
                sector_symbols,
                stock_quotes,
                first_limit_candidates,
            )

        review = None
        if self.market_review_source is not None:
            try:
                review = self.market_review_source.current()
                if review is not None:
                    sources.append(review.source)
                    warnings.extend(review.warnings)
            except (OSError, RuntimeError, ValueError):
                warnings.append("market_review_unavailable")

        if (
            review is not None
            and review.latest_trade_date is not None
            and review.latest_trade_date < as_of
            and review.quality != "unavailable"
            and market_data.freshness in {"live", "final"}
        ):
            review = review.model_copy(update={
                "quality": "stale",
                "warnings": tuple(dict.fromkeys((*review.warnings, "market_review_stale"))),
            })
            warnings.append("market_review_stale")

        large_order_flows = self._large_order_flows(
            market_stocks, as_of=as_of, cutoff=now,
        )
        if large_order_flows:
            sources.append("eastmoney-fund-flow-cache")
        sector_fund_flow, sector_flow_sample_count, sector_flow_snapshot_count = (
            self._sector_fund_flow(cutoff=now)
        )
        if sector_fund_flow:
            sources.append("eastmoney-sector-fund-flow-cache")
        official_events = self._official_events(now)
        if official_events:
            sources.append("tdx-local-ipo-calendar")

        data_scope = OverviewDataScope(
            market_aggregate=(
                "full_a_share_market"
                if market_data.quote_count > 0 and breadth.valid_count > 0
                else "unavailable"
            ),
            market_quote_count=market_data.quote_count,
            market_universe_count=market_data.universe_count,
            stock_sample="representative" if market_stocks else "none",
            stock_sample_count=len(market_stocks),
            sector_sample=(
                "strong_sector" if local_market is not None and sectors
                else "news_linked" if sectors
                else "none"
            ),
            sector_sample_count=len(sectors),
            large_order_sample_count=len(large_order_flows),
            sector_fund_flow_sample_count=sector_flow_sample_count,
            sector_fund_flow_snapshot_count=sector_flow_snapshot_count,
        )

        status = "ready" if indices and minute_series else "partial"
        field_evidence = self._field_evidence(
            snapshot=snapshot,
            local_market=local_market,
            market_data=market_data,
            sentiment=sentiment,
            breadth=breadth,
            limit_ecology=limit_ecology,
            liquidity=liquidity,
            regime=regime,
            as_of=as_of,
        )
        return MarketOverviewResponse(
            status=status,
            as_of=as_of,
            observed_at=max(
                [sentiment.observed_at]
                + [item.observed_at for item in indices]
                + [item.observed_at for item in minute_series[-1:]]
                + ([local_market.observed_at] if local_market is not None else []),
            ),
            sentiment=sentiment,
            breadth=breadth,
            limit_ecology=limit_ecology,
            liquidity=liquidity,
            regime_metrics=regime_metrics,
            regime=regime,
            market_data=market_data,
            data_scope=data_scope,
            indices=indices,
            minute_series=minute_series,
            anomalies=anomalies,
            live_feed=live_feed,
            sectors=sectors,
            sector_stocks=stocks_by_sector,
            market_stocks=market_stocks,
            large_order_flows=large_order_flows,
            sector_fund_flow=sector_fund_flow,
            official_events=official_events,
            field_evidence=field_evidence,
            review=review,
            warnings=tuple(dict.fromkeys(warnings)),
            sources=tuple(dict.fromkeys(sources)),
        )

    @staticmethod
    def _field_evidence(
        *, snapshot, local_market, market_data, sentiment, breadth,
        limit_ecology, liquidity, regime, as_of,
    ) -> tuple[FieldEvidence, ...]:
        market_observed_at = market_data.observed_at
        market_source = market_data.source
        freshness_status = {
            "live": "live",
            "final": "postclose",
            "previous_close": "cached",
            "stale": "stale",
        }.get(market_data.freshness, "missing")
        market_coverage = (
            Decimal(market_data.quote_count) / Decimal(market_data.universe_count) * HUNDRED
            if market_data.universe_count > 0 else None
        )
        if market_coverage is not None:
            market_coverage = market_coverage.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        market_limitations = (
            () if freshness_status != "missing"
            else ("tdx_local_market_unavailable",)
        )

        def market_field(path: str, source_field: str, value) -> FieldEvidence:
            return FieldEvidence(
                field_path=path,
                value=value if freshness_status != "missing" else None,
                source=market_source if freshness_status != "missing" else "unavailable",
                source_field=source_field,
                status=freshness_status,
                trade_date=(market_observed_at.astimezone(CHINA_TZ).date() if market_observed_at else None),
                observed_at=market_observed_at,
                coverage_percent=market_coverage,
                limitations=market_limitations,
            )

        sentiment_ids = snapshot.source_snapshot_ids if snapshot is not None else ()
        sentiment_formula = snapshot.formula_version if snapshot is not None else FORMULA_VERSION
        sentiment_status = (
            "missing" if snapshot is None
            else "live" if snapshot.freshness == "current" and snapshot.trading_date == as_of
            else "cached"
        )
        sentiment_limitations = () if snapshot is not None else ("market_sentiment_unavailable",)
        entries: list[FieldEvidence] = [
            FieldEvidence(
                field_path="sentiment.score",
                value=sentiment.score,
                source="market-sentiment-cache" if snapshot is not None else "unavailable",
                source_field="score",
                status=sentiment_status,
                trade_date=snapshot.trading_date if snapshot is not None else None,
                observed_at=sentiment.observed_at if snapshot is not None else None,
                coverage_percent=sentiment.coverage_percent,
                derived=True,
                formula=sentiment_formula,
                evidence_ids=sentiment_ids,
                limitations=sentiment_limitations,
            ),
        ]
        for path, source_field, value in (
            ("breadth.rising_count", "rising_count", breadth.rising_count),
            ("breadth.falling_count", "falling_count", breadth.falling_count),
            ("breadth.valid_count", "valid_count", breadth.valid_count),
            ("limit_ecology.limit_up_count", "limit_up_count", limit_ecology.limit_up_count),
            ("limit_ecology.limit_down_count", "limit_down_count", limit_ecology.limit_down_count),
            ("limit_ecology.broken_limit_up_count", "broken_limit_up_count", limit_ecology.broken_limit_up_count),
            ("liquidity.total_amount_yi", "total_amount_yi", liquidity.total_amount_yi),
        ):
            entries.append(market_field(path, source_field, value))

        relative_source = snapshot.observed_at if snapshot is not None else None
        entries.append(FieldEvidence(
            field_path="liquidity.relative_amount",
            value=liquidity.relative_amount,
            source="market-sentiment-cache" if liquidity.relative_amount is not None else "unavailable",
            source_field="activity.relative_amount",
            status=("derived" if liquidity.relative_amount is not None else "missing"),
            trade_date=snapshot.trading_date if snapshot is not None else None,
            observed_at=relative_source,
            coverage_percent=sentiment.coverage_percent if liquidity.relative_amount is not None else None,
            derived=liquidity.relative_amount is not None,
            formula="当日全市场成交额 / 20日平均成交额" if liquidity.relative_amount is not None else None,
            evidence_ids=sentiment_ids,
            limitations=() if liquidity.relative_amount is not None else ("20_day_amount_baseline_unavailable",),
        ))
        for path, value in (
            ("regime.emotion_score", regime.emotion_score),
            ("regime.risk_score", regime.risk_score),
            ("regime.heat_score", regime.heat_score),
            ("regime.rotation_score", regime.rotation_score),
        ):
            entries.append(FieldEvidence(
                field_path=path,
                value=value,
                source=market_source if value is not None else "unavailable",
                source_field=None,
                status="derived" if value is not None else "missing",
                trade_date=(market_observed_at.astimezone(CHINA_TZ).date() if market_observed_at else None),
                observed_at=market_observed_at if value is not None else None,
                coverage_percent=regime.coverage_percent if value is not None else None,
                derived=value is not None,
                formula=regime.formula_version if value is not None else None,
                limitations=() if value is not None else ("tdx_local_market_unavailable",),
            ))
        return tuple(entries)

    def _large_order_flows(
        self,
        market_stocks,
        *,
        as_of,
        cutoff: datetime,
    ) -> tuple[OverviewLargeOrderFlow, ...]:
        if self.fund_flow_repository is None:
            return ()
        records: list[OverviewLargeOrderFlow] = []
        for stock in market_stocks:
            try:
                snapshot = self.fund_flow_repository.latest(
                    stock.symbol, as_of, cutoff=cutoff,
                )
            except (OSError, RuntimeError, ValueError):
                continue
            if snapshot is None:
                continue
            main_net_yi = (snapshot.latest_main_net / Decimal("100000000")).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP,
            )
            large_net_yi = (snapshot.latest_large_net / Decimal("100000000")).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP,
            )
            super_net_yi = (snapshot.latest_super_net / Decimal("100000000")).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP,
            )
            direction = (
                "inflow" if main_net_yi > 0
                else "outflow" if main_net_yi < 0
                else "balanced"
            )
            records.append(OverviewLargeOrderFlow(
                symbol=stock.symbol,
                name=stock.name,
                latest_trade_date=snapshot.latest_trade_date,
                observed_at=snapshot.observed_at,
                main_net_yi=main_net_yi,
                large_net_yi=large_net_yi,
                super_net_yi=super_net_yi,
                direction=direction,
                source=snapshot.source,
                quality=("ready" if snapshot.latest_trade_date == as_of else "stale"),
            ))
        return tuple(sorted(
            records,
            key=lambda item: abs(item.main_net_yi),
            reverse=True,
        ))

    def _sector_fund_flow(
        self,
        *,
        cutoff: datetime,
    ) -> tuple[tuple[OverviewSectorFundFlowPoint, ...], int, int]:
        if self.sector_fund_flow_repository is None:
            return (), 0, 0
        try:
            snapshots = self.sector_fund_flow_repository.history(limit=60)
        except (OSError, RuntimeError, ValueError):
            return (), 0, 0
        if not snapshots:
            return (), 0, 0

        latest = snapshots[-1]
        tracked = tuple(sorted(
            latest.items,
            key=lambda item: abs(item.main_net_yi),
            reverse=True,
        )[:12])
        tracked_codes = {item.sector_code for item in tracked}
        snapshot_quality = (
            "stale"
            if cutoff.astimezone(timezone.utc)
            - latest.observed_at.astimezone(timezone.utc) > LIVE_MAX_AGE
            else "ready"
        )
        points_by_code: dict[str, list[OverviewSectorFundFlowPoint]] = defaultdict(list)
        for snapshot in snapshots:
            for item in snapshot.items:
                if item.sector_code not in tracked_codes:
                    continue
                points_by_code[item.sector_code].append(OverviewSectorFundFlowPoint(
                    sector_code=item.sector_code,
                    sector_name=item.sector_name,
                    observed_at=snapshot.observed_at,
                    main_net_yi=item.main_net_yi,
                    large_net_yi=item.large_net_yi,
                    super_net_yi=item.super_net_yi,
                    source=snapshot.source,
                    quality=snapshot_quality,
                ))
        points = tuple(
            point
            for tracked_item in tracked
            for point in points_by_code.get(tracked_item.sector_code, ())
        )
        return points, len(points_by_code), len(snapshots)

    def _official_events(self, cutoff: datetime) -> tuple[OverviewOfficialEvent, ...]:
        if self.official_calendar_source is None:
            return ()
        if (
            self._official_calendar_cached_at is not None
            and cutoff - self._official_calendar_cached_at < timedelta(hours=1)
        ):
            return self._official_calendar_events
        try:
            source_events = self.official_calendar_source.fetch()
        except (OSError, RuntimeError, ValueError):
            return self._official_calendar_events
        converted: list[OverviewOfficialEvent] = []
        date_fields = (
            ("subscription", "subscription_date"),
            ("allotment", "allotment_date"),
            ("listing", "listing_date"),
        )
        for item in source_events:
            for event_type, field in date_fields:
                event_date = getattr(item, field, None)
                if event_date is None:
                    continue
                converted.append(OverviewOfficialEvent(
                    event_id=f"{item.code}-{event_type}-{event_date.isoformat()}",
                    event_date=event_date,
                    event_type=event_type,
                    code=item.code,
                    name=item.name,
                    kind=item.kind,
                    observed_at=item.fetched_at,
                    source=item.source,
                    quality="ready",
                ))
        self._official_calendar_cached_at = cutoff
        self._official_calendar_events = tuple(sorted(
            converted,
            key=lambda event: (event.event_date, event.code, event.event_type),
        ))
        return self._official_calendar_events

    def _market_phase(self, local_now: datetime) -> str:
        if self.trading_calendar is not None:
            try:
                if not self.trading_calendar.is_trading_day(local_now.date()):
                    return "closed"
            except (OSError, RuntimeError, ValueError):
                pass
        if local_now.time() < time(9, 25):
            return "premarket"
        if local_now.time() < time(15, 0):
            return "intraday"
        return "postclose"

    def _previous_trading_day(self, value):
        if self.trading_calendar is not None:
            try:
                return self.trading_calendar.previous_trading_day(value)
            except (OSError, RuntimeError, ValueError):
                pass
        return value - timedelta(days=1)

    def _market_freshness(self, observed_at, quality: str, local_now: datetime) -> str:
        if observed_at is None or quality == "unavailable":
            return "unavailable"
        observed_local = observed_at.astimezone(CHINA_TZ)
        observed_day = observed_local.date()
        phase = self._market_phase(local_now)
        if phase == "intraday" and observed_day == local_now.date():
            return (
                "live"
                if local_now - observed_local <= LIVE_MAX_AGE
                else "stale"
            )
        if phase == "postclose" and observed_day == local_now.date():
            return "final"
        if phase in {"premarket", "closed"} and observed_day == self._previous_trading_day(local_now.date()):
            return "previous_close"
        return "stale"

    @staticmethod
    def _metrics(snapshot, name: str) -> dict:
        component = next(
            (item for item in snapshot.components if item.name == name),
            None,
        )
        return component.metrics if component is not None else {}

    @classmethod
    def _breadth(cls, snapshot) -> OverviewBreadth:
        metrics = cls._metrics(snapshot, "breadth")
        rising = int(metrics.get("rising_count") or 0)
        falling = int(metrics.get("falling_count") or 0)
        flat = int(metrics.get("flat_count") or 0)
        valid = int(metrics.get("valid_count") or rising + falling + flat)
        if valid != rising + falling + flat:
            valid = rising + falling + flat
        return OverviewBreadth(
            rising_count=rising, falling_count=falling,
            flat_count=flat, valid_count=valid,
        )

    @classmethod
    def _limit_ecology(cls, snapshot) -> OverviewLimitEcology:
        metrics = cls._metrics(snapshot, "limit_ecology")
        limit_up = int(metrics.get("limit_up_count") or 0)
        limit_down = int(metrics.get("limit_down_count") or 0)
        broken = int(metrics.get("broken_limit_up_count") or 0)
        denominator = limit_up + broken
        seal_rate = (
            Decimal(limit_up) / Decimal(denominator) * HUNDRED
            if denominator else None
        )
        return OverviewLimitEcology(
            limit_up_count=limit_up,
            limit_down_count=limit_down,
            broken_limit_up_count=broken,
            seal_rate_percent=(
                seal_rate.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if seal_rate is not None else None
            ),
        )

    @classmethod
    def _liquidity(cls, snapshot) -> OverviewLiquidity:
        metrics = cls._metrics(snapshot, "activity")
        total = cls._decimal(metrics.get("total_amount_wan"))
        baseline = cls._decimal(metrics.get("baseline_amount_wan"))
        relative = cls._decimal(metrics.get("relative_amount"))
        return OverviewLiquidity(
            total_amount_yi=total / Decimal("10000") if total is not None else None,
            baseline_amount_yi=(
                baseline / Decimal("10000") if baseline is not None else None
            ),
            relative_amount=relative,
        )

    @staticmethod
    def _decimal(value) -> Decimal | None:
        return None if value is None or value == "" else Decimal(str(value))

    @staticmethod
    def _event_symbols(event) -> tuple[str, ...]:
        return tuple(
            symbol
            for asset, symbol in event.affected_instruments
            if str(getattr(asset, "value", asset)) == "a_share"
        )

    @classmethod
    def _live_feed(cls, events) -> tuple[OverviewLiveFeedItem, ...]:
        return tuple(OverviewLiveFeedItem(
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            headline=event.headline,
            summary=event.headline,
            themes=tuple(dict.fromkeys((*event.industries, *event.themes)))[:6],
            symbols=cls._event_symbols(event)[:8],
            source=(event.citations[0].publisher if event.citations else "本地新闻存档"),
            review_state=str(event.review_state),
        ) for event in events)

    @classmethod
    def _anomalies(
        cls, events, minute_series, event_projections=None,
    ) -> tuple[OverviewAnomaly, ...]:
        event_projections = event_projections or {}
        minute_timestamps = tuple(
            point.observed_at.timestamp() for point in minute_series
        )
        if not minute_timestamps:
            return ()
        values = []
        for event in events:
            # market_hotspot records are daily batches. Their timestamp is the
            # collection time, not the time when a theme moved in the market.
            if event.event_type != "market_news":
                continue
            event_timestamp = event.occurred_at.timestamp()
            if min(
                abs(point_timestamp - event_timestamp)
                for point_timestamp in minute_timestamps
            ) > 90:
                continue
            labels = tuple(dict.fromkeys((*event.industries, *event.themes)))
            if not labels:
                continue
            projection = event_projections.get(event.event_id)
            values.append(OverviewAnomaly(
                anomaly_id=event.event_id,
                occurred_at=event.occurred_at,
                label=labels[0],
                headline=event.headline,
                direction=(
                    projection.direction if projection is not None
                    else "neutral" if event.review_state == "verified" else "uncertain"
                ),
                themes=labels[:6],
                symbols=cls._event_symbols(event)[:8],
                category=(projection.category if projection is not None else None),
                strength=(projection.strength if projection is not None else "unknown"),
                credibility=(
                    projection.credibility if projection is not None
                    else "verified" if event.review_state == "verified" else "pending"
                ),
            ))
        return tuple(values[:15])

    @classmethod
    def _sector_members(cls, events):
        members: dict[str, list[str]] = defaultdict(list)
        for event in events[:100]:
            symbols = cls._event_symbols(event)
            for name in tuple(dict.fromkeys((*event.industries, *event.themes))):
                for symbol in symbols:
                    if symbol not in members[name]:
                        members[name].append(symbol)
        names = tuple(sorted(members, key=lambda name: (-len(members[name]), name)))[:12]
        return names, members

    @classmethod
    def _sectors(cls, names, members, quotes, candidates):
        quotes_by_symbol = {item.symbol: item for item in quotes}
        candidates_by_symbol = {item.symbol: item for item in candidates}
        sectors = []
        stocks_by_sector = {}
        for name in names:
            sector_id = f"sector-{hashlib.sha256(name.encode('utf-8')).hexdigest()[:12]}"
            rows = []
            for symbol in members[name]:
                quote = quotes_by_symbol.get(symbol)
                candidate = candidates_by_symbol.get(symbol)
                rows.append(OverviewSectorStock(
                    symbol=symbol,
                    name=(quote.name if quote else getattr(candidate, "name", symbol)),
                    change_percent=quote.change_percent if quote else None,
                    amount_yi=quote.amount_yi if quote else None,
                    market_cap_yi=quote.market_cap_yi if quote else None,
                    first_limit_time=None,
                    position="首板" if candidate is not None else "题材成员",
                    quality="ready" if quote else "unavailable",
                ))
            rows.sort(
                key=lambda item: item.change_percent if item.change_percent is not None else Decimal("-999"),
                reverse=True,
            )
            valid_changes = [item.change_percent for item in rows if item.change_percent is not None]
            amounts = [item.amount_yi for item in rows if item.amount_yi is not None]
            average = (
                sum(valid_changes, Decimal()) / Decimal(len(valid_changes))
                if valid_changes else None
            )
            sectors.append(OverviewSector(
                sector_id=sector_id,
                name=name,
                change_percent=(
                    average.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                    if average is not None else None
                ),
                amount_yi=sum(amounts, Decimal()) if amounts else None,
                limit_up_count=sum(
                    item.change_percent is not None
                    and item.change_percent >= (Decimal("19.5") if item.symbol.startswith(("300", "301", "688", "689")) else Decimal("9.5"))
                    for item in rows
                ),
                rising_count=sum(item.change_percent is not None and item.change_percent > 0 for item in rows),
                falling_count=sum(item.change_percent is not None and item.change_percent < 0 for item in rows),
                stock_count=len(rows),
            ))
            stocks_by_sector[sector_id] = tuple(rows[:20])
        sectors.sort(
            key=lambda item: (
                item.change_percent if item.change_percent is not None else Decimal("-999"),
                item.stock_count,
            ),
            reverse=True,
        )
        return tuple(sectors), stocks_by_sector
