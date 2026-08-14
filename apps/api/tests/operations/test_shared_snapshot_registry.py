from datetime import date, datetime, timezone

from qibao_api.operations.shared_snapshots import SharedSnapshotRegistry


NOW = datetime(2026, 8, 12, 15, tzinfo=timezone.utc)


def test_shared_snapshot_registry_versions_new_content_and_distinguishes_reuse_from_duplicate_compute(tmp_path) -> None:
    registry = SharedSnapshotRegistry(tmp_path / "shared-snapshots.sqlite3")

    first = registry.record(
        "market_cross_section", content_hash="a" * 64,
        trade_date=date(2026, 8, 12), observed_at=NOW,
        coverage_percent=98.5, freshness="live", source="local-tdx",
        reused=False, latency_ms=120,
    )
    reused = registry.record(
        "market_cross_section", content_hash="a" * 64,
        trade_date=date(2026, 8, 12), observed_at=NOW,
        coverage_percent=98.5, freshness="live", source="local-tdx",
        reused=True, latency_ms=2,
    )
    duplicate = registry.record(
        "market_cross_section", content_hash="a" * 64,
        trade_date=date(2026, 8, 12), observed_at=NOW,
        coverage_percent=98.5, freshness="live", source="local-tdx",
        reused=False, latency_ms=115,
    )
    changed = registry.record(
        "market_cross_section", content_hash="b" * 64,
        trade_date=date(2026, 8, 12), observed_at=NOW,
        coverage_percent=99.0, freshness="live", source="local-tdx",
        reused=False, latency_ms=125,
    )

    assert first["snapshot_version"] == 1
    assert reused["snapshot_version"] == 1
    assert duplicate["snapshot_version"] == 1
    assert changed["snapshot_version"] == 2
    summary = registry.summary()[0]
    assert summary["compute_count"] == 3
    assert summary["reuse_count"] == 1
    assert summary["duplicate_compute_count"] == 1
    assert summary["cache_hit_rate"] == 25.0
    assert summary["content_hash"] == "b" * 64
    assert summary["coverage_percent"] == 99.0
    assert summary["slowest_compute_ms"] == 125


def test_shared_snapshot_registry_exposes_all_seven_snapshot_kinds_even_before_data_arrives(tmp_path) -> None:
    registry = SharedSnapshotRegistry(tmp_path / "shared-snapshots.sqlite3")

    summary = registry.summary()

    assert [item["kind"] for item in summary] == [
        "market_cross_section", "limit_events", "sector_strength",
        "stock_fund_flow", "news_events", "financial_valuation", "quant_factors",
    ]
    assert all(item["freshness"] == "unavailable" for item in summary)
    assert all(item["content_hash"] is None for item in summary)
