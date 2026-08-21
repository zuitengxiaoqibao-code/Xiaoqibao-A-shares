import sqlite3

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


def test_performance_store_normalizes_dynamic_api_paths_and_query_strings(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "performance.sqlite3", release_id="release-2")

    store.record(
        "api",
        "/api/v1/a-shares/600519/company-research?refresh=true",
        latency_ms=120,
        success=True,
    )
    store.record(
        "api",
        "/api/v1/a-shares/000001/company-research?refresh=false",
        latency_ms=80,
        success=True,
    )
    store.record(
        "api",
        "/api/v1/operations/tasks/68b2654c-47f7-4e62-bfb9-7eaa34cad28e",
        latency_ms=15,
        success=True,
    )
    store.record(
        "api",
        "/api/v1/decisions/2026-08-21",
        latency_ms=25,
        success=True,
    )

    metrics = {item["name"]: item for item in store.summary()}

    assert metrics["/api/v1/a-shares/{symbol}/company-research"]["sample_count"] == 2
    assert "/api/v1/operations/tasks/{task_id}" in metrics
    assert "/api/v1/decisions/{trading_date}" in metrics


def test_performance_store_excludes_legacy_release_samples_from_current_summary(tmp_path) -> None:
    database = tmp_path / "performance.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE performance_sample (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                success INTEGER NOT NULL,
                cache_hit INTEGER,
                observed_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "INSERT INTO performance_sample(kind,name,latency_ms,success,cache_hit,observed_at) VALUES(?,?,?,?,?,?)",
            ("api", "/api/v1/a-shares/600519/company-research", 999999, 0, 0, "2026-08-01T00:00:00Z"),
        )

    store = PerformanceStore(database, release_id="release-2")
    store.record(
        "api",
        "/api/v1/a-shares/{symbol}/company-research",
        latency_ms=90,
        success=True,
    )

    current = store.summary()
    historical = store.summary(include_historical=True)

    assert current[0]["p95_ms"] == 90
    assert current[0]["release_id"] == "release-2"
    assert {item["release_id"] for item in historical} == {"legacy", "release-2"}


def test_performance_store_reports_status_source_and_truthful_cache_metadata(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "performance.sqlite3", release_id="release-2")

    store.record(
        "api",
        "/api/v1/a-shares/market-overview",
        latency_ms=45,
        success=True,
        cache_hit=True,
        status_code=206,
        response_source="last-good-cache",
        outcome="partial",
    )
    store.record(
        "api",
        "/api/v1/a-shares/market-overview",
        latency_ms=55,
        success=True,
        cache_hit=None,
        status_code=200,
        response_source="local-tdx",
        outcome="ready",
    )

    metric = store.summary()[0]

    assert metric["cache_hit_rate"] == 100.0
    assert metric["cache_observed_count"] == 1
    assert metric["status_counts"] == {"200": 1, "206": 1}
    assert metric["source_counts"] == {"last-good-cache": 1, "local-tdx": 1}
    assert metric["outcome_counts"] == {"partial": 1, "ready": 1}
