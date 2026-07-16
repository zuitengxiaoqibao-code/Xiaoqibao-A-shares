from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.bars import DailyBar, DataSourceState, SyncAttempt, SyncReport


def test_daily_bar_rejects_inverted_high_low() -> None:
    with pytest.raises(ValidationError):
        DailyBar(
            symbol="600000",
            trade_date=date(2026, 7, 13),
            open=Decimal("8.50"),
            high=Decimal("8.00"),
            low=Decimal("9.00"),
            close=Decimal("8.80"),
            volume=100,
            amount=Decimal("880"),
            source="mootdx",
        )


def test_ready_sync_report_requires_export_path() -> None:
    with pytest.raises(ValidationError):
        SyncReport(
            symbol="600000",
            state=DataSourceState.READY,
            written_rows=20,
            source="mootdx",
            started_at=datetime(2026, 7, 13, 14, 0),
            finished_at=datetime(2026, 7, 13, 14, 1),
            message="同步完成",
        )


def test_sync_attempt_keeps_source_outcome_and_reason() -> None:
    attempt = SyncAttempt(source="mootdx", status="error", message="连接超时")

    assert attempt.source == "mootdx"
    assert attempt.status == "error"
    assert attempt.message == "连接超时"
