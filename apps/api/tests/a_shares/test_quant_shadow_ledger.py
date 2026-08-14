from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3
import pytest

from qibao_api.a_shares.quant_shadow_ledger import QuantShadowLedgerStore
from qibao_api.contracts.bars import DailyBar


NOW = datetime(2026, 8, 11, 8, tzinfo=timezone.utc)


def _dashboard(regime: str = "轮动震荡"):
    from qibao_api.contracts.quant_strategy import QuantStrategyCandidate, QuantStrategyDashboard
    from qibao_api.contracts.market_overview import OverviewRegimeAssessment, OverviewRegimeMetrics
    from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry

    candidate = QuantStrategyCandidate(
        symbol="600001", name="测试", model="0轴低吸模型", strategy_score=Decimal("82"),
        regime_match=Decimal("1"), stock_score=Decimal("0.8"), trigger_score=Decimal("1"),
        rr_score=Decimal("0"), risk_penalty=Decimal("0"), status="watch",
        trigger_confirmed=True, position=Decimal("0"), planned_position=Decimal("0"),
        reference_price=Decimal("10"), evidence_coverage_percent=Decimal("100"),
        buy_triggers=("确认",), invalidation_rules=("失效",), factor_as_of=date(2026, 8, 11),
    )
    observed = NOW
    return QuantStrategyDashboard(
        status="ready", as_of=date(2026, 8, 11), observed_at=observed, generated_at=observed,
        market_observed_at=observed, data_age_seconds=0, refresh_mode="postclose",
        next_refresh_at=observed, metrics=OverviewRegimeMetrics(), regime=OverviewRegimeAssessment(
            regime=regime,
            emotion_score=Decimal("55"), risk_score=Decimal("30"),
            heat_score=Decimal("50"), rotation_score=Decimal("62"),
            coverage_percent=Decimal("80"), market_coef=Decimal("0.5"),
            suitable_strategies=("0轴低吸模型",), avoid_strategies=("高开追涨",),
            reasons=("测试冻结风格",), missing_factors=(), quality="ready",
        ),
        evidence_ledger=(EvidenceLedgerEntry(source="test", operation="test", status="ready", observed_at=observed, sample_count=1),),
        input_snapshot_ids=("market-snapshot-20260811",),
        candidates=(candidate,), discipline="观察",
    )


def _bar(day: int, close: str, high: str | None = None, low: str | None = None):
    value = Decimal(close)
    return DailyBar(
        symbol="600001", trade_date=date(2026, 8, 11) + timedelta(days=day),
        open=value, high=Decimal(high or close), low=Decimal(low or close), close=value,
        volume=100, amount=value * 100, source="test",
    )


def test_freeze_is_immutable_and_evaluates_only_mature_real_windows(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    dashboard = _dashboard()

    assert store.freeze(dashboard) == 1
    assert store.freeze(dashboard) == 0

    # Obtain the deterministic id from the stored row without relying on internals.
    import sqlite3
    with sqlite3.connect(tmp_path / "shadow.sqlite3") as connection:
        decision_id = connection.execute("SELECT decision_id FROM quant_shadow_decisions").fetchone()[0]

    outcomes = store.evaluate(decision_id, [_bar(1, "10.50", "11", "9.5"), _bar(2, "10.80")])

    assert outcomes[0].status == "ready"
    assert outcomes[0].return_percent == Decimal("5.00")
    assert outcomes[0].mfe_percent == Decimal("10.00")
    assert outcomes[0].mae_percent == Decimal("-5.00")
    assert outcomes[1].status == "pending"
    assert outcomes[1].limitation == "未来真实日线不足 3 个交易日"
    assert store.get(decision_id).market_regime == "轮动震荡"


def test_candidate_lifecycle_is_append_only_and_rejects_invalid_transitions(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    store.freeze(_dashboard())
    with sqlite3.connect(store.database_path) as connection:
        decision_id = connection.execute("SELECT decision_id FROM quant_shadow_decisions").fetchone()[0]

    assert store.lifecycle(decision_id) == ("observed",)
    assert store.get(decision_id).input_snapshot_ids == ("market-snapshot-20260811",)
    store.transition(decision_id, "triggered", reason="盘中触发条件已确认", snapshot_id="snapshot-1")
    store.transition(decision_id, "reviewed", reason="人工复核完成", snapshot_id="snapshot-2")
    assert store.lifecycle(decision_id) == ("observed", "triggered", "reviewed")
    with pytest.raises(ValueError, match="invalid candidate lifecycle transition"):
        store.transition(decision_id, "triggered", reason="重复回退", snapshot_id="snapshot-3")


def test_analytics_groups_mature_results_by_frozen_six_regime_snapshot(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    _seed_analytics_rows(
        store.database_path,
        [(82, "3", "5", "-1", "2026-07-01"), (82, "-2", "1", "-4", "2026-07-02")],
        regimes=["情绪主升", "高位退潮"],
    )

    analytics = store.analytics(horizon=5)

    by_name = {item.regime: item for item in analytics.regime_performance}
    assert by_name["情绪主升"].sample_count == 1
    assert by_name["情绪主升"].hit_rate_percent == Decimal("100.00")
    assert by_name["情绪主升"].expected_value_percent == Decimal("3.00")
    assert by_name["高位退潮"].sample_count == 1
    assert by_name["高位退潮"].hit_rate_percent == Decimal("0.00")
    assert by_name["高位退潮"].max_consecutive_losses == 1


def test_evaluate_blocks_returns_when_future_bar_sequence_has_duplicate_trade_date(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    store.freeze(_dashboard())
    with sqlite3.connect(store.database_path) as connection:
        decision_id = connection.execute(
            "SELECT decision_id FROM quant_shadow_decisions"
        ).fetchone()[0]

    duplicate_day = _bar(1, "10.50")
    outcomes = store.evaluate(decision_id, [duplicate_day, duplicate_day])

    assert all(outcome.status == "unavailable" for outcome in outcomes)
    assert all(outcome.return_percent is None for outcome in outcomes)
    assert "重复交易日" in (outcomes[0].limitation or "")


def test_evaluate_keeps_large_jump_as_warning_without_rewriting_real_return(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    store.freeze(_dashboard())
    with sqlite3.connect(store.database_path) as connection:
        decision_id = connection.execute(
            "SELECT decision_id FROM quant_shadow_decisions"
        ).fetchone()[0]

    outcomes = store.evaluate(
        decision_id,
        [_bar(1, "10.00"), _bar(2, "14.00", "14.50", "13.50"), _bar(3, "14.20")],
    )

    assert outcomes[1].status == "ready"
    assert outcomes[1].return_percent == Decimal("42.00")
    assert "跳变超过 35%" in (outcomes[1].limitation or "")


def _seed_analytics_rows(
    database_path,
    rows: list[tuple[int, str, str, str, str]],
    *,
    horizon: int = 5,
    regimes: list[str | None] | None = None,
) -> None:
    """Insert frozen decisions and mature outcomes for analytics-only tests."""
    with sqlite3.connect(database_path) as connection:
        for index, (score, return_percent, mfe_percent, mae_percent, as_of) in enumerate(rows):
            decision_id = f"analytics-{index:03d}"
            connection.execute(
                """INSERT INTO quant_shadow_decisions
                (decision_id, as_of, symbol, formula_version, candidate_status,
                 strategy_score, reference_price, candidate_json, frozen_at, market_regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision_id,
                    as_of,
                    f"{600000 + index:06d}",
                    "a-share-short-strategy-v2.0",
                    "watch",
                    str(score),
                    "10",
                    json.dumps({"symbol": f"{600000 + index:06d}"}),
                    NOW.isoformat(),
                    regimes[index] if regimes and index < len(regimes) else None,
                ),
            )
            connection.execute(
                """INSERT INTO quant_shadow_outcomes
                (decision_id, horizon, status, evaluated_trade_date, return_percent,
                 mfe_percent, mae_percent, invalidation_state, evaluated_at, limitation)
                VALUES (?, ?, 'ready', ?, ?, ?, ?, 'unavailable', ?, NULL)""",
                (
                    decision_id,
                    horizon,
                    "2026-08-11",
                    return_percent,
                    mfe_percent,
                    mae_percent,
                    NOW.isoformat(),
                ),
            )


def test_analytics_refuses_reliability_claim_when_mature_sample_is_too_small(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    _seed_analytics_rows(
        store.database_path,
        [(75, "2", "4", "-1", f"2026-07-{day:02d}") for day in range(1, 6)],
    )

    analytics = store.analytics(horizon=5)

    assert analytics.status == "insufficient"
    assert analytics.mature_sample_count == 5
    assert analytics.hit_rate_percent == Decimal("100.00")
    assert analytics.drift.status == "insufficient"
    assert "成熟样本少于 20 条" in analytics.limitations[0]


def test_analytics_builds_score_buckets_and_brier_from_mature_outcomes(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    rows: list[tuple[int, str, str, str, str]] = []
    for index, score in enumerate((60, 65, 66, 68, 69, 70, 72, 74, 76, 79, 80, 82, 84, 86, 89, 90, 92, 94, 96, 100)):
        positive = index % 2 == 0
        rows.append((
            score,
            "2" if positive else "-1",
            "4" if positive else "1",
            "-1" if positive else "-3",
            f"2026-07-{index + 1:02d}",
        ))
    _seed_analytics_rows(store.database_path, rows)

    analytics = store.analytics(horizon=5)

    assert analytics.status == "ready"
    assert analytics.mature_sample_count == 20
    assert analytics.hit_rate_percent == Decimal("50.00")
    assert analytics.average_return_percent == Decimal("0.50")
    assert analytics.average_mfe_percent == Decimal("2.50")
    assert analytics.average_mae_percent == Decimal("-2.00")
    assert analytics.brier_score == Decimal("0.3623")
    assert [(bucket.label, bucket.sample_count) for bucket in analytics.buckets] == [
        ("0-69", 5),
        ("70-79", 5),
        ("80-89", 5),
        ("90-100", 5),
    ]
    assert all(bucket.status == "ready" for bucket in analytics.buckets)
    assert analytics.buckets[0].hit_rate_percent == Decimal("60.00")
    assert analytics.buckets[1].hit_rate_percent == Decimal("40.00")


def test_analytics_detects_recent_strategy_drift_against_earlier_baseline(tmp_path) -> None:
    store = QuantShadowLedgerStore(tmp_path / "shadow.sqlite3", clock=lambda: NOW)
    rows: list[tuple[int, str, str, str, str]] = []
    for index in range(10):
        rows.append((82, "3", "5", "-1", f"2026-06-{index + 1:02d}"))
    for index in range(10):
        rows.append((82, "-2", "1", "-4", f"2026-07-{index + 1:02d}"))
    _seed_analytics_rows(store.database_path, rows)

    analytics = store.analytics(horizon=5)

    assert analytics.drift.status == "drift"
    assert analytics.drift.baseline_sample_count == 10
    assert analytics.drift.recent_sample_count == 10
    assert analytics.drift.baseline_hit_rate_percent == Decimal("100.00")
    assert analytics.drift.recent_hit_rate_percent == Decimal("0.00")
    assert analytics.drift.baseline_average_return_percent == Decimal("3.00")
    assert analytics.drift.recent_average_return_percent == Decimal("-2.00")
    assert "近期命中率较基线下降至少 20 个百分点" in analytics.drift.reasons
