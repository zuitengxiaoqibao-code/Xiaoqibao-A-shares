from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from qibao_api.contracts.data_source import NormalizedBatch


@dataclass(frozen=True, slots=True)
class MergeConflict:
    key: tuple[str, str]
    field: str
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedRecordSet:
    records: tuple[dict[str, Any], ...]
    conflicts: tuple[MergeConflict, ...]
    quality_status: str


class MergePolicy:
    """按来源优先级、观测时间和字段覆盖率裁决多源记录。"""

    def __init__(self, priorities: dict[str, int]) -> None:
        self.priorities = dict(priorities)

    def resolve(self, batches: tuple[NormalizedBatch, ...], as_of: date) -> ResolvedRecordSet:
        candidates: dict[tuple[str, str], list[tuple[NormalizedBatch, dict[str, Any]]]] = {}
        for batch in batches:
            if batch.as_of > as_of:
                continue
            for raw in batch.records:
                symbol = str(raw.get("symbol") or "").strip()
                row_date = str(raw.get("as_of") or batch.as_of.isoformat())
                if not symbol:
                    continue
                candidates.setdefault((symbol, row_date), []).append((batch, raw))

        output: list[dict[str, Any]] = []
        conflicts: list[MergeConflict] = []
        for key, rows in sorted(candidates.items()):
            ordered = sorted(
                rows,
                key=lambda item: (
                    self.priorities.get(item[0].source_id, 0),
                    item[0].observed_at,
                ),
                reverse=True,
            )
            winner_batch, winner = ordered[0]
            record = dict(winner)
            record["source_id"] = winner_batch.source_id
            record["observed_at"] = winner_batch.observed_at.isoformat()
            for field in sorted({field for _batch, row in rows for field in row}):
                values = [(batch, row.get(field)) for batch, row in rows if row.get(field) is not None]
                distinct = {repr(value) for _batch, value in values}
                if len(distinct) > 1:
                    conflicts.append(MergeConflict(
                        key=key,
                        field=field,
                        sources=tuple(item[0].source_id for item in ordered),
                    ))
                if record.get(field) is None and values:
                    record[field] = values[0][1]
            output.append(record)

        quality = "partial" if not output or conflicts else "ready"
        if output and any(value.get("close") is None for value in output):
            quality = "partial"
        return ResolvedRecordSet(tuple(output), tuple(conflicts), quality)
