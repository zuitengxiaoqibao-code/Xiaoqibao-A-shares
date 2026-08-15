from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.event_impact import (
    EventImpactReport,
    EventImpactTarget,
    EventImpactWindow,
)
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.contracts.market import AssetKind


HORIZONS = (1, 3, 5, 20)
CHINA_TZ = ZoneInfo("Asia/Shanghai")


class EventImpactNotFoundError(LookupError):
    pass


def _unavailable_windows(reason: str) -> tuple[EventImpactWindow, ...]:
    return tuple(
        EventImpactWindow(
            horizon_days=horizon,
            status="unavailable",
            reason=reason,
        )
        for horizon in HORIZONS
    )


def _stock_target(
    symbol: str,
    bars: list[DailyBar],
    first_published_at: datetime,
) -> EventImpactTarget:
    ordered = sorted(bars, key=lambda item: item.trade_date)
    published = first_published_at.astimezone(CHINA_TZ)
    after_close = published.timetz().replace(tzinfo=None) >= time(15)
    if after_close:
        baseline_candidates = [item for item in ordered if item.trade_date <= published.date()]
        post_event = [item for item in ordered if item.trade_date > published.date()]
    else:
        baseline_candidates = [item for item in ordered if item.trade_date < published.date()]
        post_event = [item for item in ordered if item.trade_date >= published.date()]
    if not baseline_candidates:
        reason = "event_baseline_daily_bar_unavailable"
        return EventImpactTarget(
            target_type="stock",
            target_id=symbol,
            status="unavailable",
            windows=_unavailable_windows(reason),
            limitations=(reason,),
        )
    baseline = baseline_candidates[-1]
    windows: list[EventImpactWindow] = []
    for horizon in HORIZONS:
        if len(post_event) < horizon:
            windows.append(EventImpactWindow(
                horizon_days=horizon,
                status="unavailable",
                reason=f"{horizon}_day_market_window_unavailable",
            ))
            continue
        end = post_event[horizon - 1]
        return_percent = (
            (end.close / baseline.close - Decimal("1")) * Decimal("100")
        ).quantize(Decimal("0.01"))
        windows.append(EventImpactWindow(
            horizon_days=horizon,
            status="ready",
            baseline_trade_date=baseline.trade_date,
            end_trade_date=end.trade_date,
            baseline_close=baseline.close,
            end_close=end.close,
            return_percent=return_percent,
        ))
    ready_count = sum(item.status == "ready" for item in windows)
    status = "ready" if ready_count == 4 else "partial" if ready_count else "unavailable"
    limitations = tuple(
        item.reason for item in windows if item.reason is not None
    )
    return EventImpactTarget(
        target_type="stock",
        target_id=symbol,
        status=status,
        windows=tuple(windows),
        limitations=limitations,
    )


class EventImpactService:
    def __init__(self, news_repository, bar_repository) -> None:
        self.news_repository = news_repository
        self.bar_repository = bar_repository

    def report(
        self,
        event_id: str,
        *,
        cutoff: datetime | None = None,
        as_of: date | None = None,
    ) -> EventImpactReport:
        if cutoff is None:
            selected_date = as_of or datetime.now(CHINA_TZ).date()
            cutoff = datetime.combine(
                selected_date,
                time.max,
                tzinfo=CHINA_TZ,
            ).astimezone(timezone.utc)
        events = tuple(self.news_repository.effective_events(cutoff=cutoff))
        event = next((item for item in events if item.event_id == event_id), None)
        if event is None:
            raise EventImpactNotFoundError(event_id)
        first_published_at = min(item.published_at for item in event.citations)
        symbols = tuple(dict.fromkeys(
            symbol
            for asset, symbol in event.affected_instruments
            if asset is AssetKind.A_SHARE
        ))
        sectors = tuple(dict.fromkeys((*event.industries, *event.themes)))
        histories = self.bar_repository.latest_many(
            list(symbols), 21, cutoff.astimezone(CHINA_TZ).date(), cutoff=cutoff
        ) if symbols else {}
        targets = [
            _stock_target(symbol, histories.get(symbol, []), first_published_at)
            for symbol in symbols
        ]
        sector_reason = "sector_daily_bar_series_unavailable"
        targets.extend(
            EventImpactTarget(
                target_type="sector",
                target_id=sector,
                status="unavailable",
                windows=_unavailable_windows(sector_reason),
                limitations=(sector_reason,),
            )
            for sector in sectors
        )

        duplicate_ids: set[str] = set()
        for citation in event.citations:
            cluster = self.news_repository.cluster_for_article(citation.article_id)
            if cluster is not None:
                duplicate_ids.update(cluster.article_ids)
        duplicate_count = max(1, len(duplicate_ids))
        duplicate_status = "duplicate_cluster" if duplicate_count > 1 else "unique"
        has_association = bool(symbols or sectors)
        if event.review_state == "rejected":
            association_status = "rejected"
        elif not has_association:
            association_status = "unavailable"
        elif event.review_state != "verified" or event.association_confidence < Decimal("0.70"):
            association_status = "low_confidence"
        else:
            association_status = "verified"

        ready_windows = sum(
            window.status == "ready" for target in targets for window in target.windows
        )
        total_windows = len(targets) * len(HORIZONS)
        limitations = list(dict.fromkeys(
            limitation for target in targets for limitation in target.limitations
        ))
        if association_status == "low_confidence":
            limitations.insert(0, "low_confidence_association")
        elif association_status != "verified":
            limitations.insert(0, f"association_{association_status}")
        if ready_windows == total_windows and association_status == "verified":
            status = "ready"
        elif ready_windows:
            status = "partial"
        else:
            status = "unavailable"
        coverage = (
            round(ready_windows * 100 / total_windows, 2) if total_windows else 0.0
        )
        ledger_status = "ready" if status == "ready" else "partial" if ready_windows else "unavailable"
        if ledger_status == "unavailable" and not limitations:
            limitations.append("event_impact_targets_unavailable")
        evidence_ledger = (
            EvidenceLedgerEntry(
                source="news-repository",
                operation="event-impact-source-event",
                status="ready" if association_status == "verified" else "partial",
                trade_date=first_published_at.astimezone(CHINA_TZ).date(),
                observed_at=event.normalized_at,
                sample_count=len(event.citations),
                total_count=len(event.citations),
                coverage_percent=100.0,
                limitations=(
                    () if association_status == "verified"
                    else (f"association_{association_status}",)
                ),
            ),
            EvidenceLedgerEntry(
                source="local-daily-bars",
                operation="event-impact-return-windows",
                status=ledger_status,
                trade_date=cutoff.astimezone(CHINA_TZ).date(),
                observed_at=cutoff,
                formula_version="event-impact-v1",
                sample_count=ready_windows,
                total_count=total_windows,
                coverage_percent=coverage,
                limitations=tuple(limitations),
            ),
        )
        return EventImpactReport(
            status=status,
            event_id=event.event_id,
            headline=event.headline,
            event_type=event.event_type,
            first_published_at=first_published_at,
            affected_symbols=symbols,
            related_sectors=sectors,
            association_confidence=event.association_confidence,
            association_status=association_status,
            duplicate_status=duplicate_status,
            duplicate_article_count=duplicate_count,
            targets=tuple(targets),
            evidence_ledger=evidence_ledger,
            limitations=tuple(limitations),
        )


def build_event_impact_report(
    event_id: str,
    *,
    news_repository,
    bar_repository,
    cutoff: datetime | None = None,
    as_of: date | None = None,
) -> EventImpactReport:
    return EventImpactService(news_repository, bar_repository).report(
        event_id, cutoff=cutoff, as_of=as_of
    )


NewsEventImpactService = EventImpactService
