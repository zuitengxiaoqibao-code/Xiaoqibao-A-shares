from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from qibao_api.contracts.late_session_selection import (
    DEFAULT_LATE_SESSION_RULE_SETTINGS,
    LateSessionCandidateResult,
    LateSessionQuote,
    LateSessionRuleSettings,
    LateSessionRuleResult,
)


CHINA_TZ = ZoneInfo("Asia/Shanghai")
PRE_SCREEN_START = time(0, 0)
LIVE_START = time(14, 30)
LIVE_END = time(15, 0)


def classify_phase(
    now: datetime,
    *,
    start_time: time = LIVE_START,
    end_time: time = LIVE_END,
) -> str:
    """Classify by China local clock using the active editable time window."""
    local = now.astimezone(CHINA_TZ) if now.tzinfo else now.replace(tzinfo=CHINA_TZ)
    current = local.time().replace(tzinfo=None)
    if current < start_time:
        return "pre_screen"
    if current < end_time:
        return "live_monitor"
    return "post_close"


def _range_rule(
    *, key: str, label: str, actual: Decimal | None, lower: Decimal, upper: Decimal,
    target: str, enabled: bool,
) -> LateSessionRuleResult:
    if not enabled:
        return LateSessionRuleResult(key=key, label=label, actual=actual, target="已停用", status="disabled", detail="该规则已停用，不参与筛选")
    if actual is None:
        return LateSessionRuleResult(key=key, label=label, actual=None, target=target, status="unavailable", detail=f"{label}不可用，不能用代理字段替代")
    passed = lower <= actual <= upper
    return LateSessionRuleResult(key=key, label=label, actual=actual, target=target, status="passed" if passed else "failed", detail=f"实际 {actual}，目标 {target}")


def evaluate_candidate(
    quote: LateSessionQuote,
    *,
    settings: LateSessionRuleSettings = DEFAULT_LATE_SESSION_RULE_SETTINGS,
    allow_close_boundary: bool = False,
) -> LateSessionCandidateResult:
    local = quote.observed_at.astimezone(CHINA_TZ)
    current = local.time().replace(tzinfo=None)
    time_passed = settings.start_time <= current < settings.end_time or (
        allow_close_boundary and current == settings.end_time
    )
    rules = (
        LateSessionRuleResult(
            key="time_window", label="监控时间", actual=current.strftime("%H:%M:%S"), target=f"{settings.start_time.strftime('%H:%M')}–{settings.end_time.strftime('%H:%M')}",
            status="disabled" if not settings.time_enabled else ("passed" if time_passed else "failed"),
            detail="该规则已停用" if not settings.time_enabled else ("处于当前尾盘实时窗口" if current < settings.end_time else "使用收盘冻结的尾盘最后时点" if time_passed else "当前不在设定尾盘时间窗口"),
        ),
        _range_rule(key="change_percent", label="涨幅", actual=quote.change_percent, lower=settings.change_min, upper=settings.change_max, target=f"{settings.change_min}%–{settings.change_max}%", enabled=settings.change_enabled),
        _range_rule(key="volume_ratio", label="量比", actual=quote.volume_ratio, lower=settings.volume_ratio_min, upper=settings.volume_ratio_max, target=f"{settings.volume_ratio_min}–{settings.volume_ratio_max}", enabled=settings.volume_ratio_enabled),
        _range_rule(key="turnover_rate", label="换手率", actual=quote.turnover_rate, lower=settings.turnover_rate_min, upper=settings.turnover_rate_max, target=f"{settings.turnover_rate_min}%–{settings.turnover_rate_max}%", enabled=settings.turnover_rate_enabled),
        _range_rule(key="market_cap", label="总市值", actual=quote.market_cap_yi, lower=settings.market_cap_min, upper=settings.market_cap_max, target=f"{settings.market_cap_min}–{settings.market_cap_max}亿元", enabled=settings.market_cap_enabled),
        LateSessionRuleResult(
            key="twenty_day_limit_up", label="20日涨停", actual=quote.twenty_day_limit_up_count,
            target=f"近20日 {settings.twenty_day_limit_up_min}–{settings.twenty_day_limit_up_max if settings.twenty_day_limit_up_max is not None else '不限'} 次",
            status=("disabled" if not settings.twenty_day_limit_up_enabled else ("unavailable" if quote.twenty_day_limit_up_count is None else ("passed" if quote.twenty_day_limit_up_count >= settings.twenty_day_limit_up_min and (settings.twenty_day_limit_up_max is None or quote.twenty_day_limit_up_count <= settings.twenty_day_limit_up_max) else "failed"))),
            detail=("该规则已停用" if not settings.twenty_day_limit_up_enabled else ("20日涨停次数不可用，不能用当前涨幅代替" if quote.twenty_day_limit_up_count is None else f"近20个交易日涨停 {quote.twenty_day_limit_up_count} 次")),
        ),
        LateSessionRuleResult(
            key="above_intraday_average", label="分时黄线", actual=quote.price,
            target={"above": "最新价>真实分时均价", "below": "最新价<真实分时均价", "any": "不限制黄线方向"}[settings.intraday_relation],
            status=("disabled" if not settings.intraday_average_enabled else ("passed" if settings.intraday_relation == "any" else ("unavailable" if quote.intraday_average_price is None else ("passed" if ((settings.intraday_relation == "above" and quote.price > quote.intraday_average_price) or (settings.intraday_relation == "below" and quote.price < quote.intraday_average_price)) else "failed")))),
            detail=("该规则已停用" if not settings.intraday_average_enabled else ("分时黄线方向不限制" if settings.intraday_relation == "any" else ("分时黄线不可用，不能用收盘价或日线均价代理" if quote.intraday_average_price is None else f"最新价 {quote.price}，分时均价 {quote.intraday_average_price}"))),
        ),
    )
    passed = all(rule.status in {"passed", "disabled"} for rule in rules)
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
