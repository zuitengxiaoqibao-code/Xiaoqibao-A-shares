from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from qibao_api.contracts.late_session_selection import (
    LateSessionCandidateResult,
    LateSessionQuote,
    LateSessionRuleResult,
)


CHINA_TZ = ZoneInfo("Asia/Shanghai")
PRE_SCREEN_START = time(0, 0)
LIVE_START = time(14, 30)
LIVE_END = time(15, 0)


def classify_phase(now: datetime) -> str:
    """Classify by China local clock; pre-screen is the entire pre-14:30 session."""
    local = now.astimezone(CHINA_TZ) if now.tzinfo else now.replace(tzinfo=CHINA_TZ)
    current = local.time().replace(tzinfo=None)
    if current < LIVE_START:
        return "pre_screen"
    if current < LIVE_END:
        return "live_monitor"
    return "post_close"


def _range_rule(
    *, key: str, label: str, actual: Decimal | None, lower: Decimal, upper: Decimal, target: str,
) -> LateSessionRuleResult:
    if actual is None:
        return LateSessionRuleResult(key=key, label=label, actual=None, target=target, status="unavailable", detail=f"{label}不可用，不能用代理字段替代")
    passed = lower <= actual <= upper
    return LateSessionRuleResult(
        key=key, label=label, actual=actual, target=target,
        status="passed" if passed else "failed",
        detail=f"实际 {actual}，目标 {target}",
    )


def evaluate_candidate(quote: LateSessionQuote) -> LateSessionCandidateResult:
    local = quote.observed_at.astimezone(CHINA_TZ)
    current = local.time().replace(tzinfo=None)
    time_passed = LIVE_START <= current < LIVE_END
    rules = (
        LateSessionRuleResult(
            key="time_window", label="监控时间", actual=current.strftime("%H:%M:%S"), target="14:30–15:00",
            status="passed" if time_passed else "failed",
            detail="处于尾盘实时窗口" if time_passed else "当前不在14:30–15:00尾盘窗口",
        ),
        _range_rule(key="change_percent", label="涨幅", actual=quote.change_percent, lower=Decimal("3"), upper=Decimal("6"), target="3%–6%"),
        _range_rule(key="volume_ratio", label="量比", actual=quote.volume_ratio, lower=Decimal("2"), upper=Decimal("5"), target="2–5"),
        _range_rule(key="turnover_rate", label="换手率", actual=quote.turnover_rate, lower=Decimal("6"), upper=Decimal("15"), target="6%–15%"),
        _range_rule(key="market_cap", label="总市值", actual=quote.market_cap_yi, lower=Decimal("60"), upper=Decimal("300"), target="60–300亿元"),
        LateSessionRuleResult(
            key="twenty_day_limit_up", label="20日涨停", actual=quote.twenty_day_limit_up_count,
            target="近20个交易日≥1次",
            status=("unavailable" if quote.twenty_day_limit_up_count is None else ("passed" if quote.twenty_day_limit_up_count >= 1 else "failed")),
            detail=("20日涨停次数不可用，不能用当前涨幅代替" if quote.twenty_day_limit_up_count is None else f"近20个交易日涨停 {quote.twenty_day_limit_up_count} 次"),
        ),
        LateSessionRuleResult(
            key="above_intraday_average", label="分时黄线", actual=quote.price,
            target="最新价>真实分时均价",
            status=("unavailable" if quote.intraday_average_price is None else ("passed" if quote.price > quote.intraday_average_price else "failed")),
            detail=("分时黄线不可用，不能用收盘价或日线均价代理" if quote.intraday_average_price is None else f"最新价 {quote.price}，分时均价 {quote.intraday_average_price}"),
        ),
    )
    passed = all(rule.status == "passed" for rule in rules)
    missing = tuple(rule.label for rule in rules if rule.status == "unavailable")
    failed = tuple(rule.label for rule in rules if rule.status == "failed")
    return LateSessionCandidateResult(
        quote=quote,
        passed=passed,
        rules=rules,
        risk_notes=tuple(f"未通过：{label}" for label in failed) + tuple(f"待补齐：{label}" for label in missing),
    )


def classify_behavior(*, change_percent: Decimal, volume_ratio: Decimal | None, above_average: bool | None) -> tuple[str, ...]:
    """Return conservative tags; no tag is a trade instruction."""
    tags: list[str] = []
    if change_percent >= Decimal("3") and (volume_ratio is None or volume_ratio < Decimal("1.5")):
        tags.append("尾盘拉升量能不足：次日冲高回落风险")
    if change_percent <= Decimal("-3") and volume_ratio is not None and volume_ratio >= Decimal("2"):
        tags.append("尾盘急跌放量：风险释放未完成")
    if change_percent >= Decimal("2") and volume_ratio is not None and Decimal("1") <= volume_ratio <= Decimal("2") and above_average is True:
        tags.append("尾盘平稳走高量价配合：次日溢价观察")
    if above_average is False and abs(change_percent) < Decimal("1"):
        tags.append("尾盘横盘弱于大盘：补跌风险")
    return tuple(tags)
