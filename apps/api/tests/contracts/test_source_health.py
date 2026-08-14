from datetime import UTC, datetime

from qibao_api.contracts.source_health import (
    SourceHealthItem,
    SourceHealthResponse,
)


def _item(status: str) -> SourceHealthItem:
    return SourceHealthItem(
        source="fixture",
        operation="quotes",
        target="local",
        status=status,
        attempts=1,
        successes=1 if status == "ready" else 0,
        failures=0 if status == "ready" else 1,
        empty_responses=0,
        success_rate=100 if status == "ready" else 0,
        average_latency_ms=10,
        latest_latency_ms=10,
        last_success_at=datetime.now(UTC) if status == "ready" else None,
        last_failure_at=None if status == "ready" else datetime.now(UTC),
    )


def test_source_health_response_exposes_unambiguous_probe_counts() -> None:
    response = SourceHealthResponse(
        generated_at=datetime.now(UTC),
        window_size=20,
        sources=(_item("ready"), _item("degraded"), _item("unavailable")),
    )

    assert response.source_count == 3
    assert response.probed_count == 3
    assert response.ready_count == 1
    assert response.degraded_count == 1
    assert response.unavailable_count == 1
    assert response.observed_at == response.generated_at

