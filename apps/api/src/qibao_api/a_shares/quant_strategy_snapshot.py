"""Durable, date-scoped snapshots for the quant strategy dashboard."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from qibao_api.contracts.quant_strategy import QuantStrategyDashboard


SNAPSHOT_SCHEMA_VERSION = 1


class QuantStrategySnapshotStore:
    def __init__(self, path: Path | None) -> None:
        self.path = path

    def load(
        self, *, trading_date: date, formula_version: str
    ) -> QuantStrategyDashboard | None:
        if self.path is None or not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
                return None
            if payload.get("formula_version") != formula_version:
                return None
            dashboard = QuantStrategyDashboard.model_validate(payload["dashboard"])
        except (OSError, TypeError, ValueError, ValidationError, KeyError):
            return None
        if dashboard.as_of != trading_date:
            return None
        if dashboard.formula_version != formula_version:
            return None
        if dashboard.status == "unavailable" or dashboard.candidate_scan_state != "ready":
            return None
        return dashboard

    def save(self, dashboard: QuantStrategyDashboard) -> None:
        if self.path is None:
            return
        if dashboard.status == "unavailable" or dashboard.candidate_scan_state != "ready":
            return
        payload = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "formula_version": dashboard.formula_version,
            "dashboard": dashboard.model_dump(mode="json"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(self.path)
