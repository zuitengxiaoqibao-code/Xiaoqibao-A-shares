from datetime import date, datetime, timezone

from qibao_api.contracts.data_source import NormalizedBatch
from qibao_api.data_sources.merge_policy import MergePolicy


def _batch(source: str, value: float, observed_hour: int) -> NormalizedBatch:
    return NormalizedBatch(
        source_id=source,
        as_of=date(2026, 8, 20),
        observed_at=datetime(2026, 8, 20, observed_hour, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 20, observed_hour, 1, tzinfo=timezone.utc),
        records=({"symbol": "600519", "close": value},),
        content_hash=("a" if source == "tdx" else "b") * 64,
        quality_status="ready",
    )


def test_merge_policy_uses_priority_then_freshness_and_keeps_provenance() -> None:
    result = MergePolicy({"tdx": 10, "tencent": 5}).resolve(
        (_batch("tencent", 1501, 10), _batch("tdx", 1500, 9)),
        date(2026, 8, 20),
    )
    assert result.records[0]["close"] == 1500
    assert result.records[0]["source_id"] == "tdx"
    assert result.conflicts[0].sources == ("tdx", "tencent")


def test_merge_policy_does_not_invent_missing_values() -> None:
    result = MergePolicy({"tdx": 10}).resolve((_batch("tdx", None, 9),), date(2026, 8, 20))
    assert result.records[0]["close"] is None
    assert result.quality_status == "partial"
