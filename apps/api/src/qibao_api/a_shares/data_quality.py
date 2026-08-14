"""Deterministic quality gates for real daily-bar sequences."""

from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.data_quality import DataQualityIssue, DataQualityReport


JUMP_WARNING_PERCENT = Decimal("35")


def assess_bar_series(bars: Sequence[DailyBar]) -> DataQualityReport:
    issues: list[DataQualityIssue] = []
    seen_dates = set()
    previous = None
    for item in bars:
        if item.trade_date in seen_dates:
            issues.append(DataQualityIssue(
                code="duplicate_trade_date",
                severity="blocking",
                detail="同一股票序列存在重复交易日，已阻止进入计算。",
                trade_date=item.trade_date,
            ))
        seen_dates.add(item.trade_date)
        if previous is not None and item.trade_date < previous.trade_date:
            issues.append(DataQualityIssue(
                code="date_not_ascending",
                severity="blocking",
                detail="交易日顺序不是严格递增，已阻止进入计算。",
                trade_date=item.trade_date,
            ))
        if (item.volume == 0 and item.amount > 0) or (item.volume > 0 and item.amount == 0):
            issues.append(DataQualityIssue(
                code="volume_amount_conflict",
                severity="blocking",
                detail="成交量与成交额状态矛盾，已阻止进入计算。",
                trade_date=item.trade_date,
            ))
        if previous is not None:
            jump = abs(item.close / previous.close - Decimal("1")) * Decimal("100")
            if jump > JUMP_WARNING_PERCENT:
                issues.append(DataQualityIssue(
                    code="large_close_jump",
                    severity="warning",
                    detail="相邻收盘价跳变超过 35%，请核验复权、停牌或数据修订。",
                    trade_date=item.trade_date,
                    observed_value=jump.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                ))
        previous = item

    blocked = any(item.severity == "blocking" for item in issues)
    status = "error" if blocked else "partial" if issues else "ready"
    return DataQualityReport(
        status=status,
        blocked=blocked,
        sample_count=len(bars),
        issues=tuple(issues),
    )
