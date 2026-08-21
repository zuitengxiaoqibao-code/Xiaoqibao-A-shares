from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.contracts.data_source import DataSourceHealth, NormalizedBatch


def test_normalized_batch_requires_complete_provenance() -> None:
    with pytest.raises(ValidationError):
        NormalizedBatch(source_id="tdx", as_of=date(2026, 8, 21), records=[])


def test_normalized_batch_accepts_real_provenance() -> None:
    batch = NormalizedBatch(
        source_id="tdx",
        as_of=date(2026, 8, 21),
        observed_at=datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 21, 7, 1, tzinfo=timezone.utc),
        records=({"symbol": "600519.SH", "close": 1500.0},),
        content_hash="a" * 64,
        quality_status="ready",
    )
    assert batch.source_id == "tdx"
    assert batch.records[0]["symbol"] == "600519.SH"


def test_source_health_rejects_invalid_coverage() -> None:
    with pytest.raises(ValidationError):
        DataSourceHealth(
            source_id="tdx",
            status="ready",
            observed_at=datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc),
            coverage=101,
            latency_ms=10,
            reason=None,
        )
