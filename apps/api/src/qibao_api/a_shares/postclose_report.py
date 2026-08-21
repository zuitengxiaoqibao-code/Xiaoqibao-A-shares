from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo
from pathlib import Path


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


class PostCloseReportRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, report: FrozenMarketReport) -> None:
        target = self.root / f"{report.report_id}.json"
        if target.exists():
            raise ValueError("盘后报告不可覆盖")
        target.write_text(json.dumps({
            "report_id": report.report_id,
            "trading_date": report.trading_date.isoformat(),
            "observed_at": report.observed_at.isoformat(),
            "facts": report.facts,
            "quality": report.quality,
            "coverage": str(report.coverage),
            "ai_status": report.ai_status,
            "explanation": report.explanation,
        }, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def latest(self, trading_date: date) -> FrozenMarketReport | None:
        candidates = []
        for path in self.root.glob(f"postclose-{trading_date.isoformat()}-*.json"):
            if path.name.endswith(".delivery.json"):
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            candidates.append(FrozenMarketReport(
                value["report_id"], date.fromisoformat(value["trading_date"]),
                datetime.fromisoformat(value["observed_at"]), value["facts"],
                value["quality"], Decimal(value["coverage"]), value["ai_status"],
                value["explanation"],
            ))
        return max(candidates, key=lambda item: item.observed_at) if candidates else None

    def get(self, report_id: str) -> FrozenMarketReport | None:
        if not report_id.startswith("postclose-") or "/" in report_id or "\\" in report_id:
            return None
        target = self.root / f"{report_id}.json"
        if not target.exists():
            return None
        value = json.loads(target.read_text(encoding="utf-8"))
        return FrozenMarketReport(
            value["report_id"],
            date.fromisoformat(value["trading_date"]),
            datetime.fromisoformat(value["observed_at"]),
            value["facts"],
            value["quality"],
            Decimal(value["coverage"]),
            value["ai_status"],
            value["explanation"],
        )

    def list(self, limit: int = 30) -> list[FrozenMarketReport]:
        reports = []
        for path in self.root.glob("postclose-*.json"):
            if path.name.endswith(".delivery.json"):
                continue
            report = self.get(path.stem)
            if report is not None:
                reports.append(report)
        return sorted(reports, key=lambda item: item.observed_at, reverse=True)[: max(1, limit)]

    def record_delivery(self, report_id: str, channel: str, status: str, reason: str | None = None) -> None:
        target = self.root / f"{report_id}.delivery.json"
        state = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
        state[channel] = {"status": status, "reason": reason}
        target.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def delivery(self, report_id: str) -> dict[str, Any]:
        target = self.root / f"{report_id}.delivery.json"
        return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}


class PostCloseReportService:
    def __init__(self, repository: PostCloseReportRepository, fact_source, *, ai_provider=None, delivery=None) -> None:
        self.repository = repository
        self.fact_source = fact_source
        self.ai_provider = ai_provider
        self.delivery = delivery
        self.builder = PostCloseReportBuilder()

    def run(self, trading_date: date, observed_at: datetime) -> FrozenMarketReport:
        existing = self.repository.latest(trading_date)
        if existing is not None:
            return existing
        snapshot = self.fact_source(trading_date)
        if snapshot is None:
            facts = {"reason_code": "market_review_unavailable"}
            coverage = Decimal("0")
        else:
            facts = snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else dict(snapshot)
            watermark = getattr(snapshot, "watermark", None)
            coverage = getattr(watermark, "coverage_percent", None) or Decimal("0")
        frozen = self.builder.freeze(trading_date, observed_at, facts, coverage=coverage)
        explanation = None
        if self.ai_provider is not None:
            try:
                explanation = self.ai_provider(frozen)
            except Exception:
                explanation = None
        report = self.builder.explain(frozen, ai_explanation=explanation)
        self.repository.append(report)
        if self.delivery is not None:
            try:
                delivery_result = self.delivery(report)
            except Exception as error:
                self.repository.record_delivery(report.report_id, "feishu", "failed", str(error))
            else:
                status = getattr(delivery_result, "status", delivery_result)
                if not isinstance(status, str) or not status:
                    status = "sent"
                self.repository.record_delivery(report.report_id, "feishu", status)
        else:
            self.repository.record_delivery(report.report_id, "feishu", "未配置")
        return report

    def retry_delivery(self, report_id: str) -> str:
        report = self.repository.get(report_id)
        if report is None:
            raise KeyError(report_id)
        if self.delivery is None:
            self.repository.record_delivery(report_id, "feishu", "未配置")
            return "未配置"
        try:
            result = self.delivery(report)
        except Exception as error:
            self.repository.record_delivery(report_id, "feishu", "failed", str(error))
            raise
        status = getattr(result, "status", result)
        if not isinstance(status, str) or not status:
            status = "sent"
        self.repository.record_delivery(report_id, "feishu", status)
        return status
