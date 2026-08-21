from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime
from typing import Mapping

from qibao_api.contracts.page_snapshots import PageSnapshot


PAGE_SNAPSHOT_POLICIES: Mapping[str, tuple[tuple[str, ...], str]] = {
    "market_overview": (("market_cross_section", "limit_events", "sector_strength", "stock_fund_flow", "news_events"), "交易时段实时推送；断线统一保底"),
    "today_decision": (("market_cross_section", "sector_strength", "news_events"), "市场版本变化时更新"),
    "stock_observation": (("market_cross_section", "news_events"), "标的主题增量"),
    "company_research": (("financial_valuation", "news_events"), "缓存优先；交易日后台补证"),
    "first_limit_up": (("limit_events", "sector_strength"), "共享生态版本更新"),
    "late_session_selection": (("market_cross_section", "sector_strength"), "尾盘窗口增量"),
    "quant_analysis": (("market_cross_section", "quant_factors", "news_events"), "策略事件更新；扫描后台执行"),
    "monitor_center": (("news_events",), "告警事件推送"),
    "news": (("news_events",), "新闻增量推送"),
    "risk": (("market_cross_section", "news_events"), "风险输入变化时重算"),
    "history": (("market_cross_section", "news_events", "quant_factors"), "收盘事实冻结"),
    "settings": ((), "本地配置读取"),
    "operations": ((), "页面可见时读取"),
    "bonds": ((), "独立转债主题"),
}


class PageSnapshotService:
    def __init__(self, registry) -> None:
        self.registry = registry

    def snapshot(self, menu: str, *, started_at: float | None = None) -> PageSnapshot:
        started = time.perf_counter() if started_at is None else started_at
        if menu not in PAGE_SNAPSHOT_POLICIES:
            raise ValueError("unknown page snapshot menu")
        kinds, policy = PAGE_SNAPSHOT_POLICIES[menu]
        summaries = {item["kind"]: item for item in self.registry.summary()}
        selected = [summaries[kind] for kind in kinds if kind in summaries]
        available = [item for item in selected if int(item.get("snapshot_version") or 0) > 0]
        missing = [kind for kind in kinds if int(summaries.get(kind, {}).get("snapshot_version") or 0) == 0]
        observed_values = [item.get("observed_at") for item in available if item.get("observed_at")]
        trade_values = [item.get("trade_date") for item in available if item.get("trade_date")]
        coverage_values = [float(item["coverage_percent"]) for item in available if item.get("coverage_percent") is not None]
        hashes = sorted(str(item["content_hash"]) for item in available if item.get("content_hash"))
        content_hash = hashlib.sha256(json.dumps(hashes, separators=(",", ":")).encode()).hexdigest() if hashes else None
        state = "unavailable" if not available and kinds else "ready" if not missing else "partial"
        return PageSnapshot(
            menu=menu,
            state=state,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            cache_frame_ms=max(0, round((time.perf_counter() - started) * 1000)) if available else None,
            usable_content=bool(available) or not kinds,
            reason=(f"共享快照尚未生成：{', '.join(missing)}" if missing else None),
            observed_at=max((datetime.fromisoformat(value) for value in observed_values), default=None),
            trade_date=max((date.fromisoformat(value) for value in trade_values), default=None),
            source="shared-snapshot-registry" if available else "unavailable",
            coverage=round(sum(coverage_values) / len(coverage_values), 2) if coverage_values else None,
            content_hash=content_hash,
            snapshot_versions={kind: int(summaries.get(kind, {}).get("snapshot_version") or 0) for kind in kinds},
            refresh_policy=policy,
        )
