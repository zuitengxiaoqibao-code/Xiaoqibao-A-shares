from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Literal


Completeness = Literal["complete", "partial"]


class SnapshotStore:
    def __init__(self, path: Path, *, schema_version: int, data_version: str = "1") -> None:
        self.path = path
        self.schema_version = schema_version
        self.data_version = data_version
        self._replace = os.replace

    def read(self, *, scope: str, symbol: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if (
            payload.get("schema_version") != self.schema_version
            or payload.get("scope") != scope
            or payload.get("symbol") != symbol
            or payload.get("completeness") != "complete"
            or "value" not in payload
        ):
            return None
        return payload

    def write(
        self,
        *,
        scope: str,
        symbol: str,
        value: Any,
        completeness: Completeness = "complete",
        source_cutoff: str | None = None,
    ) -> bool:
        if completeness == "partial" and self.read(scope=scope, symbol=symbol) is not None:
            return False
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": self.schema_version,
            "data_version": self.data_version,
            "scope": scope,
            "symbol": symbol,
            "generated_at": now,
            "source_cutoff": source_cutoff,
            "completeness": completeness,
            "value": value,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            self._replace(temporary, self.path)
            return True
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return False

