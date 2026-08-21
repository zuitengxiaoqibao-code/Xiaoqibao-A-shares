from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DataVersionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    domain: str = Field(min_length=1)
    as_of: date
    source_ids: tuple[str, ...]
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_status: str = Field(min_length=1)
    published_at: datetime


class DataVersionStore:
    """Append-only JSON version index used by point-in-time readers."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def publish(
        self,
        domain: str,
        as_of: date,
        source_ids: tuple[str, ...],
        content_hash: str,
        quality_status: str,
    ) -> DataVersionRecord:
        record = DataVersionRecord(
            domain=domain,
            as_of=as_of,
            source_ids=tuple(dict.fromkeys(source_ids)),
            content_hash=content_hash,
            quality_status=quality_status,
            published_at=datetime.now(timezone.utc),
        )
        target = self.root / "versions" / domain / f"{as_of.isoformat()}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{as_of.isoformat()}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(record.model_dump_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            Path(temp_name).unlink(missing_ok=True)
        return record

    def latest(self, domain: str, as_of: date) -> DataVersionRecord | None:
        directory = self.root / "versions" / domain
        if not directory.is_dir():
            return None
        candidates = sorted(
            (path for path in directory.glob("*.json") if path.stem <= as_of.isoformat()),
            key=lambda path: path.stem,
        )
        if not candidates:
            return None
        return DataVersionRecord.model_validate_json(candidates[-1].read_text(encoding="utf-8"))
