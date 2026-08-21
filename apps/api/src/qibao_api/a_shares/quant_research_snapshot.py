from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from qibao_api.contracts.quant_research import QuantResearchSnapshot


SNAPSHOT_SCHEMA_VERSION = 1


class QuantResearchSnapshotStore:
    def __init__(self, path: Path | None) -> None:
        self.path = path

    def load(self, *, trading_date: date) -> QuantResearchSnapshot | None:
        snapshot = self.load_latest()
        if snapshot is None or snapshot.as_of != trading_date:
            return None
        return snapshot

    def load_latest(self) -> QuantResearchSnapshot | None:
        if self.path is None or not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
                return None
            snapshot = QuantResearchSnapshot.model_validate(payload["snapshot"])
        except (OSError, TypeError, ValueError, ValidationError, KeyError):
            return None
        if snapshot.status == "error":
            return None
        return snapshot

    def save(self, snapshot: QuantResearchSnapshot) -> None:
        if self.path is None or snapshot.status == "error":
            return
        payload = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "formula_version": snapshot.formula_version,
            "snapshot": snapshot.model_dump(mode="json"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(self.path)
