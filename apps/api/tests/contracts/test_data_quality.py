from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from qibao_api.contracts.data_quality_matrix import DataQualityItem


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


def test_data_quality_requires_consistent_real_coverage() -> None:
    item = DataQualityItem(
        domain="market_quotes",
        status="ready",
        source="tdx-local",
        observed_at=NOW,
        valid_count=5195,
        total_count=5198,
        coverage_percent=99.94,
        cache_state="live",
    )
    assert item.coverage_percent == 99.94


@pytest.mark.parametrize(
    "changes",
    [
        {"valid_count": 11, "total_count": 10, "coverage_percent": 100},
        {"valid_count": 9, "total_count": 10, "coverage_percent": 99},
        {"observed_at": None},
    ],
)
def test_data_quality_rejects_invalid_ready_claims(changes: dict) -> None:
    payload = {
        "domain": "market_quotes",
        "status": "ready",
        "source": "tdx-local",
        "observed_at": NOW,
        "valid_count": 10,
        "total_count": 10,
        "coverage_percent": 100,
        "cache_state": "live",
    }
    payload.update(changes)
    with pytest.raises(ValidationError):
        DataQualityItem(**payload)


def test_data_quality_requires_limitation_when_unavailable() -> None:
    with pytest.raises(ValidationError, match="limitations"):
        DataQualityItem(
            domain="professional_fields",
            status="unavailable",
            source="tdx-professional",
            cache_state="not_applicable",
        )
