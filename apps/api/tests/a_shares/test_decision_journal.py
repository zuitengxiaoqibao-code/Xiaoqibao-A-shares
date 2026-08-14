from datetime import datetime, timezone
from decimal import Decimal

from qibao_api.a_shares.decision_journal import DecisionJournalStore
from qibao_api.contracts.decision_journal import DecisionJournalCreate


NOW = datetime(2026, 8, 11, 8, 30, tzinfo=timezone.utc)


def test_decision_journal_is_append_only_and_returns_recent_entries(tmp_path) -> None:
    store = DecisionJournalStore(tmp_path / "journal.sqlite3", clock=lambda: NOW)

    first = store.append(DecisionJournalCreate(
        decision_id="shadow-1",
        symbol="600519",
        action="observe",
        recorded_at=NOW,
        note="等待盘中触发，不交易",
    ))
    second = store.append(DecisionJournalCreate(
        symbol="000001",
        action="buy",
        recorded_at=NOW,
        actual_price=Decimal("12.35"),
        quantity=Decimal("100"),
        note="人工记录，不是自动下单",
    ))

    assert first.entry_id != second.entry_id
    assert store.recent(limit=10) == (second, first)
    assert second.actual_price == Decimal("12.35")
    assert second.quantity == Decimal("100")


def test_decision_journal_keeps_snapshot_context_and_queries_same_day(tmp_path) -> None:
    store = DecisionJournalStore(tmp_path / "journal.sqlite3", clock=lambda: NOW)
    entry = store.append(DecisionJournalCreate(
        symbol="600519", action="observe", recorded_at=NOW, note="等待触发",
        market_regime="轮动震荡", screener_session_id="screen-1", snapshot_hash="a" * 64,
        observation_reason="只做前排低吸", risks=("高开超过 4%",),
        invalidation_conditions=("跌破均价且资金转负",),
    ))

    assert store.on_date(NOW.date()) == (entry,)
    assert entry.market_regime == "轮动震荡"
    assert entry.snapshot_hash == "a" * 64
    assert entry.risks == ("高开超过 4%",)
