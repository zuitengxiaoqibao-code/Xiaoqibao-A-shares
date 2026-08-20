from datetime import date, datetime, timezone

from qibao_api.contracts.runtime_snapshot import RuntimeSnapshot
from qibao_api.runtime_snapshot import choose_runtime_snapshot


def make_snapshot(**overrides) -> RuntimeSnapshot[dict]:
    values = {
        "data": {"rows": [{"id": "a"}]},
        "status": "ready",
        "freshness": "current",
        "observed_at": datetime(2026, 8, 20, 2, 0, tzinfo=timezone.utc),
        "generated_at": datetime(2026, 8, 20, 2, 0, 1, tzinfo=timezone.utc),
        "trade_date": date(2026, 8, 20),
        "source": "test",
        "coverage": 100,
        "cache": {"state": "live", "cached_at": None},
        "progress": None,
        "error": None,
        "trace_id": "trace-current",
    }
    values.update(overrides)
    return RuntimeSnapshot[dict](**values)


def test_runtime_snapshot_keeps_nonempty_data_when_refresh_is_empty() -> None:
    current = make_snapshot()
    incoming = make_snapshot(
        data={"rows": []},
        status="partial",
        coverage=0,
        observed_at=datetime(2026, 8, 20, 2, 1, tzinfo=timezone.utc),
    )

    decision = choose_runtime_snapshot(
        current,
        incoming,
        is_empty=lambda payload: not payload.get("rows"),
    )

    assert decision.snapshot is current
    assert decision.reason == "新数据为空，继续展示上一次完整数据"


def test_runtime_snapshot_rejects_older_trade_date_and_lower_coverage() -> None:
    current = make_snapshot(coverage=98)
    older = make_snapshot(
        trade_date=date(2026, 8, 19),
        observed_at=datetime(2026, 8, 20, 3, 0, tzinfo=timezone.utc),
    )
    thinner = make_snapshot(
        coverage=40,
        observed_at=datetime(2026, 8, 20, 3, 0, tzinfo=timezone.utc),
    )

    assert choose_runtime_snapshot(current, older).snapshot is current
    assert choose_runtime_snapshot(current, thinner).snapshot is current


def test_runtime_snapshot_keeps_data_on_error_and_preserves_reason() -> None:
    current = make_snapshot()
    incoming = make_snapshot(
        data=None,
        status="error",
        observed_at=None,
        coverage=None,
        error={"code": "source_timeout", "message": "数据源连接超时"},
    )

    decision = choose_runtime_snapshot(current, incoming)

    assert decision.snapshot is current
    assert decision.reason == "数据源连接超时"
