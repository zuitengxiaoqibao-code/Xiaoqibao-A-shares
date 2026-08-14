from dataclasses import dataclass
from typing import Literal


GateState = Literal["pass", "warning", "fail"]


@dataclass(frozen=True)
class QualityGateReport:
    state: GateState
    failures: tuple[str, ...]
    warnings: tuple[str, ...]


def evaluate_quality_gates(
    *,
    api_tests_passed: bool,
    web_tests_passed: bool,
    production_build_passed: bool,
    encoding_scan_passed: bool,
    smoke_passed: bool,
    data_integrity_ratio: float | None,
    minimum_integrity_ratio: float = 0.98,
) -> QualityGateReport:
    failures: list[str] = []
    warnings: list[str] = []
    for value, name in (
        (api_tests_passed, "api_tests"),
        (web_tests_passed, "web_tests"),
        (production_build_passed, "production_build"),
        (encoding_scan_passed, "encoding_scan"),
        (smoke_passed, "portable_smoke"),
    ):
        if not value:
            failures.append(name)
    if data_integrity_ratio is None:
        warnings.append("data_integrity_unavailable")
    elif not 0 <= data_integrity_ratio <= 1:
        failures.append("data_integrity_invalid")
    elif data_integrity_ratio < minimum_integrity_ratio:
        warnings.append("data_integrity_below_ready_threshold")
    return QualityGateReport(
        state="fail" if failures else "warning" if warnings else "pass",
        failures=tuple(failures),
        warnings=tuple(warnings),
    )

