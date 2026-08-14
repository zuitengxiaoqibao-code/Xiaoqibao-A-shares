from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry


def test_evidence_ledger_requires_observation_for_ready_evidence() -> None:
    entry = EvidenceLedgerEntry(
        source="tdx-local-daily",
        operation="market_review",
        status="ready",
        trade_date=date(2026, 8, 10),
        observed_at=datetime(2026, 8, 10, 7, tzinfo=timezone.utc),
        formula_version="a-share-market-review-v2",
        sample_count=5000,
        limitations=(),
    )

    assert entry.sample_count == 5000


def test_evidence_ledger_rejects_ready_entry_without_timestamp() -> None:
    with pytest.raises(ValidationError):
        EvidenceLedgerEntry(
            source="tdx-local-daily",
            operation="market_review",
            status="ready",
            trade_date=date(2026, 8, 10),
            observed_at=None,
            formula_version="a-share-market-review-v2",
            sample_count=5000,
            limitations=(),
        )


def test_evidence_ledger_allows_unavailable_with_explicit_limitation() -> None:
    entry = EvidenceLedgerEntry(
        source="tdx-local-professional",
        operation="professional_probe",
        status="unavailable",
        trade_date=None,
        observed_at=None,
        formula_version=None,
        sample_count=None,
        limitations=("专业数据包未初始化",),
    )

    assert entry.status == "unavailable"
