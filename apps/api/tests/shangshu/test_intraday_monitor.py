import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from qibao_api.a_shares.models import CandidateBoard
from qibao_api.contracts.decision import (
    AdviceCard, DecisionCycleAggregate, DecisionCycleSnapshot, EvidenceReference,
)
from qibao_api.contracts.market import AssetKind
from qibao_api.gongbu.market_feed import MarketFeedSnapshot
from qibao_api.shangshu.decision_runtime import DeterministicIntradayEvaluator
from qibao_api.shangshu.intraday_monitor import (
    AdviceChangeDetector, IntradayEvaluationResult, IntradayMonitor,
    PollState, PollStateRepository,
)
from qibao_api.shangshu.decision_repository import DecisionRepository
from qibao_api.zhongshu.decision_ai import DecisionAIResult
from qibao_api.zhongshu.premarket_decision import (
    CandidateInputSnapshot, ComplianceInputSnapshot, MarketRiskInputSnapshot,
)


NOW = datetime(2026, 7, 14, 2, 30, tzinfo=UTC)


class Calendar:
    def __init__(self, confirmed=True): self.confirmed = confirmed
    def is_trading_day(self, value: date): return self.confirmed and value == date(2026, 7, 14)


class Feed:
    def __init__(self):
        self.calls = []
        self.fail = False

    def snapshot_many(self, symbols, *, cutoff=None):
        self.calls.append((symbols, cutoff))
        if self.fail:
            raise RuntimeError("feed unavailable")
        return tuple(type("Quote", (), {"symbol": symbol, "observed_at": cutoff})() for symbol in symbols)


def monitor(tmp_path, *, feed=None, calendar=None):
    return IntradayMonitor(
        feed=feed or Feed(), calendar=calendar or Calendar(),
        state_repository=PollStateRepository(tmp_path / "poll.sqlite3"),
        focus_symbols=lambda now: ("000001",),
        universe_symbols=lambda now: ("300001", "123001"),
    )


def test_initial_due_schedule_and_restart_recovery(tmp_path) -> None:
    first = monitor(tmp_path)
    assert first.due(NOW) == frozenset({"focus", "universe"})
    result = first.check(NOW)
    assert result.polled == frozenset({"focus", "universe"})
    assert first.due(NOW + timedelta(seconds=59)) == frozenset()
    assert first.due(NOW + timedelta(seconds=60)) == frozenset({"focus"})
    assert first.due(NOW + timedelta(seconds=180)) == frozenset({"focus", "universe"})
    restarted = monitor(tmp_path)
    assert restarted.due(NOW + timedelta(seconds=60)) == frozenset({"focus"})


def test_failure_backoff_caps_and_success_resets(tmp_path) -> None:
    feed = Feed()
    feed.fail = True
    value = monitor(tmp_path, feed=feed)
    due = NOW
    expected = [60, 120, 240, 300]
    for seconds in expected:
        value.check(due, scopes=frozenset({"focus"}))
        state = value.state
        assert state.focus_interval_seconds == seconds
        assert state.mode == "degraded"
        assert state.last_error_code == "runtime_error"
        due = state.next_focus_due_at
    feed.fail = False
    value.check(due, scopes=frozenset({"focus"}))
    assert value.state.consecutive_focus_failures == 0
    assert value.state.focus_interval_seconds == 60


def test_focus_and_universe_keep_independent_error_codes_during_recovery(tmp_path) -> None:
    class ScopeFeed:
        def __init__(self):
            self.focus_error = TimeoutError("focus timeout")
            self.universe_error = ValueError("universe incomplete")

        def snapshot_many(self, symbols, *, cutoff=None):
            error = self.focus_error if symbols == ("000001",) else self.universe_error
            if error is not None:
                raise error
            return tuple(
                type("Quote", (), {"symbol": symbol, "observed_at": cutoff})()
                for symbol in symbols
            )

    feed = ScopeFeed()
    value = monitor(tmp_path, feed=feed)

    value.check(NOW, scopes=frozenset({"focus", "universe"}))

    assert value.state.focus_error_code == "timeout_error"
    assert value.state.universe_error_code == "value_error"
    assert value.state.consecutive_focus_failures == 1
    assert value.state.consecutive_universe_failures == 1

    feed.focus_error = None
    value.check(NOW + timedelta(seconds=60), scopes=frozenset({"focus"}))

    assert value.state.focus_error_code is None
    assert value.state.universe_error_code == "value_error"
    assert value.state.mode == "degraded"
    assert value.state.last_error_code == "value_error"


def test_no_poll_outside_window_or_unconfirmed_day(tmp_path) -> None:
    feed = Feed()
    value = monitor(tmp_path, feed=feed)
    assert value.check(datetime(2026, 7, 14, 1, 24, tzinfo=UTC)).polled == frozenset()
    assert monitor(tmp_path / "other", feed=feed, calendar=Calendar(False)).check(NOW).polled == frozenset()
    assert feed.calls == []


def test_universe_filters_convertible_bonds(tmp_path) -> None:
    feed = Feed()
    value = monitor(tmp_path, feed=feed)
    value.check(NOW, scopes=frozenset({"universe"}))
    assert feed.calls[0][0] == ("300001",)
    assert value.state_repository.snapshots() == [{
        "scope": "universe", "symbol": "300001",
        "observed_at": NOW.isoformat(), "source_snapshot_id": None,
    }]


def advice(advice_id="a1", **updates):
    evidence = EvidenceReference(
        evidence_id="e1", source="test", snapshot_id="s1", summary="factor",
        observed_at=NOW,
    )
    values = dict(
        advice_id=advice_id, snapshot_id="snapshot-1", asset=AssetKind.A_SHARE,
        symbol="000001", horizon="intraday", observation_state="candidate",
        action="observe", conclusion="unchanged", confidence=Decimal("0.5"),
        supporting_evidence=(evidence,), contrary_evidence=(), risks=("risk",),
        invalidation_conditions=("condition",), quantitative_result={"membership": "short_term"},
        strategy_version="v1", created_at=NOW,
    )
    values.update(updates)
    return AdviceCard(**values)


def test_advice_change_sets_previous_id_and_exact_sorted_fields() -> None:
    detector = AdviceChangeDetector()
    updated = detector.changed(
        advice(), advice("a2", action="wait", risks=("new risk",), conclusion="changed")
    )
    assert updated is not None
    assert updated.previous_advice_id == "a1"
    assert updated.changed_fields == ("action", "conclusion", "risks")
    assert detector.changed(updated, updated.model_copy(update={"advice_id": "a3"})) is None


def test_removed_candidate_is_invalidated_once_and_future_evidence_rejected() -> None:
    detector = AdviceChangeDetector()
    previous = advice(
        ai_interpretation_id="premarket-ai-old",
        plain_language_explanation="旧模型解释。",
        quantitative_result={
            "membership": "short_term", "ai_provider": "old", "kept": "value",
        },
    )
    invalidated = detector.removed(previous, "candidate_removed", NOW)
    assert invalidated is not None and invalidated.action == "invalidated"
    assert invalidated.ai_interpretation_id is None
    assert invalidated.plain_language_explanation == (
        "候选状态发生变化：candidate_removed。原建议已失效，等待重新核验。"
    )
    assert invalidated.quantitative_result["kept"] == "value"
    assert "ai_provider" not in invalidated.quantitative_result
    assert detector.removed(invalidated, "candidate_removed", NOW) is None
    future = advice("future", supporting_evidence=(
        EvidenceReference(
            evidence_id="e2", source="test", snapshot_id="s2", summary="future",
            observed_at=NOW + timedelta(seconds=1),
        ),
    ))
    with pytest.raises(ValueError, match="future evidence"):
        detector.validate_cutoff(future, NOW)


def test_success_batch_and_state_are_atomic_idempotent_and_restart_safe(tmp_path) -> None:
    database = tmp_path / "poll.sqlite3"
    repository = PollStateRepository(database)
    state = PollState(
        last_focus_success_at=NOW, next_focus_due_at=NOW + timedelta(seconds=60),
        next_universe_due_at=NOW,
    )
    snapshot = type("Quote", (), {
        "symbol": "000001", "observed_at": NOW, "source_snapshot_id": "q1",
    })()
    assert repository.append_success_batch("batch-1", "focus", (snapshot,), state, NOW)
    assert not repository.append_success_batch("batch-1", "focus", (snapshot,), state, NOW)
    reopened = PollStateRepository(database)
    assert reopened.latest() == state
    assert len(reopened.snapshots()) == 1
    indexes = {
        row["name"] for row in reopened.connection.execute(
            "PRAGMA index_list(intraday_market_snapshot_events)"
        ).fetchall()
    }
    assert "ix_intraday_market_symbol_observed" in indexes
    query_plan = reopened.connection.execute(
        "EXPLAIN QUERY PLAN SELECT payload FROM intraday_market_snapshot_events "
        "WHERE symbol=? AND payload IS NOT NULL ORDER BY observed_at, sequence",
        ("000001",),
    ).fetchall()
    assert any(
        "ix_intraday_market_symbol_observed" in row["detail"]
        for row in query_plan
    )


def test_identical_snapshot_on_two_due_executions_advances_restart_due_time(tmp_path) -> None:
    class IdenticalFeed:
        def snapshot_many(self, symbols, *, cutoff=None):
            return (type("Quote", (), {
                "symbol": "300001", "observed_at": NOW, "source_snapshot_id": "same",
            })(),)

    database = tmp_path / "identical.sqlite3"
    first = IntradayMonitor(
        feed=IdenticalFeed(), calendar=Calendar(),
        state_repository=PollStateRepository(database), focus_symbols=lambda now: (),
        universe_symbols=lambda now: ("300001",),
    )
    first.check(NOW, scopes=frozenset({"universe"}))
    second_at = NOW + timedelta(seconds=180)
    first.check(second_at, scopes=frozenset({"universe"}))
    restarted = IntradayMonitor(
        feed=IdenticalFeed(), calendar=Calendar(),
        state_repository=PollStateRepository(database), focus_symbols=lambda now: (),
        universe_symbols=lambda now: ("300001",),
    )
    assert restarted.due(second_at + timedelta(seconds=179)) == frozenset({"focus"})
    assert restarted.due(second_at + timedelta(seconds=180)) == frozenset({"focus", "universe"})


def test_due_executions_advance_state_but_persist_only_changed_quote_content(tmp_path) -> None:
    class ContentFeed:
        def __init__(self):
            self.prices = {"000001": Decimal("10"), "300001": Decimal("20")}

        def snapshot_many(self, symbols, *, cutoff=None):
            return tuple(MarketFeedSnapshot(
                symbol=symbol, price=self.prices[symbol], change=Decimal("0"),
                change_percent=Decimal("0"), volume=Decimal("100"), source="test",
                observed_at=cutoff, fetched_at=cutoff, quality="ready",
                source_snapshot_id=f"execution-{int(cutoff.timestamp())}-{symbol}",
            ) for symbol in symbols)

    database = tmp_path / "content.sqlite3"
    feed = ContentFeed()
    value = IntradayMonitor(
        feed=feed, calendar=Calendar(), state_repository=PollStateRepository(database),
        focus_symbols=lambda now: (), universe_symbols=lambda now: ("000001", "300001"),
    )
    value.check(NOW, scopes=frozenset({"universe"}))
    value.check(NOW + timedelta(seconds=180), scopes=frozenset({"universe"}))
    assert len(value.state_repository.success_states("universe")) == 2
    assert len(value.state_repository.snapshots()) == 2

    feed.prices["000001"] = Decimal("10.1")
    value.check(NOW + timedelta(seconds=360), scopes=frozenset({"universe"}))
    reopened = PollStateRepository(database)
    assert len(reopened.success_states("universe")) == 3
    assert len(reopened.snapshots()) == 3
    latest = {item.symbol: item for item in reopened.latest_snapshots(NOW + timedelta(seconds=360))}
    assert latest["000001"].price == Decimal("10.1")
    assert latest["300001"].price == Decimal("20")


def test_intraday_snapshots_filter_symbol_trading_date_and_cutoff(tmp_path) -> None:
    repository = PollStateRepository(tmp_path / "intraday-read.sqlite3")
    state = PollState(
        last_focus_success_at=NOW,
        next_focus_due_at=NOW + timedelta(seconds=60),
        next_universe_due_at=NOW,
    )

    def snapshot(symbol: str, price: str, observed_at: datetime) -> MarketFeedSnapshot:
        return MarketFeedSnapshot(
            symbol=symbol,
            price=Decimal(price),
            change=Decimal(price) - Decimal("10"),
            change_percent=(Decimal(price) / Decimal("10") - Decimal("1")) * 100,
            volume=Decimal("1000"),
            source="test",
            observed_at=observed_at,
            fetched_at=observed_at,
            quality="ready",
            source_snapshot_id=f"{symbol}-{observed_at.isoformat()}",
        )

    previous_day = NOW - timedelta(days=1)
    later = NOW + timedelta(minutes=1)
    after_cutoff = NOW + timedelta(minutes=2)
    for index, value in enumerate((
        snapshot("000001", "9.9", previous_day),
        snapshot("000001", "10.1", NOW),
        snapshot("300001", "20", NOW),
        snapshot("000001", "10.2", later),
        snapshot("000001", "10.3", after_cutoff),
    )):
        repository.append_success_batch(
            f"batch-read-{index}", "focus", (value,), state, value.observed_at,
        )

    result = repository.intraday_snapshots(
        "000001", date(2026, 7, 14), cutoff=later,
    )

    assert [item.price for item in result] == [Decimal("10.1"), Decimal("10.2")]
    assert [item.observed_at for item in result] == [NOW, later]


def test_older_focus_quote_cannot_replace_fresher_universe_quote_across_restart(tmp_path) -> None:
    class CrossoverFeed:
        def __init__(self):
            self.stale = False

        def snapshot_many(self, symbols, *, cutoff=None):
            observed = NOW - timedelta(seconds=10) if self.stale else NOW
            price = Decimal("9") if self.stale else Decimal("10")
            return tuple(MarketFeedSnapshot(
                symbol=symbol, price=price, change=Decimal("0"),
                change_percent=Decimal("0"), volume=Decimal("100"), source="test",
                observed_at=observed, fetched_at=cutoff, quality="ready",
                source_snapshot_id=f"{'stale' if self.stale else 'fresh'}-{symbol}",
            ) for symbol in symbols)

    database = tmp_path / "crossover.sqlite3"
    feed = CrossoverFeed()
    value = IntradayMonitor(
        feed=feed, calendar=Calendar(), state_repository=PollStateRepository(database),
        focus_symbols=lambda now: ("000001",), universe_symbols=lambda now: ("000001",),
    )
    value.check(NOW, scopes=frozenset({"universe"}))
    feed.stale = True
    value.check(NOW + timedelta(seconds=60), scopes=frozenset({"focus"}))
    reopened = PollStateRepository(database)
    latest = reopened.latest_snapshots(NOW + timedelta(seconds=60))
    assert len(reopened.snapshots()) == 1
    assert latest[0].price == Decimal("10")
    assert latest[0].observed_at == NOW


def test_identical_content_persists_once_per_beijing_trading_date_across_restart(tmp_path) -> None:
    next_day = NOW + timedelta(days=1)

    class TwoDayCalendar:
        def is_trading_day(self, value):
            return value in {date(2026, 7, 14), date(2026, 7, 15)}

    class SameContentFeed:
        def snapshot_many(self, symbols, *, cutoff=None):
            return tuple(MarketFeedSnapshot(
                symbol=symbol, price=Decimal("10"), change=Decimal("0"),
                change_percent=Decimal("0"), volume=Decimal("100"), source="test",
                observed_at=cutoff, fetched_at=cutoff, quality="ready",
                source_snapshot_id=f"daily-{cutoff.date()}-{symbol}",
            ) for symbol in symbols)

    database = tmp_path / "daily-content.sqlite3"
    value = IntradayMonitor(
        feed=SameContentFeed(), calendar=TwoDayCalendar(),
        state_repository=PollStateRepository(database), focus_symbols=lambda now: (),
        universe_symbols=lambda now: ("300001",),
    )
    value.check(NOW, scopes=frozenset({"universe"}))
    value.check(next_day, scopes=frozenset({"universe"}))

    reopened_repository = PollStateRepository(database)
    current_start = datetime(2026, 7, 15, 1, 25, tzinfo=UTC)
    current = reopened_repository.latest_snapshots(next_day, since=current_start)
    restarted = IntradayMonitor(
        feed=SameContentFeed(), calendar=TwoDayCalendar(),
        state_repository=reopened_repository, focus_symbols=lambda now: (),
        universe_symbols=lambda now: ("300001",),
    )
    assert len(reopened_repository.snapshots()) == 2
    assert len(current) == 1 and current[0].observed_at == next_day
    assert len(reopened_repository.success_states("universe")) == 2
    assert restarted.due(next_day + timedelta(seconds=179)) == frozenset({"focus"})


def test_constrained_budget_persists_300_second_universe_cadence(tmp_path) -> None:
    value = IntradayMonitor(
        feed=Feed(), calendar=Calendar(),
        state_repository=PollStateRepository(tmp_path / "budget.sqlite3"),
        focus_symbols=lambda now: (), universe_symbols=lambda now: ("300001",),
        source_budget=lambda now: "constrained",
    )
    value.check(NOW, scopes=frozenset({"universe"}))
    assert value.state.universe_interval_seconds == 300
    assert value.state.next_universe_due_at == NOW + timedelta(seconds=300)


def test_stream_selected_by_capability_does_not_poll(tmp_path) -> None:
    class StreamFeed:
        capabilities = frozenset({"subscribe"})

        def snapshot_many(self, symbols, *, cutoff=None):
            raise AssertionError("stream mode must not poll")

    value = IntradayMonitor(
        feed=StreamFeed(), calendar=Calendar(),
        state_repository=PollStateRepository(tmp_path / "stream.sqlite3"),
        focus_symbols=lambda now: ("000001",), universe_symbols=lambda now: ("300001",),
        delivery_mode="stream",
    )
    assert value.due(NOW) == frozenset()
    assert value.check(NOW).polled == frozenset()


class Evaluation:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def evaluate(self, context):
        self.calls.append(context)
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


class AI:
    def __init__(self, *, ready=True) -> None:
        self.ready = ready
        self.requests = []

    def explain(self, request):
        self.requests.append(request)
        return DecisionAIResult(
            status="ready" if self.ready else "unavailable",
            explanation="模型只解释冻结的盘中变化。" if self.ready else None,
            statements=(), provider="openai-compatible", model="model-one",
            prompt_version="decision-v1", generated_at=request.generated_at,
            evidence_ids=tuple(item.evidence_id for item in request.evidence),
            invalid_output_count=0, provider_error_count=0 if self.ready else 1,
        )


class InputPort:
    def __init__(self, value=None):
        self.value = value if value is not None else {"state": "ready"}

    def snapshot(self, *, now, cutoff):
        return self.value


class QuoteFeed:
    capabilities = frozenset({"snapshot", "snapshot_many"})

    def snapshot_many(self, symbols, *, cutoff=None):
        return tuple(MarketFeedSnapshot(
            symbol=symbol, price=Decimal("10"), change=Decimal("0"),
            change_percent=Decimal("0"), volume=Decimal("100"), source="test",
            observed_at=cutoff, fetched_at=cutoff, quality="ready",
            source_snapshot_id=f"quote-{symbol}-{int(cutoff.timestamp())}",
        ) for symbol in symbols)


class LayeredQuoteFeed(QuoteFeed):
    def __init__(self):
        self.price = Decimal("10")

    def snapshot_many(self, symbols, *, cutoff=None):
        values = super().snapshot_many(symbols, cutoff=cutoff)
        return tuple(item.model_copy(update={"price": self.price}) for item in values)


def baseline_aggregate(repository):
    snapshot = DecisionCycleSnapshot(
        snapshot_id="premarket-1", trading_date=date(2026, 7, 14), phase="premarket",
        sequence=1, generated_at=datetime(2026, 7, 14, 1, 20, tzinfo=UTC),
        window_start=datetime(2026, 7, 14, 1, 0, tzinfo=UTC),
        window_end=datetime(2026, 7, 14, 1, 20, tzinfo=UTC), market_state="range",
        data_quality="ready", source_snapshot_ids=("source-1",),
        source_observed_at=(datetime(2026, 7, 14, 1, 20, tzinfo=UTC),),
        candidate_snapshot_id="candidates-1", news_event_ids=(), risk_event_ids=(),
        input_snapshot_hash=hashlib.sha256(b"premarket").hexdigest(),
        previous_snapshot_id=None, status="ready", ai_status="not_requested",
    )
    base = advice(snapshot_id="premarket-1",
                  created_at=datetime(2026, 7, 14, 1, 20, tzinfo=UTC),
                  supporting_evidence=(EvidenceReference(
                      evidence_id="base-e", source="test", snapshot_id="base-s",
                      summary="base", observed_at=datetime(2026, 7, 14, 1, 20, tzinfo=UTC),
                  ),))
    aggregate = DecisionCycleAggregate(snapshot=snapshot, advice=(base,))
    repository.append_cycle(aggregate)
    return aggregate


def decision_monitor(tmp_path, evaluation, repository, *, feed=None, state_database=None,
                     focus_symbols=None, universe_symbols=None, ai=None):
    ai_options = {} if ai is None else {"ai_gateway": ai}
    return IntradayMonitor(
        feed=feed or QuoteFeed(), calendar=Calendar(),
        state_repository=PollStateRepository(
            state_database or tmp_path / "poll-decisions.sqlite3"
        ),
        focus_symbols=focus_symbols or (lambda now: ("000001",)),
        universe_symbols=universe_symbols or (lambda now: ("000001",)),
        decision_repository=repository, evaluator=evaluation,
        candidate_factor_port=InputPort(), risk_port=InputPort(),
        compliance_port=InputPort(), evidence_port=InputPort(),
        **ai_options,
    )


def result_for(proposed=(), *, source="source-v1", gates=None):
    return IntradayEvaluationResult(
        advice=proposed, source_content={"version": source}, gates=gates or {},
        market_state="range", data_quality="ready", status="ready",
        candidate_snapshot_id="candidate-current", news_event_ids=(), risk_event_ids=(),
    )


class EmptyQuoteFeed:
    def snapshot_many(self, symbols, *, cutoff=None):
        return ()


class StaleQuoteFeed(QuoteFeed):
    def snapshot_many(self, symbols, *, cutoff=None):
        return tuple(
            item.model_copy(update={"observed_at": cutoff - timedelta(seconds=181)})
            for item in super().snapshot_many(symbols, cutoff=cutoff)
        )


def deterministic_decision_monitor(
    tmp_path, repository, *, feed, compliance_allowed=True, ai=None,
):
    ai_options = {} if ai is None else {"ai_gateway": ai}
    candidate_input = CandidateInputSnapshot(
        board=CandidateBoard(
            snapshot_id="candidate-current", as_of=date(2026, 7, 14),
            short_term=[], swing=[],
        ),
        captured_at=NOW, history_available=False,
    )
    risk_input = MarketRiskInputSnapshot(
        snapshot_id="risk-current", captured_at=NOW, available=True,
        market_state="range", version="test-v1", summary="ready", risks=(),
    )
    compliance_input = ComplianceInputSnapshot(
        snapshot_id="compliance-current", captured_at=NOW, available=True,
        allowed=compliance_allowed, version="test-v1", risks=(),
    )
    return IntradayMonitor(
        feed=feed, calendar=Calendar(),
        state_repository=PollStateRepository(tmp_path / "poll-blocked.sqlite3"),
        focus_symbols=lambda now: ("000001",),
        universe_symbols=lambda now: ("000001",),
        decision_repository=repository, evaluator=DeterministicIntradayEvaluator(),
        candidate_factor_port=InputPort(candidate_input), risk_port=InputPort(risk_input),
        compliance_port=InputPort(compliance_input), evidence_port=InputPort(()),
        **ai_options,
    )


def assert_single_blocked_cycle(repository):
    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert len(cycles) == 1
    aggregate = cycles[0]
    assert aggregate.snapshot.status == "blocked"
    assert aggregate.snapshot.data_quality == "blocked"
    assert aggregate.snapshot.candidate_snapshot_id == "candidate-current"
    assert aggregate.snapshot.news_event_ids == ()
    assert aggregate.snapshot.risk_event_ids == ()
    assert aggregate.advice == ()
    assert not any(
        item.quantitative_result.get("invalidation_reason_code") == "candidate_removed"
        for item in aggregate.advice
    )
    return aggregate


def test_ready_evaluation_preserves_premarket_evidence_and_appends_live_quote(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-ready-evidence.sqlite3")
    baseline = baseline_aggregate(repository)
    monitor = deterministic_decision_monitor(tmp_path, repository, feed=QuoteFeed())

    result = monitor.check(NOW)

    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert len(cycles) == 1
    aggregate = cycles[0]
    assert result.aggregate == aggregate
    assert aggregate.snapshot.status == "ready"
    assert aggregate.snapshot.data_quality == "ready"
    assert len(aggregate.advice) == 1
    inherited = baseline.advice[0].supporting_evidence[0]
    supporting = aggregate.advice[0].supporting_evidence
    assert supporting[0] == inherited
    assert supporting[1].evidence_id == f"quote-000001-{int(NOW.timestamp())}"
    assert supporting[1].source == "test"
    assert supporting[1].snapshot_id == supporting[1].evidence_id
    assert supporting[1].observed_at == NOW


@pytest.mark.parametrize(
    "old_evidence",
    (
        pytest.param(
            EvidenceReference(
                evidence_id="introduced-old", source="test", snapshot_id="introduced-s",
                summary="new old evidence", observed_at=datetime(2026, 7, 14, 1, 20, tzinfo=UTC),
            ),
            id="new-evidence",
        ),
        pytest.param(
            EvidenceReference(
                evidence_id="base-e", source="test", snapshot_id="base-s",
                summary="tampered base", observed_at=datetime(2026, 7, 14, 1, 20, tzinfo=UTC),
            ),
            id="tampered-inherited-id",
        ),
    ),
)
def test_ready_evaluation_rejects_non_inherited_evidence_before_window(
    tmp_path, old_evidence,
) -> None:
    repository = DecisionRepository(tmp_path / "decisions-old-evidence.sqlite3")
    baseline_aggregate(repository)
    proposed = advice(
        "proposal", conclusion="changed", created_at=NOW,
        supporting_evidence=(old_evidence,),
    )
    monitor = decision_monitor(
        tmp_path, Evaluation([result_for((proposed,), source="old-evidence")]), repository,
    )

    with pytest.raises(ValueError, match="evidence predates the advice baseline"):
        monitor.check(NOW)


def test_no_quotes_persist_blocked_cycle_idempotently_without_candidate_removal(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-no-quotes.sqlite3")
    baseline_aggregate(repository)
    monitor = deterministic_decision_monitor(tmp_path, repository, feed=EmptyQuoteFeed())

    first = monitor.check(NOW)
    second = monitor.check(NOW + timedelta(seconds=180))

    aggregate = assert_single_blocked_cycle(repository)
    assert first.aggregate == aggregate
    assert second.aggregate == aggregate
    assert aggregate.snapshot.market_state == "insufficient_data"
    assert aggregate.snapshot.source_snapshot_ids == ()
    assert aggregate.snapshot.source_observed_at == ()
    assert aggregate.snapshot.quality_reasons == ("live_quotes_unavailable",)


def test_stale_quote_persists_blocked_cycle_without_candidate_removal(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-stale-quote.sqlite3")
    baseline_aggregate(repository)
    monitor = deterministic_decision_monitor(tmp_path, repository, feed=StaleQuoteFeed())

    result = monitor.check(NOW)

    aggregate = assert_single_blocked_cycle(repository)
    assert result.aggregate == aggregate
    assert aggregate.snapshot.market_state == "range"
    assert aggregate.snapshot.source_snapshot_ids == (
        f"quote-000001-{int(NOW.timestamp())}",
    )
    assert aggregate.snapshot.source_observed_at == (NOW - timedelta(seconds=181),)


def test_denied_compliance_persists_blocked_cycle_without_candidate_removal(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-compliance-denied.sqlite3")
    baseline_aggregate(repository)
    monitor = deterministic_decision_monitor(
        tmp_path, repository, feed=QuoteFeed(), compliance_allowed=False,
    )

    result = monitor.check(NOW)

    aggregate = assert_single_blocked_cycle(repository)
    assert result.aggregate == aggregate
    assert aggregate.snapshot.market_state == "range"
    assert aggregate.snapshot.source_snapshot_ids == (
        f"quote-000001-{int(NOW.timestamp())}",
    )
    assert aggregate.snapshot.source_observed_at == (NOW,)


def test_partial_evaluation_does_not_invalidate_removed_candidate(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-partial.sqlite3")
    baseline = baseline_aggregate(repository)
    partial = result_for((), source="partial").model_copy(update={
        "data_quality": "partial", "status": "partial",
    })
    monitor = decision_monitor(tmp_path, Evaluation([partial]), repository)

    result = monitor.check(NOW)

    assert result.aggregate == baseline
    assert repository.cycles(date(2026, 7, 14), "intraday") == []


def test_blocked_evaluator_advice_is_discarded_defensively(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-blocked-advice.sqlite3")
    baseline_aggregate(repository)
    blocked = result_for((
        advice("blocked-proposal", conclusion="must not leak", created_at=NOW),
    ), source="blocked-contract").model_copy(update={
        "data_quality": "blocked", "status": "blocked",
    })
    monitor = decision_monitor(tmp_path, Evaluation([blocked]), repository)

    result = monitor.check(NOW)

    aggregate = assert_single_blocked_cycle(repository)
    assert result.aggregate == aggregate


def test_ready_state_after_blocked_cycle_is_persisted_without_advice_change(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-blocked-recovery.sqlite3")
    baseline_aggregate(repository)
    blocked = result_for((), source="same-state").model_copy(update={
        "data_quality": "blocked", "status": "blocked",
    })
    ready = result_for((advice("ready-proposal", created_at=NOW),), source="same-state")
    ai = AI()
    monitor = decision_monitor(
        tmp_path, Evaluation([blocked, ready]), repository, ai=ai,
    )

    first = monitor.check(NOW)
    second = monitor.check(NOW + timedelta(seconds=60))

    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert first.aggregate == cycles[0]
    assert cycles[0].snapshot.status == "blocked"
    assert second.aggregate == cycles[1]
    assert cycles[1].snapshot.status == "ready"
    assert cycles[1].snapshot.data_quality == "ready"
    assert cycles[1].advice == ()
    assert cycles[1].snapshot.ai_status == "not_requested"
    assert ai.requests == []


def test_source_hash_distinguishes_ready_partial_and_blocked_states() -> None:
    quote = QuoteFeed().snapshot_many(("000001",), cutoff=NOW)
    ready = result_for((), source="same")
    partial = ready.model_copy(update={"data_quality": "partial", "status": "partial"})
    blocked_quote = ready.model_copy(update={
        "data_quality": "blocked", "status": "blocked",
        "quality_reasons": ("live_quotes_unavailable",),
    })
    blocked_risk = blocked_quote.model_copy(update={
        "quality_reasons": ("risk_unavailable",),
    })

    hashes = {
        IntradayMonitor._source_hash(result, quote)
        for result in (ready, partial, blocked_quote, blocked_risk)
    }

    assert len(hashes) == 4


def test_check_appends_changed_aggregate_then_unchanged_check_is_idempotent(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions.sqlite3")
    baseline_aggregate(repository)
    proposed = advice("proposal", conclusion="changed", created_at=NOW)
    evaluation = Evaluation([result_for((proposed,)), result_for((proposed,))])
    monitor = decision_monitor(tmp_path, evaluation, repository)
    first = monitor.check(NOW)
    second = monitor.check(NOW + timedelta(seconds=180))
    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert first.aggregate == cycles[0]
    assert second.aggregate == cycles[0]
    assert len(cycles) == 1
    assert cycles[0].advice[0].previous_advice_id == "a1"
    assert cycles[0].advice[0].changed_fields == ("conclusion",)


def test_ready_ai_appends_one_explanation_without_changing_frozen_intraday_fields(
    tmp_path,
) -> None:
    repository = DecisionRepository(tmp_path / "decisions-ai-ready.sqlite3")
    baseline_aggregate(repository)
    ai = AI()
    proposed = advice(
        "proposal-ai-ready",
        action="wait",
        conclusion="盘中确定性结论",
        confidence=Decimal("0.42"),
        plain_language_explanation="盘中确定性解释。",
        ai_interpretation_id="premarket-ai-old",
        quantitative_result={
            "membership": "short_term",
            "ai_provider": "old-provider",
            "kept": "value",
        },
        created_at=NOW,
    )
    second_proposed = advice(
        "proposal-ai-ready-second",
        symbol="300001",
        conclusion="第二只股票的确定性结论",
        plain_language_explanation="第二条确定性解释。",
        created_at=NOW,
    )
    monitor = decision_monitor(
        tmp_path,
        Evaluation([result_for((proposed, second_proposed))]),
        repository,
        ai=ai,
    )

    result = monitor.check(NOW)
    stored = next(item for item in result.aggregate.advice if item.symbol == "000001")

    assert result.aggregate.snapshot.ai_status == "ready"
    assert result.aggregate.snapshot.status == "ready"
    assert result.aggregate.snapshot.data_quality == "ready"
    assert stored.action == "wait"
    assert stored.conclusion == "盘中确定性结论"
    assert stored.confidence == Decimal("0.42")
    assert stored.risks == proposed.risks
    assert stored.supporting_evidence == proposed.supporting_evidence
    assert stored.plain_language_explanation == (
        "盘中确定性解释。模型补充：模型只解释冻结的盘中变化。"
    )
    assert stored.ai_interpretation_id is not None
    assert stored.ai_interpretation_id != "premarket-ai-old"
    assert stored.quantitative_result["ai_provider"] == "openai-compatible"
    assert stored.quantitative_result["kept"] == "value"
    assert len(result.aggregate.advice) == 2
    assert all(item.ai_interpretation_id for item in result.aggregate.advice)
    assert len(ai.requests) == 1
    assert ai.requests[0].generated_at == NOW
    assert tuple(item.evidence_id for item in ai.requests[0].evidence) == ("e1",)


def test_unavailable_ai_keeps_ready_intraday_decision_and_deterministic_text(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-ai-unavailable.sqlite3")
    baseline_aggregate(repository)
    ai = AI(ready=False)
    proposed = advice(
        "proposal-ai-unavailable", conclusion="changed",
        plain_language_explanation="确定性解释。", created_at=NOW,
    )
    monitor = decision_monitor(
        tmp_path, Evaluation([result_for((proposed,))]), repository, ai=ai,
    )

    result = monitor.check(NOW)
    stored = result.aggregate.advice[0]

    assert result.aggregate.snapshot.ai_status == "unavailable"
    assert result.aggregate.snapshot.status == "ready"
    assert result.aggregate.snapshot.data_quality == "ready"
    assert stored.plain_language_explanation == "确定性解释。"
    assert stored.ai_interpretation_id is None
    assert stored.quantitative_result["ai_provider_error_count"] == "1"


def test_unchanged_intraday_poll_does_not_call_ai_again(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-ai-idempotent.sqlite3")
    baseline_aggregate(repository)
    ai = AI()
    proposed = advice(
        "proposal-ai-idempotent", conclusion="changed",
        plain_language_explanation="确定性解释。", created_at=NOW,
    )
    monitor = decision_monitor(
        tmp_path,
        Evaluation([result_for((proposed,)), result_for((proposed,))]),
        repository,
        ai=ai,
    )

    first = monitor.check(NOW)
    second = monitor.check(NOW + timedelta(seconds=180))

    assert second.aggregate.snapshot.snapshot_id == first.aggregate.snapshot.snapshot_id
    assert len(repository.cycles(date(2026, 7, 14), "intraday")) == 1
    assert len(ai.requests) == 1


def test_blocked_intraday_snapshot_does_not_call_ai(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions-ai-blocked.sqlite3")
    baseline_aggregate(repository)
    ai = AI()
    monitor = deterministic_decision_monitor(
        tmp_path, repository, feed=EmptyQuoteFeed(), ai=ai,
    )

    result = monitor.check(NOW)

    assert result.aggregate.snapshot.ai_status == "not_requested"
    assert result.aggregate.snapshot.status == "blocked"
    assert ai.requests == []


def test_changed_evaluator_output_with_same_source_content_appends(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions.sqlite3")
    baseline_aggregate(repository)
    evaluation = Evaluation([
        result_for((advice("p1", conclusion="first", created_at=NOW),)),
        result_for((advice("p2", conclusion="second", created_at=NOW),)),
    ])
    monitor = decision_monitor(tmp_path, evaluation, repository)
    monitor.check(NOW)
    monitor.check(NOW + timedelta(seconds=180))
    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert len(cycles) == 2
    assert cycles[1].advice[0].previous_advice_id == cycles[0].advice[0].advice_id
    assert cycles[1].advice[0].changed_fields == ("conclusion",)


def test_quote_and_source_change_without_semantic_delta_does_not_append(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions.sqlite3")
    baseline_aggregate(repository)
    proposed = advice("proposal", conclusion="changed", created_at=NOW)
    evaluation = Evaluation([
        result_for((proposed,), source="source-v1"),
        result_for((proposed,), source="source-v2"),
    ])
    feed = LayeredQuoteFeed()
    monitor = decision_monitor(tmp_path, evaluation, repository, feed=feed)
    monitor.check(NOW)
    feed.price = Decimal("10.01")
    second = monitor.check(NOW + timedelta(seconds=180))
    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert len(cycles) == 1
    assert second.aggregate == cycles[0]


def test_removed_candidate_invalidates_once(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions.sqlite3")
    baseline_aggregate(repository)
    evaluation = Evaluation([result_for((), source="removed"), result_for((), source="removed")])
    monitor = decision_monitor(tmp_path, evaluation, repository)
    monitor.check(NOW)
    monitor.check(NOW + timedelta(seconds=180))
    cycles = repository.cycles(date(2026, 7, 14), "intraday")
    assert len(cycles) == 1
    assert cycles[0].advice[0].action == "invalidated"
    assert cycles[0].advice[0].quantitative_result["invalidation_reason_code"] == "candidate_removed"


def test_layered_quotes_retain_universe_and_update_focus_across_restart(tmp_path) -> None:
    repository = DecisionRepository(tmp_path / "decisions.sqlite3")
    evaluation = Evaluation([result_for(())])
    feed = LayeredQuoteFeed()
    database = tmp_path / "layered.sqlite3"
    monitor = decision_monitor(
        tmp_path, evaluation, repository, feed=feed, state_database=database,
        focus_symbols=lambda now: ("000001",),
        universe_symbols=lambda now: ("000001", "300001"),
    )
    monitor.check(NOW, scopes=frozenset({"universe"}))
    feed.price = Decimal("10.20")
    restarted = decision_monitor(
        tmp_path, evaluation, repository, feed=feed, state_database=database,
        focus_symbols=lambda now: ("000001",),
        universe_symbols=lambda now: ("000001", "300001"),
    )
    restarted.check(NOW + timedelta(seconds=60), scopes=frozenset({"focus"}))
    quotes = {item.symbol: item for item in evaluation.calls[-1].quotes}
    assert set(quotes) == {"000001", "300001"}
    assert quotes["000001"].price == Decimal("10.20")
    assert quotes["300001"].price == Decimal("10")
