from qibao_api.operations.refresh_policy import RefreshPolicy


def test_refresh_policy_prioritizes_visible_intraday_topics() -> None:
    policy = RefreshPolicy()

    assert policy.interval_ms("index_minutes", phase="intraday", visible=True) == 1000
    assert policy.interval_ms("late_session_candidates", phase="intraday", visible=True) == 1000
    assert policy.interval_ms("market_cross_section", phase="intraday", visible=True) == 10000
    assert policy.interval_ms("company_research", phase="intraday", visible=True) is None


def test_refresh_policy_reduces_hidden_and_post_close_work() -> None:
    policy = RefreshPolicy()

    assert policy.interval_ms("late_session_candidates", phase="intraday", visible=False) == 10000
    assert policy.interval_ms("index_minutes", phase="post_close", visible=True) == 60000
    assert policy.interval_ms("market_cross_section", phase="post_close", visible=True) == 300000

