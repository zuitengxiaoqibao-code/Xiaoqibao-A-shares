from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qibao_api.a_shares.late_session_evaluation import evaluate_next_session


def test_next_session_evaluation_uses_real_later_bars() -> None:
    snapshot = {
        "snapshot_id": "late-1",
        "trading_date": "2026-08-18",
        "regime": "轮动震荡",
        "candidate": {"quote": {"symbol": "600000", "price": "10.00"}},
    }
    bars = (
        SimpleNamespace(trade_date=date(2026, 8, 19), open=Decimal("10.10"), high=Decimal("10.50"), low=Decimal("9.80"), close=Decimal("9.90")),
        SimpleNamespace(trade_date=date(2026, 8, 19), open=Decimal("9.90"), high=Decimal("10.20"), low=Decimal("9.70"), close=Decimal("9.80")),
    )

    result = evaluate_next_session(snapshot, bars)

    assert result.open_return_percent == Decimal("1.00")
    assert result.high_return_percent == Decimal("5.00")
    assert result.max_drawdown_percent == Decimal("-3.00")
    assert result.false_breakout is True
    assert result.regime == "轮动震荡"


def test_next_session_evaluation_rejects_same_day_or_missing_bars() -> None:
    snapshot = {
        "snapshot_id": "late-1",
        "trading_date": "2026-08-18",
        "candidate": {"quote": {"symbol": "600000", "price": "10.00"}},
    }
    same_day = (SimpleNamespace(trade_date=date(2026, 8, 18), open=Decimal("10"), high=Decimal("10"), low=Decimal("10"), close=Decimal("10")),)

    with pytest.raises(ValueError, match="next trading session"):
        evaluate_next_session(snapshot, same_day)
