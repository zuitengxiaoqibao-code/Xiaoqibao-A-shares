from qibao_api.operations.performance_store import PerformanceStore


def test_performance_store_reports_recent_p50_p95_failure_and_cache_hit(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "performance.sqlite3", max_samples_per_key=10)
    for latency in (10, 20, 30, 40, 50):
        store.record("api", "/company-research", latency_ms=latency, success=latency < 50, cache_hit=latency in {10, 20})

    metric = store.summary()[0]

    assert metric["sample_count"] == 5
    assert metric["p50_ms"] == 30
    assert metric["p95_ms"] == 50
    assert metric["failure_rate"] == 20.0
    assert metric["cache_hit_rate"] == 40.0
    assert metric["recent_ms"] == [10, 20, 30, 40, 50]


def test_performance_store_keeps_only_the_configured_recent_samples(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "performance.sqlite3", max_samples_per_key=3)
    for latency in (10, 20, 30, 40):
        store.record("page", "company-research", latency_ms=latency, success=True)

    assert store.summary()[0]["recent_ms"] == [20, 30, 40]


def test_performance_store_includes_shared_snapshot_inventory_when_configured(tmp_path) -> None:
    class Snapshots:
        def summary(self):
            return [{"kind": "market_cross_section", "snapshot_version": 2}]

    store = PerformanceStore(
        tmp_path / "performance.sqlite3",
        shared_snapshot_registry=Snapshots(),
    )

    assert store.snapshot_summary() == [
        {"kind": "market_cross_section", "snapshot_version": 2},
    ]
