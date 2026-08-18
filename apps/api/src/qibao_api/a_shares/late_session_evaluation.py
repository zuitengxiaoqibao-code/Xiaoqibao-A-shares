from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class LateSessionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    symbol: str
    trading_date: date
    next_trading_date: date
    regime: str | None = None
    open_return_percent: Decimal
    high_return_percent: Decimal
    close_return_percent: Decimal
    max_drawdown_percent: Decimal
    false_breakout: bool


def evaluate_next_session(snapshot: dict[str, Any], bars: tuple[object, ...]) -> LateSessionOutcome:
    trading_date = date.fromisoformat(str(snapshot["trading_date"]))
    later = [bar for bar in bars if getattr(bar, "trade_date", trading_date) > trading_date]
    if not later:
        raise ValueError("next trading session bars are required")
    next_trading_date = min(bar.trade_date for bar in later)
    session = [bar for bar in later if bar.trade_date == next_trading_date]
    candidate = snapshot["candidate"]
    quote = candidate["quote"]
    reference = Decimal(str(quote["price"]))
    if reference <= 0:
        raise ValueError("candidate reference price must be positive")
    first = session[0]
    open_return = _return_percent(Decimal(str(first.open)), reference)
    high_return = _return_percent(max(Decimal(str(bar.high)) for bar in session), reference)
    close_return = _return_percent(Decimal(str(session[-1].close)), reference)
    max_drawdown = _return_percent(min(Decimal(str(bar.low)) for bar in session), reference)
    return LateSessionOutcome(
        snapshot_id=str(snapshot["snapshot_id"]),
        symbol=str(quote["symbol"]),
        trading_date=trading_date,
        next_trading_date=next_trading_date,
        regime=snapshot.get("regime"),
        open_return_percent=open_return,
        high_return_percent=high_return,
        close_return_percent=close_return,
        max_drawdown_percent=max_drawdown,
        false_breakout=high_return >= Decimal("2") and close_return <= 0,
    )


def _return_percent(value: Decimal, reference: Decimal) -> Decimal:
    return ((value / reference) - Decimal("1")).scaleb(2).quantize(Decimal("0.01"))
