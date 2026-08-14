from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from collections import Counter
from typing import Callable

from qibao_api.contracts.market_review import (
    MarketIntervalReviewSnapshot,
    MarketIntervalReviewStock,
    MarketDataWatermark,
    MarketReviewSnapshot,
    MarketReviewStock,
)
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.gongbu.tdx_local_daily import TdxLocalDailyBar


CENT = Decimal("0.01")
HUNDRED_MILLION = Decimal("100000000")
BENCHMARK_SYMBOLS = frozenset({"000300", "000852", "511010"})


def _two_places(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _limit_rate(symbol: str, name: str) -> Decimal:
    if symbol.startswith(("300", "301", "688", "689")):
        return Decimal("0.20")
    if symbol.startswith(("8", "4")):
        return Decimal("0.30")
    if "ST" in name.upper():
        return Decimal("0.05")
    return Decimal("0.10")


def _limit_price(previous_close: Decimal, symbol: str, name: str) -> Decimal:
    return (previous_close * (Decimal("1") + _limit_rate(symbol, name))).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def _is_limit_up(
    previous: TdxLocalDailyBar,
    current: TdxLocalDailyBar,
    *,
    name: str,
) -> bool:
    return current.close >= _limit_price(previous.close, current.symbol, name)


def _change(previous: TdxLocalDailyBar, current: TdxLocalDailyBar) -> Decimal:
    return _two_places((current.close / previous.close - Decimal("1")) * Decimal("100"))


def _volume_multiple(bars: tuple[TdxLocalDailyBar, ...]) -> Decimal | None:
    if len(bars) < 6:
        return None
    baseline = sum((Decimal(item.volume) for item in bars[-6:-1]), Decimal()) / Decimal("5")
    if baseline <= 0:
        return None
    return _two_places(Decimal(bars[-1].volume) / baseline)


def _base_stock(
    bars: tuple[TdxLocalDailyBar, ...],
    *,
    name: str,
    category: str,
    **updates,
) -> MarketReviewStock:
    current, previous = bars[-1], bars[-2]
    return MarketReviewStock(
        symbol=current.symbol,
        name=name,
        trade_date=current.trade_date,
        category=category,
        close=current.close,
        change_percent=_change(previous, current),
        amount_yi=_two_places(current.amount / HUNDRED_MILLION),
        **updates,
    )


def _review_trade_dates(
    histories: dict[str, tuple[TdxLocalDailyBar, ...]],
) -> tuple[date | None, date | None, int, Decimal | None]:
    latest_by_symbol = {
        symbol: bars[-1].trade_date
        for symbol, bars in histories.items()
        if symbol not in BENCHMARK_SYMBOLS and bars
    }
    if not latest_by_symbol:
        return None, None, 0, None
    counts = Counter(latest_by_symbol.values())
    dominant_date, dominant_count = max(
        counts.items(),
        key=lambda item: (item[1], item[0]),
    )
    latest_available = max(counts)
    coverage = _two_places(
        Decimal(dominant_count) / Decimal(len(latest_by_symbol)) * Decimal("100")
    )
    return dominant_date, latest_available, dominant_count, coverage


def build_market_review(
    histories: dict[str, tuple[TdxLocalDailyBar, ...]],
    *,
    as_of: date,
    observed_at: datetime,
    name_resolver: Callable[[str], str],
    history_source: str = "tdx-local-day",
) -> MarketReviewSnapshot:
    latest_trade_date, latest_available_trade_date, latest_trade_date_count, coverage = _review_trade_dates(histories)
    consecutive: list[MarketReviewStock] = []
    first: list[MarketReviewStock] = []
    new_high_100: list[MarketReviewStock] = []
    previous_limit_up: list[MarketReviewStock] = []
    volume_breakouts: list[MarketReviewStock] = []
    previous_high_breakouts: list[MarketReviewStock] = []
    low_position_volume: list[MarketReviewStock] = []
    ready_count = 0

    for symbol, raw_bars in histories.items():
        if symbol in BENCHMARK_SYMBOLS:
            continue
        bars = tuple(raw_bars)
        if len(bars) < 2 or bars[-1].trade_date != latest_trade_date:
            continue
        ready_count += 1
        name = name_resolver(symbol) or symbol
        latest_limit = _is_limit_up(bars[-2], bars[-1], name=name)
        if latest_limit:
            board_count = 1
            cursor = len(bars) - 2
            while cursor >= 1 and _is_limit_up(bars[cursor - 1], bars[cursor], name=name):
                board_count += 1
                cursor -= 1
            item = _base_stock(
                bars,
                name=name,
                category=("consecutive_limit_up" if board_count >= 2 else "first_limit_up"),
                board_count=board_count,
                limit_statistics=f"{board_count}/{board_count}",
            )
            if board_count >= 2:
                consecutive.append(item)
            else:
                first.append(item)

        if len(bars) >= 101:
            prior_close_high = max(item.close for item in bars[-101:-1])
            if bars[-1].close >= prior_close_high:
                new_high_100.append(_base_stock(
                    bars,
                    name=name,
                    category="new_high_100",
                    reference_high=prior_close_high,
                    window_days=100,
                ))

        if len(bars) >= 3 and _is_limit_up(bars[-3], bars[-2], name=name):
            previous_limit_up.append(_base_stock(
                bars,
                name=name,
                category="previous_limit_feedback",
                prior_close=bars[-2].close,
                prior_change_percent=_change(bars[-3], bars[-2]),
                window_days=1,
            ))

        multiple = _volume_multiple(bars)
        if len(bars) >= 61 and multiple is not None:
            prior_close_high = max(item.close for item in bars[-61:-1])
            if bars[-1].close >= prior_close_high and multiple >= Decimal("1.80"):
                volume_breakouts.append(_base_stock(
                    bars,
                    name=name,
                    category="volume_breakout",
                    volume_multiple=multiple,
                    reference_high=prior_close_high,
                    window_days=60,
                ))

        if len(bars) >= 21 and multiple is not None and multiple >= Decimal("1.20"):
            prior_high = max(item.high for item in bars[-21:-1])
            if bars[-1].close > prior_high:
                previous_high_breakouts.append(_base_stock(
                    bars,
                    name=name,
                    category="previous_high_breakout",
                    volume_multiple=multiple,
                    reference_high=prior_high,
                    window_days=20,
                ))

        if len(bars) >= 120 and multiple is not None and multiple >= Decimal("1.50"):
            window = bars[-120:]
            lowest = min(item.low for item in window)
            highest = max(item.high for item in window)
            span = highest - lowest
            position = Decimal("50") if span <= 0 else _two_places(
                (bars[-1].close - lowest) / span * Decimal("100")
            )
            if position <= Decimal("30"):
                low_position_volume.append(_base_stock(
                    bars,
                    name=name,
                    category="low_position_volume",
                    volume_multiple=multiple,
                    window_days=120,
                    range_position_percent=position,
                ))

    consecutive.sort(key=lambda item: (-(item.board_count or 0), -item.amount_yi, item.symbol))
    first.sort(key=lambda item: (-item.amount_yi, item.symbol))
    new_high_100.sort(key=lambda item: (-item.change_percent, -item.amount_yi, item.symbol))
    previous_limit_up.sort(key=lambda item: (-item.change_percent, -item.amount_yi, item.symbol))
    volume_breakouts.sort(key=lambda item: (-(item.volume_multiple or Decimal()), item.symbol))
    previous_high_breakouts.sort(key=lambda item: (-(item.volume_multiple or Decimal()), item.symbol))
    low_position_volume.sort(key=lambda item: (item.range_position_percent or Decimal("100"), -(item.volume_multiple or Decimal())))
    warning_list: list[str] = []
    if latest_trade_date is None:
        warning_list.append("tdx_daily_history_unavailable")
    elif latest_available_trade_date != latest_trade_date:
        warning_list.extend(("history_dates_fragmented", "history_latest_outlier"))
    warnings = tuple(warning_list)
    stock_universe_count = sum(
        1 for symbol in histories if symbol not in BENCHMARK_SYMBOLS
    )
    watermark_blockers: list[str] = []
    if latest_trade_date is None:
        watermark_blockers.append("tdx_daily_history_unavailable")
    if latest_trade_date_count < stock_universe_count:
        watermark_blockers.append("history_dates_fragmented")
    if ready_count < stock_universe_count:
        watermark_blockers.append("history_not_ready_for_all_symbols")
    if coverage is not None and coverage < Decimal("98"):
        watermark_blockers.append("history_coverage_below_98_percent")
    quality = (
        "ready"
        if ready_count and coverage is not None and coverage >= Decimal("98") and not watermark_blockers
        else "partial" if ready_count
        else "unavailable"
    )
    watermark = MarketDataWatermark(
        dominant_trade_date=latest_trade_date,
        latest_available_trade_date=latest_available_trade_date,
        universe_count=stock_universe_count,
        history_ready_count=ready_count,
        coverage_percent=coverage,
        fragmented_latest_count=max(0, stock_universe_count - latest_trade_date_count),
        missing_history_count=max(0, stock_universe_count - ready_count),
        quality=quality,
        blockers=tuple(dict.fromkeys(watermark_blockers)),
    )
    evidence_status = quality
    evidence_ledger = EvidenceLedgerEntry(
        source=history_source if latest_trade_date else "unavailable",
        operation="market_review",
        status=evidence_status,
        trade_date=latest_trade_date,
        observed_at=observed_at,
        formula_version="a-share-market-review-v2",
        sample_count=ready_count if ready_count > 0 else None,
        limitations=tuple(dict.fromkeys((*warnings, *watermark.blockers))),
    )
    return MarketReviewSnapshot(
        as_of=as_of,
        observed_at=observed_at,
        latest_trade_date=latest_trade_date,
        latest_available_trade_date=latest_available_trade_date,
        latest_available_trade_date_count=sum(
            1 for symbol, bars in histories.items()
            if bars
            and bars[-1].trade_date == latest_available_trade_date
            and symbol not in BENCHMARK_SYMBOLS
        ) if latest_available_trade_date is not None else 0,
        latest_trade_date_coverage_percent=coverage,
        source=history_source if latest_trade_date else "unavailable",
        quality=quality,
        universe_count=len(histories),
        history_ready_count=ready_count,
        consecutive_limit_up=tuple(consecutive),
        first_limit_up=tuple(first),
        new_high_100=tuple(new_high_100),
        previous_limit_up=tuple(previous_limit_up),
        volume_breakouts=tuple(volume_breakouts),
        previous_high_breakouts=tuple(previous_high_breakouts),
        low_position_volume=tuple(low_position_volume),
        watermark=watermark,
        evidence_ledger=(evidence_ledger,),
        warnings=warnings,
    )


def build_interval_review(
    histories: dict[str, tuple[TdxLocalDailyBar, ...]],
    *,
    start_date: date,
    end_date: date,
    as_of: date,
    observed_at: datetime,
    name_resolver: Callable[[str], str],
) -> MarketIntervalReviewSnapshot:
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")

    eligible = {
        symbol: tuple(sorted(bars, key=lambda item: item.trade_date))
        for symbol, bars in histories.items()
        if symbol not in BENCHMARK_SYMBOLS and bars
    }
    effective_end = min(end_date, as_of)
    available_dates = sorted({
        bar.trade_date
        for bars in eligible.values()
        for bar in bars
        if start_date <= bar.trade_date <= effective_end
    })
    if len(available_dates) < 2:
        return MarketIntervalReviewSnapshot(
            requested_start_date=start_date,
            requested_end_date=end_date,
            observed_at=observed_at,
            universe_count=len(eligible),
            warnings=("interval_history_unavailable",),
        )

    resolved_start = next((item for item in available_dates if item >= start_date), None)
    resolved_end = next((item for item in reversed(available_dates) if item <= effective_end), None)
    if resolved_start is None or resolved_end is None or resolved_start >= resolved_end:
        return MarketIntervalReviewSnapshot(
            requested_start_date=start_date,
            requested_end_date=end_date,
            observed_at=observed_at,
            universe_count=len(eligible),
            warnings=("interval_window_too_short",),
        )

    rows: list[MarketIntervalReviewStock] = []
    for symbol, bars in eligible.items():
        by_date = {bar.trade_date: bar for bar in bars}
        opening = by_date.get(resolved_start)
        closing = by_date.get(resolved_end)
        if opening is None or closing is None:
            continue
        window = tuple(
            bar for bar in bars
            if resolved_start <= bar.trade_date <= resolved_end
        )
        if not window:
            continue
        lowest = min(bar.low for bar in window)
        highest = max(bar.high for bar in window)
        amplitude = _two_places(
            (highest / lowest - Decimal("1")) * Decimal("100")
        ) if lowest > 0 else Decimal("0")
        rows.append(MarketIntervalReviewStock(
            symbol=symbol,
            name=name_resolver(symbol) or symbol,
            start_date=resolved_start,
            end_date=resolved_end,
            start_close=opening.close,
            end_close=closing.close,
            return_percent=_change(opening, closing),
            amplitude_percent=amplitude,
            amount_yi=_two_places(
                sum((bar.amount for bar in window), Decimal()) / HUNDRED_MILLION
            ),
        ))

    rows.sort(key=lambda item: (-item.return_percent, -item.amount_yi, item.symbol))
    quality = "ready" if len(rows) >= 1000 else "partial" if rows else "unavailable"
    warnings = () if rows else ("interval_samples_unavailable",)
    return MarketIntervalReviewSnapshot(
        requested_start_date=start_date,
        requested_end_date=end_date,
        start_date=resolved_start,
        end_date=resolved_end,
        observed_at=observed_at,
        source="tdx-local-day" if rows else "unavailable",
        quality=quality,
        universe_count=len(eligible),
        valid_count=len(rows),
        rows=tuple(rows),
        warnings=warnings,
    )
