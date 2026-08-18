from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qibao_api.operations.field_arbitration import FieldArbitrator, FieldEvidence


NOW = datetime(2026, 8, 18, 6, 31, tzinfo=UTC)


def test_arbitrator_uses_fresh_priority_source_and_falls_back_from_stale() -> None:
    arbitrator = FieldArbitrator()
    fresh = FieldEvidence(value=Decimal("10.01"), source="tencent", observed_at=NOW, priority=20, max_age_seconds=3)
    stale_primary = FieldEvidence(value=Decimal("10.00"), source="tdx", observed_at=NOW - timedelta(seconds=10), priority=10, max_age_seconds=3)

    result = arbitrator.select("price", (stale_primary, fresh), now=NOW)

    assert result.status == "selected"
    assert result.value == Decimal("10.01")
    assert result.source == "tencent"
    assert result.rejected_sources == ("tdx:stale",)


def test_arbitrator_preserves_material_price_conflict() -> None:
    arbitrator = FieldArbitrator(price_relative_tolerance=Decimal("0.001"))
    tdx = FieldEvidence(value=Decimal("10.00"), source="tdx", observed_at=NOW, priority=10, max_age_seconds=3)
    tencent = FieldEvidence(value=Decimal("10.20"), source="tencent", observed_at=NOW, priority=20, max_age_seconds=3)

    result = arbitrator.select("price", (tdx, tencent), now=NOW)

    assert result.status == "conflicted"
    assert result.value is None
    assert {item.source for item in result.evidence} == {"tdx", "tencent"}

