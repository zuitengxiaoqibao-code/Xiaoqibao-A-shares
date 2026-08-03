from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.first_limit_up import (
    FirstLimitUpCandidate,
)


LIMIT_TOLERANCE = Decimal("0.002")
WEEKLY_BOTTOM_THRESHOLD = Decimal("0.30")
MONTHLY_BOTTOM_THRESHOLD = Decimal("0.45")
MINIMUM_DAILY_HISTORY = 250
MINIMUM_CONSOLIDATION_DAYS = 5


def limit_rate_for_symbol(symbol: str) -> Decimal:
    if symbol.startswith(("300", "301", "688", "689")):
        return Decimal("0.20")
    return Decimal("0.10")


def is_limit_up(previous_close: Decimal, close: Decimal, limit_rate: Decimal) -> bool:
    target = (previous_close * (Decimal("1") + limit_rate)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return close >= target * (Decimal("1") - LIMIT_TOLERANCE)


def evaluate_first_limit_up(
    *,
    symbol: str,
    name: str,
    bars: list[DailyBar],
    pe_ttm: Decimal | None,
    as_of: date,
) -> FirstLimitUpCandidate | None:
    ordered = sorted((bar for bar in bars if bar.trade_date <= as_of), key=lambda item: item.trade_date)
    if len(ordered) < 2 or ordered[-1].trade_date != as_of:
        return None
    current = ordered[-1]
    previous = ordered[-2]
    limit_rate = limit_rate_for_symbol(symbol)
    if not is_limit_up(previous.close, current.close, limit_rate):
        return None

    reasons: list[str] = []
    risk_flags: list[str] = ["limit_up_day_no_buy"]
    if symbol.startswith(("4", "8", "92")):
        reasons.append("outside_shenzhen_shanghai_scope")
    if "ST" in name.upper() or "退" in name:
        reasons.append("st_or_delisting_name")

    for index in range(max(1, len(ordered) - 21), len(ordered) - 1):
        if is_limit_up(ordered[index - 1].close, ordered[index].close, limit_rate):
            reasons.append("recent_limit_up_within_20_bars")
            break

    if pe_ttm is None:
        reasons.append("pe_missing")
    elif pe_ttm <= 0:
        reasons.append("pe_not_positive")
    elif pe_ttm > Decimal("50"):
        reasons.append("pe_above_50")

    weekly_distance, weekly_bottom, weekly_reason = _bottom_position(
        ordered, "weekly", 26, WEEKLY_BOTTOM_THRESHOLD
    )
    monthly_distance, monthly_bottom, monthly_reason = _bottom_position(
        ordered, "monthly", 12, MONTHLY_BOTTOM_THRESHOLD
    )
    if weekly_reason:
        reasons.append(weekly_reason)
    elif not weekly_bottom:
        reasons.append("weekly_not_at_bottom")
    if monthly_reason:
        reasons.append(monthly_reason)
    elif not monthly_bottom:
        reasons.append("monthly_not_at_bottom")

    status = "qualified"
    if any(reason.endswith("history_insufficient") for reason in reasons):
        status = "data_insufficient"
        risk_flags.append("history_insufficient")
    elif reasons:
        status = "excluded"

    score = _score(pe_ttm, weekly_distance, monthly_distance, qualified=status == "qualified")
    if status == "data_insufficient":
        stage = "data_insufficient"
        action = "data_insufficient"
    elif status != "qualified":
        stage = "limit_up_day"
        action = "avoid"
    else:
        stage = "limit_up_day"
        action = "no_buy"

    return FirstLimitUpCandidate(
        symbol=symbol,
        name=name,
        as_of=as_of,
        limit_up_date=current.trade_date,
        limit_up_close=current.close,
        current_close=current.close,
        pe_ttm=pe_ttm,
        limit_rate=limit_rate,
        weekly_distance_to_low=weekly_distance,
        monthly_distance_to_low=monthly_distance,
        weekly_bottom=weekly_bottom,
        monthly_bottom=monthly_bottom,
        pullback_pct=Decimal("0"),
        consolidation_days=0,
        selection_status=status,
        stage=stage,
        action=action,
        score=score,
        reasons=tuple(dict.fromkeys(reasons)),
        risk_flags=tuple(dict.fromkeys(risk_flags)),
        sources=("local-daily-bars", "tencent-quote" if pe_ttm is not None else "pe-unavailable"),
    )


def refresh_candidate_state(
    candidate: FirstLimitUpCandidate,
    bars: list[DailyBar],
    *,
    as_of: date,
    current_close: Decimal | None = None,
) -> FirstLimitUpCandidate:
    ordered = sorted((bar for bar in bars if bar.trade_date <= as_of), key=lambda item: item.trade_date)
    if not ordered:
        return candidate.model_copy(update={
            "as_of": as_of,
            "stage": "data_insufficient",
            "action": "data_insufficient",
            "risk_flags": tuple(dict.fromkeys((*candidate.risk_flags, "history_insufficient"))),
        })
    close = current_close or ordered[-1].close
    if candidate.selection_status != "qualified":
        return candidate.model_copy(update={"as_of": as_of, "current_close": close})
    if as_of <= candidate.limit_up_date:
        return candidate.model_copy(update={
            "as_of": as_of,
            "current_close": close,
            "stage": "limit_up_day",
            "action": "no_buy",
            "pullback_pct": Decimal("0"),
            "consolidation_days": 0,
            "risk_flags": tuple(dict.fromkeys((*candidate.risk_flags, "limit_up_day_no_buy"))),
        })

    pullback = max(
        Decimal("0"),
        (candidate.limit_up_close - close) / candidate.limit_up_close,
    )
    consolidation_days = _consolidation_days(ordered, candidate.limit_up_date)
    risk_flags = [flag for flag in candidate.risk_flags if flag != "limit_up_day_no_buy"]
    if pullback > Decimal("0.20"):
        stage, action = "risk_expanded", "avoid"
        risk_flags.append("pullback_above_20_percent")
    elif pullback >= Decimal("0.05") and consolidation_days >= MINIMUM_CONSOLIDATION_DAYS:
        stage, action = "pullback_window", "staged_entry_reference"
    else:
        stage, action = "waiting_pullback", "observe"
    score = min(
        Decimal("100"),
        candidate.score + (Decimal("8") if stage == "pullback_window" else Decimal("0")),
    )
    return candidate.model_copy(update={
        "as_of": as_of,
        "current_close": close,
        "pullback_pct": pullback,
        "consolidation_days": consolidation_days,
        "stage": stage,
        "action": action,
        "score": score,
        "risk_flags": tuple(dict.fromkeys(risk_flags)),
    })


def _bottom_position(
    bars: list[DailyBar], period: str, minimum_periods: int, threshold: Decimal
) -> tuple[Decimal | None, bool | None, str | None]:
    grouped: dict[tuple[int, int], DailyBar] = {}
    for bar in bars:
        key = (
            bar.trade_date.isocalendar().year,
            bar.trade_date.isocalendar().week,
        ) if period == "weekly" else (bar.trade_date.year, bar.trade_date.month)
        grouped[key] = bar
    closes = [item.close for item in sorted(grouped.values(), key=lambda item: item.trade_date)]
    if len(closes) < minimum_periods:
        return None, None, f"{period}_history_insufficient"
    recent = closes[-minimum_periods:]
    distance = recent[-1] / min(recent) - Decimal("1")
    return distance, distance <= threshold, None


def _score(
    pe_ttm: Decimal | None,
    weekly_distance: Decimal | None,
    monthly_distance: Decimal | None,
    *,
    qualified: bool,
) -> Decimal:
    if not qualified:
        return Decimal("0")
    pe_points = (
        max(Decimal("0"), Decimal("30") * (Decimal("50") - pe_ttm) / Decimal("50"))
        if pe_ttm is not None else Decimal("0")
    )
    weekly_points = (
        max(Decimal("0"), Decimal("25") * (Decimal("1") - weekly_distance / WEEKLY_BOTTOM_THRESHOLD))
        if weekly_distance is not None else Decimal("0")
    )
    monthly_points = (
        max(Decimal("0"), Decimal("25") * (Decimal("1") - monthly_distance / MONTHLY_BOTTOM_THRESHOLD))
        if monthly_distance is not None else Decimal("0")
    )
    return min(Decimal("100"), (pe_points + weekly_points + monthly_points).quantize(Decimal("0.1")))


def _consolidation_days(bars: list[DailyBar], limit_up_date: date) -> int:
    post_limit = [bar for bar in bars if bar.trade_date > limit_up_date]
    if len(post_limit) < MINIMUM_CONSOLIDATION_DAYS:
        return 0
    for size in range(min(len(post_limit), 20), MINIMUM_CONSOLIDATION_DAYS - 1, -1):
        window = post_limit[-size:]
        low = min(item.close for item in window)
        high = max(item.close for item in window)
        if low > 0 and (high / low - Decimal("1")) <= Decimal("0.08"):
            return size
    return 0
