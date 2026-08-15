from datetime import UTC, datetime

from qibao_api.a_shares.source_arbitration import select_preferred


NOW = datetime(2026, 8, 15, 8, 0, tzinfo=UTC)


def test_select_preferred_keeps_conflicting_candidates_and_uses_source_priority():
    result = select_preferred((
        {
            "source": "tencent",
            "value": "100.00",
            "observed_at": NOW,
            "coverage_percent": 100,
        },
        {
            "source": "local-tdx",
            "value": "99.98",
            "observed_at": datetime(2026, 8, 15, 7, 59, tzinfo=UTC),
            "coverage_percent": 98,
        },
    ), cutoff=NOW)

    assert result["status"] == "conflict"
    assert result["selected"]["source"] == "local-tdx"
    assert len(result["candidates"]) == 2
    assert "source_values_disagree" in result["limitations"]


def test_select_preferred_excludes_future_candidates_and_reports_unavailable():
    result = select_preferred((
        {
            "source": "tencent",
            "value": "100.00",
            "observed_at": datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        },
    ), cutoff=NOW)

    assert result["status"] == "unavailable"
    assert result["selected"] is None
    assert result["candidates"] == []
    assert "no_candidate_observed_before_cutoff" in result["limitations"]


def test_select_preferred_considers_coverage_after_source_priority():
    result = select_preferred((
        {
            "source": "eastmoney",
            "value": "10",
            "observed_at": NOW,
            "coverage_percent": 80,
        },
        {
            "source": "eastmoney",
            "value": "10",
            "observed_at": NOW,
            "coverage_percent": 95,
        },
    ), cutoff=NOW)

    assert result["status"] == "ready"
    assert result["selected"]["coverage_percent"] == 95
    assert result["limitations"] == []
