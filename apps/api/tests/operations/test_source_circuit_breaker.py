from qibao_api.operations.source_circuit_breaker import SourceCircuitBreaker


def test_circuit_breaker_opens_probes_and_recovers() -> None:
    breaker = SourceCircuitBreaker(failure_threshold=3, recovery_seconds=30)

    breaker.record_failure(now=0)
    breaker.record_failure(now=1)
    breaker.record_failure(now=2)
    assert breaker.before_request(now=10) is False
    assert breaker.status(now=10)["state"] == "open"

    assert breaker.before_request(now=32) is True
    assert breaker.status(now=32)["state"] == "half_open"
    breaker.record_success(now=33)
    assert breaker.status(now=33)["state"] == "closed"
    assert breaker.before_request(now=34) is True


def test_failed_half_open_probe_reopens_circuit() -> None:
    breaker = SourceCircuitBreaker(failure_threshold=1, recovery_seconds=10)
    breaker.record_failure(now=0)

    assert breaker.before_request(now=10) is True
    breaker.record_failure(now=10)

    assert breaker.before_request(now=15) is False
    assert breaker.status(now=15)["failures"] == 2
