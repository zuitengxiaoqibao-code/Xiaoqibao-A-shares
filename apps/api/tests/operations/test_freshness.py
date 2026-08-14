from datetime import UTC, datetime, timedelta

from qibao_api.operations.freshness import FreshnessPolicy, classify_freshness


NOW = datetime(2026, 8, 12, 6, 0, tzinfo=UTC)


def test_freshness_policy_distinguishes_live_fresh_stale_expired_and_unavailable() -> None:
    policy = FreshnessPolicy(live_seconds=120, fresh_seconds=600, stale_seconds=3600)

    assert classify_freshness(NOW - timedelta(seconds=60), NOW, policy).state == "live"
    assert classify_freshness(NOW - timedelta(seconds=300), NOW, policy).state == "fresh"
    assert classify_freshness(NOW - timedelta(seconds=1800), NOW, policy).state == "stale"
    assert classify_freshness(NOW - timedelta(seconds=7200), NOW, policy).state == "expired"
    assert classify_freshness(None, NOW, policy).state == "unavailable"


def test_freshness_result_exposes_age_and_reason() -> None:
    result = classify_freshness(
        NOW - timedelta(seconds=300),
        NOW,
        FreshnessPolicy(live_seconds=120, fresh_seconds=600, stale_seconds=3600),
    )

    assert result.age_seconds == 300
    assert "600" in result.reason

