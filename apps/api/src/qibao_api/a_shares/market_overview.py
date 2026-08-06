import hashlib
import threading
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

from qibao_api.a_shares.market_regime import assess_market_regime
from qibao_api.a_shares.market_sentiment import FORMULA_VERSION
from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewAnomaly,
    OverviewBreadth,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewLiveFeedItem,
    OverviewMarketDataStatus,
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
    OverviewSector,
    OverviewSectorStock,
    OverviewSentiment,
)


HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")
CHINA_TZ = ZoneInfo("Asia/Shanghai")


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
        trading_calendar=None,
        cache_seconds: int = 5,
    ) -> None:
        self.sentiment_repository = sentiment_repository
        self.news_repository = news_repository
        self.first_limit_up_repository = first_limit_up_repository
        self.source = source
        self.clock = clock
        self.local_market_source = local_market_source
        self.market_review_source = market_review_source
        self.trading_calendar = trading_calendar
        self.cache_ttl = timedelta(seconds=cache_seconds)
        self._lock = threading.RLock()
        self._cached_at: datetime | None = None
        self._cached: MarketOverviewResponse | None = None

    def current(self, now: datetime) -> MarketOverviewResponse:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("overview cutoff must include timezone")
        with self._lock:
            if (
                self._cached is not None
                and self._cached_at is not None
                and now - self._cached_at < self.cache_ttl
            ):
                return self._cached
            response = self._build(now)
            self._cached = response
            self._cached_at = now
            return response

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
        anomalies = self._anomalies(events, minute_series)

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

        status = "ready" if indices and minute_series else "partial"
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
            indices=indices,
            minute_series=minute_series,
            anomalies=anomalies,
            live_feed=live_feed,
            sectors=sectors,
            sector_stocks=stocks_by_sector,
            market_stocks=market_stocks,
            review=review,
            warnings=tuple(dict.fromkeys(warnings)),
            sources=tuple(dict.fromkeys(sources)),
        )

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
            return "live"
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
    def _anomalies(cls, events, minute_series) -> tuple[OverviewAnomaly, ...]:
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
            values.append(OverviewAnomaly(
                anomaly_id=event.event_id,
                occurred_at=event.occurred_at,
                label=labels[0],
                headline=event.headline,
                direction=(
                    "neutral" if event.review_state == "verified" else "uncertain"
                ),
                themes=labels[:6],
                symbols=cls._event_symbols(event)[:8],
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
