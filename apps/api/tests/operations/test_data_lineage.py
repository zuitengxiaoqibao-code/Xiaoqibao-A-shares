from datetime import UTC, date, datetime

import pytest

from qibao_api.contracts.data_lineage import DataLineageRecord
from qibao_api.operations.data_lineage import DataLineageRepository


NOW = datetime(2026, 8, 15, 8, 0, tzinfo=UTC)


def _record(**overrides):
    values = {
        "domain": "quant_strategy",
        "field": "close",
        "symbol": "600519",
        "trade_date": date(2026, 8, 14),
        "observed_at": NOW,
        "source": "local-tdx",
        "source_version": "tdx-7.73",
        "content_hash": "a" * 64,
        "status": "ready",
        "coverage_percent": 99.5,
        "limitations": (),
    }
    values.update(overrides)
    return DataLineageRecord(**values)


def test_lineage_record_rejects_ready_without_observation_or_bad_hash():
    with pytest.raises(ValueError, match="ready lineage requires observed_at"):
        _record(observed_at=None)
    with pytest.raises(ValueError, match="content_hash must be SHA-256"):
        _record(content_hash="bad")


def test_lineage_repository_is_append_only_and_filters_records(tmp_path):
    repository = DataLineageRepository(tmp_path / "data-lineage.sqlite3")
    first = repository.append(_record())
    repository.append(_record(
        field="volume",
        content_hash="b" * 64,
        status="partial",
        coverage_percent=85.0,
        limitations=("部分股票缺少成交量",),
    ))

    rows = repository.list(domain="quant_strategy", symbol="600519", field="volume")

    assert first["lineage_id"].startswith("lineage-")
    assert first["content_hash"] == "a" * 64
    assert len(rows) == 1
    assert rows[0]["field"] == "volume"
    assert rows[0]["status"] == "partial"
    assert rows[0]["coverage_percent"] == 85.0
    with pytest.raises(Exception):
        repository.connection.execute("DELETE FROM data_lineage")
    repository.close()


def test_lineage_repository_reports_unavailable_limits_explicitly(tmp_path):
    repository = DataLineageRepository(tmp_path / "data-lineage.sqlite3")

    with pytest.raises(ValueError, match="unavailable lineage requires limitations"):
        repository.append(_record(status="unavailable", limitations=()))

    repository.close()
