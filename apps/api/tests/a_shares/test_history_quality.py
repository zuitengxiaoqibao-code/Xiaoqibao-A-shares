from datetime import date, datetime, timezone

from qibao_api.a_shares.history_quality import inspect_history_quality


def test_history_quality_reports_missing_duplicate_and_future_dates() -> None:
    sessions = [date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 12)]
    report = inspect_history_quality(
        sessions,
        ["600000", "000001"],
        {
            "600000": [date(2026, 8, 10), date(2026, 8, 10), date(2026, 8, 13)],
            "000001": sessions,
        },
        observed_at=datetime(2026, 8, 13, 1, tzinfo=timezone.utc),
    )

    assert report.status == "partial"
    assert report.expected_sessions == 3
    assert report.covered_sessions == 3
    assert report.coverage_ratio == 1
    assert report.gap_count == 1
    assert report.gaps[0].symbol == "600000"
    assert report.gaps[0].missing_dates == (date(2026, 8, 11), date(2026, 8, 12))
    assert report.gaps[0].duplicate_dates == (date(2026, 8, 10),)
    assert report.gaps[0].future_dates == (date(2026, 8, 13),)


def test_history_quality_is_unavailable_without_sessions_or_symbols() -> None:
    assert inspect_history_quality([], ["600000"], {}).status == "unavailable"
    assert inspect_history_quality([date(2026, 8, 10)], [], {}).status == "unavailable"

