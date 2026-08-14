from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


LEVEL_RANK = {"low": 0, "medium": 1, "high": 2, "unavailable": -1}
BAND_LABEL = {
    "panic": "恐慌",
    "cold": "偏冷",
    "neutral": "中性",
    "active": "活跃",
    "overheated": "过热",
    "unavailable": "数据待补齐",
}


def build_risk_status(*, sentiment_repository=None, news_repository=None, now=None) -> dict:
    generated_at = now or datetime.now(timezone.utc)
    sentiment = _latest_sentiment(sentiment_repository)
    alerts = _news_alerts(news_repository, generated_at)
    dimensions = [
        _market_dimension(sentiment),
        _stock_dimension(),
        _news_dimension(alerts),
        _freshness_dimension(sentiment, generated_at),
        _coverage_dimension(sentiment),
        _strategy_dimension(),
    ]
    available_levels = [item["level"] for item in dimensions if item["level"] != "unavailable"]
    overall = max(available_levels, key=LEVEL_RANK.get) if available_levels else "unavailable"
    return {
        "rule_version": "research-risk-v2",
        "limits": {
            "max_quote_age_seconds": 180,
            "industry_concentration": "data_required",
            "liquidity": "data_required",
        },
        "overall_level": overall,
        "generated_at": generated_at.isoformat(),
        "dimensions": dimensions,
        "alerts": alerts,
    }


def _latest_sentiment(repository):
    if repository is None:
        return None
    try:
        return repository.latest()
    except Exception:
        return None


def _market_dimension(snapshot) -> dict:
    if snapshot is None or snapshot.score is None:
        return _dimension("market_sentiment", "市场环境", "unavailable", "数据待补齐", "没有可核验的市场情绪快照", "先同步全市场行情，再判断市场风险")
    level = "high" if snapshot.band in {"panic", "overheated"} else "medium" if snapshot.band in {"cold", "active"} else "low"
    action = {
        "panic": "停止追高，等待恐慌修复证据",
        "cold": "降低试错频率，只观察高质量触发",
        "neutral": "按策略触发执行，不预判方向",
        "active": "关注拥挤度和炸板风险",
        "overheated": "防止一致加速后的高位回撤",
    }.get(snapshot.band, "等待可核验数据")
    return _dimension("market_sentiment", "市场环境", level, f"{BAND_LABEL.get(snapshot.band, snapshot.band)} · {snapshot.score} 分", f"情绪公式覆盖 {snapshot.coverage_percent}% · {snapshot.quality}", action)


def _freshness_dimension(snapshot, now: datetime) -> dict:
    if snapshot is None:
        return _dimension("data_freshness", "数据时效", "unavailable", "未发现快照", "无法确认行情观测时间", "同步行情后再使用盘中判断")
    age = max(Decimal("0"), Decimal(str((now - snapshot.observed_at).total_seconds())))
    stale = snapshot.freshness == "stale" or age > Decimal("180")
    return _dimension("data_freshness", "数据时效", "high" if stale else "low", "已过期" if stale else "当前有效", f"最近观测 {snapshot.observed_at.isoformat()} · 相隔 {int(age)} 秒", "刷新市场快照" if stale else "继续按计划复核")


def _coverage_dimension(snapshot) -> dict:
    if snapshot is None:
        return _dimension("evidence_coverage", "证据覆盖", "unavailable", "无法测算", "没有市场情绪证据覆盖记录", "补齐全市场横截面和基准数据")
    coverage = snapshot.coverage_percent
    level = "high" if coverage < 50 else "medium" if coverage < 80 else "low"
    return _dimension("evidence_coverage", "证据覆盖", level, f"{coverage}%", f"快照质量 {snapshot.quality} · {len(snapshot.source_snapshot_ids)} 个来源快照", "覆盖不足时不放大结论" if level != "low" else "覆盖可用于辅助判断")


def _news_dimension(alerts: list[dict]) -> dict:
    high_count = sum(item["level"] == "high" for item in alerts)
    level = "high" if high_count else "medium" if alerts else "low"
    value = f"{len(alerts)} 条负面事件" if alerts else "暂无已证实负面事件"
    evidence = f"其中 {high_count} 条高风险" if alerts else "只统计已复核且方向置信度达到 60% 的事件"
    action = "逐条核对受影响股票和板块" if alerts else "继续监控已核验新闻"
    return _dimension("news_events", "新闻事件", level, value, evidence, action)


def _stock_dimension() -> dict:
    return _dimension(
        "stock_specific",
        "个股风险",
        "unavailable",
        "等待选择股票",
        "全局风险页没有绑定单只股票，不能用市场均值代替个股风险",
        "进入个股观察或公司研究后核验财务、价格和事件风险",
    )


def _strategy_dimension() -> dict:
    return _dimension(
        "strategy_execution",
        "策略风险",
        "unavailable",
        "等待策略与触发记录",
        "当前没有可归属到具体策略版本的执行样本",
        "先冻结策略参数，再根据样本外回测和实际触发结果评估",
    )


def _news_alerts(repository, now: datetime) -> list[dict]:
    if repository is None:
        return []
    try:
        events = {item.event_id: item for item in repository.effective_events()}
        interpretations = repository.interpretations()
    except Exception:
        return []
    cutoff = now - timedelta(days=7)
    alerts = []
    for interpretation in reversed(interpretations):
        if interpretation.impact_direction != "negative" or interpretation.confidence < Decimal("0.60"):
            continue
        event = events.get(interpretation.event_id)
        if event is None or event.review_state != "verified" or event.occurred_at < cutoff:
            continue
        citation = event.citations[0] if event.citations else None
        alerts.append({
            "id": event.event_id,
            "title": event.headline,
            "level": "high" if interpretation.confidence >= Decimal("0.80") else "medium",
            "category": "新闻事件",
            "evidence": citation.quoted_text[:180] if citation else "事件已复核，但引用摘要待补齐",
            "action": "核对原始来源、失效条件和关联范围，未确认前暂不参与",
            "affected_instruments": [code for asset, code in event.affected_instruments if str(asset) in {"a_share", "AssetKind.A_SHARE"}],
            "affected_sectors": list(dict.fromkeys((*event.industries, *event.themes))),
            "observed_at": event.occurred_at.isoformat(),
            "source": citation.publisher if citation else "已归档来源",
        })
        if len(alerts) >= 20:
            break
    return alerts


def _dimension(identifier: str, label: str, level: str, value: str, evidence: str, action: str) -> dict:
    return {"id": identifier, "label": label, "level": level, "value": value, "evidence": evidence, "action": action}
