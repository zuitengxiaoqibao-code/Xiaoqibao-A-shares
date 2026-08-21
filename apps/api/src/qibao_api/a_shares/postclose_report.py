from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class FrozenMarketReport:
    report_id: str
    trading_date: date
    observed_at: datetime
    facts: dict[str, Any]
    quality: str
    coverage: Decimal
    ai_status: str = "not_requested"
    explanation: str | None = None


class PostCloseReportBuilder:
    def freeze(self, trading_date: date, observed_at: datetime, facts: dict[str, Any], *, coverage: int | Decimal = 100) -> FrozenMarketReport:
        local = observed_at.astimezone(ZoneInfo("Asia/Shanghai"))
        if local.date() == trading_date and local.time() < time(15, 0):
            raise ValueError("收盘前不能冻结盘后报告")
        encoded = json.dumps({"date": trading_date.isoformat(), "facts": facts}, ensure_ascii=False, sort_keys=True).encode()
        report_id = f"postclose-{trading_date.isoformat()}-{hashlib.sha256(encoded).hexdigest()[:16]}"
        quality = "ready" if Decimal(str(coverage)) >= 98 else "partial"
        return FrozenMarketReport(report_id, trading_date, observed_at, dict(facts), quality, Decimal(str(coverage)))

    def explain(self, report: FrozenMarketReport, *, ai_explanation: str | None) -> FrozenMarketReport:
        return FrozenMarketReport(report.report_id, report.trading_date, report.observed_at, report.facts, report.quality, report.coverage, "ready" if ai_explanation else "unavailable", ai_explanation)
