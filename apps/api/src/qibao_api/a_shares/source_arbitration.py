from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from qibao_api.a_shares.point_in_time import as_of


SOURCE_PRIORITY: dict[str, int] = {
    "local-tdx": 0,
    "tdx": 0,
    "mootdx": 0,
    "tencent": 1,
    "eastmoney": 2,
    "baidu": 3,
}


def _value_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def select_preferred(
    records: Iterable[Mapping[str, Any]],
    *,
    cutoff: datetime,
    source_priority: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Select one point-in-time source while preserving conflict evidence."""
    priority = source_priority or SOURCE_PRIORITY
    eligible: list[dict[str, Any]] = []
    limitations: list[str] = []
    for index, raw in enumerate(records):
        candidate = dict(raw)
        source = str(candidate.get("source") or "").strip()
        if not source:
            limitations.append("candidate_source_missing")
            continue
        observed_at = candidate.get("observed_at")
        if not isinstance(observed_at, datetime):
            limitations.append("candidate_observed_at_missing")
            continue
        try:
            accepted = as_of(candidate, cutoff)
        except ValueError:
            limitations.append("candidate_observed_at_timezone_invalid")
            continue
        if accepted is None:
            continue
        coverage = candidate.get("coverage_percent")
        try:
            normalized_coverage = float(coverage) if coverage is not None else 0.0
        except (TypeError, ValueError):
            normalized_coverage = 0.0
            limitations.append("candidate_coverage_invalid")
        candidate["coverage_percent"] = normalized_coverage
        candidate["_source_priority"] = priority.get(source, 99)
        candidate["_sequence"] = index
        eligible.append(candidate)

    if not eligible:
        limitations.append("no_candidate_observed_before_cutoff")
        return {
            "status": "unavailable",
            "selected": None,
            "candidates": [],
            "limitations": list(dict.fromkeys(limitations)),
        }

    ordered = sorted(
        eligible,
        key=lambda item: (
            item["_source_priority"],
            -item["observed_at"].timestamp(),
            -item["coverage_percent"],
            item["source"],
            item["_sequence"],
        ),
    )
    selected = dict(ordered[0])
    for item in (selected, *ordered):
        item.pop("_source_priority", None)
        item.pop("_sequence", None)
    values = {_value_key(item.get("value")) for item in ordered}
    status = "conflict" if len(values) > 1 else "ready"
    if status == "conflict":
        limitations.append("source_values_disagree")
    return {
        "status": status,
        "selected": selected,
        "candidates": [dict(item) for item in ordered],
        "limitations": list(dict.fromkeys(limitations)),
    }
