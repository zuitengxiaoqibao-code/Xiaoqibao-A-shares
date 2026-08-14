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


def test_evidence_ledger_rejects_coverage_outside_zero_to_one_hundred() -> None:
    with pytest.raises(ValidationError, match="coverage_percent"):
        EvidenceLedgerEntry(
            source="tdx-local-daily",
            operation="market_review",
            status="partial",
            trade_date=date(2026, 8, 10),
            observed_at=datetime(2026, 8, 10, 7, tzinfo=timezone.utc),
            sample_count=5000,
            total_count=5200,
            coverage_percent=101.0,
            limitations=("少量股票缺失日线",),
        )


def test_evidence_ledger_rejects_sample_count_above_total_count() -> None:
    with pytest.raises(ValidationError, match="sample_count cannot exceed total_count"):
        EvidenceLedgerEntry(
            source="tdx-local-daily",
            operation="market_review",
            status="partial",
            trade_date=date(2026, 8, 10),
            observed_at=datetime(2026, 8, 10, 7, tzinfo=timezone.utc),
            sample_count=5201,
            total_count=5200,
            coverage_percent=100.0,
            limitations=("样本口径异常",),
        )
