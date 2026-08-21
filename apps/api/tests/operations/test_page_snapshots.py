from datetime import UTC, datetime

from qibao_api.operations.page_snapshots import PageSnapshotService


class Registry:
    def __init__(self, rows):
        self.rows = rows

    def summary(self):
        return self.rows


def row(kind, version=1):
    return {
        "kind": kind,
        "snapshot_version": version,
        "trade_date": "2026-08-21",
        "observed_at": datetime(2026, 8, 21, 1, 30, tzinfo=UTC).isoformat(),
        "coverage_percent": 98.5,
        "content_hash": "a" * 64,
        "freshness": "live",
        "source": "fixture",
    }


def test_market_page_projects_shared_versions_and_metadata():
    snapshot = PageSnapshotService(Registry([row("market_cross_section"), row("limit_events")])).snapshot("market_overview")
    assert snapshot.menu == "market_overview"
    assert snapshot.state == "partial"
    assert snapshot.usable_content is True
    assert snapshot.snapshot_versions["market_cross_section"] == 1
    assert snapshot.trade_date.isoformat() == "2026-08-21"
    assert snapshot.content_hash is not None
    assert "sector_strength" in (snapshot.reason or "")


def test_missing_shared_snapshot_is_truthful_and_fast():
    snapshot = PageSnapshotService(Registry([])).snapshot("quant_analysis")
    assert snapshot.state == "unavailable"
    assert snapshot.usable_content is False
    assert "quant_factors" in (snapshot.reason or "")
    assert snapshot.source == "unavailable"


def test_local_only_page_has_a_usable_contract_without_market_data():
    snapshot = PageSnapshotService(Registry([])).snapshot("settings")
    assert snapshot.state == "ready"
    assert snapshot.usable_content is True
