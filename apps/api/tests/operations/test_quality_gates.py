from qibao_api.operations.quality_gates import evaluate_quality_gates


def test_quality_gates_pass_when_build_and_integrity_are_ready() -> None:
    result = evaluate_quality_gates(
        api_tests_passed=True,
        web_tests_passed=True,
        production_build_passed=True,
        encoding_scan_passed=True,
        smoke_passed=True,
        data_integrity_ratio=1.0,
    )
    assert result.state == "pass"
    assert result.failures == ()
    assert result.warnings == ()


def test_quality_gates_warn_for_real_partial_data_without_blocking_release() -> None:
    result = evaluate_quality_gates(
        api_tests_passed=True,
        web_tests_passed=True,
        production_build_passed=True,
        encoding_scan_passed=True,
        smoke_passed=True,
        data_integrity_ratio=0.85,
    )
    assert result.state == "warning"
    assert result.warnings == ("data_integrity_below_ready_threshold",)


def test_quality_gates_fail_for_test_or_invalid_integrity_result() -> None:
    result = evaluate_quality_gates(
        api_tests_passed=False,
        web_tests_passed=True,
        production_build_passed=True,
        encoding_scan_passed=True,
        smoke_passed=True,
        data_integrity_ratio=2.0,
    )
    assert result.state == "fail"
    assert result.failures == ("api_tests", "data_integrity_invalid")


def test_quality_gates_fail_for_slow_or_untraceable_realtime_pipeline() -> None:
    result = evaluate_quality_gates(
        api_tests_passed=True,
        web_tests_passed=True,
        production_build_passed=True,
        encoding_scan_passed=True,
        smoke_passed=True,
        data_integrity_ratio=1.0,
        late_session_request_ms=9000,
        maximum_late_session_request_ms=8000,
        realtime_traceability_passed=False,
    )

    assert result.state == "fail"
    assert result.failures == ("late_session_latency", "realtime_traceability")
