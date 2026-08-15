from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from qibao_api.contracts.instruments import validate_a_share_code


EXPECTED_BAR_FIELDS = ("open", "high", "low", "close", "volume", "amount")


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def inspect_gaps(
    trading_dates: Sequence[date],
    symbols: Sequence[str],
    bars: Mapping[str, Iterable[Any]],
) -> dict[str, Any]:
    """Inspect explicit trading-date, symbol and OHLCV field coverage."""
    dates = tuple(trading_dates)
    if len(dates) != len(set(dates)):
        raise ValueError("trading_dates must be unique")
    normalized_symbols: list[str] = []
    for symbol in symbols:
        try:
            normalized_symbols.append(validate_a_share_code(symbol))
        except ValueError as error:
            raise ValueError("invalid A-share symbol") from error
    if len(normalized_symbols) != len(set(normalized_symbols)):
        raise ValueError("symbols must be unique")

    missing_dates: dict[str, list[str]] = {}
    missing_symbols: list[str] = []
    field_gaps: dict[str, dict[str, list[str]]] = {}
    source_recommendations: dict[str, str] = {}
    gap_count = 0
    for symbol in normalized_symbols:
        rows = tuple(bars.get(symbol, ()))
        if not rows:
            missing_symbols.append(symbol)
        row_by_date = {
            _field(row, "trade_date"): row
            for row in rows
            if isinstance(_field(row, "trade_date"), date)
        }
        absent = [item.isoformat() for item in dates if item not in row_by_date]
        missing_dates[symbol] = absent
        gap_count += len(absent)
        gaps_for_symbol: dict[str, list[str]] = {}
        for trade_date, row in sorted(row_by_date.items()):
            missing_fields = [
                field for field in EXPECTED_BAR_FIELDS
                if _field(row, field) is None
            ]
            if missing_fields:
                gaps_for_symbol[trade_date.isoformat()] = missing_fields
                gap_count += len(missing_fields)
        if gaps_for_symbol:
            field_gaps[symbol] = gaps_for_symbol
        sources = {str(_field(row, "source") or "") for row in rows}
        source_recommendations[symbol] = (
            "local-tdx"
            if sources & {"local-tdx", "tdx", "mootdx"} or not sources
            else "baidu"
        )

    return {
        "missing_trade_dates": missing_dates,
        "missing_symbols": missing_symbols,
        "field_gaps": field_gaps,
        "source_recommendations": source_recommendations,
        "gap_count": gap_count + len(missing_symbols),
    }
