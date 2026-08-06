from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


class TdxFormulaDataUnavailable(RuntimeError):
    """Raised when a TDX formula result is empty or not structurally usable."""


@dataclass(frozen=True)
class TdxFormulaPoint:
    symbol: str
    name: str | None
    formula_name: str
    values: dict[str, Decimal]
    fetched_at: datetime
    source: str = "tdx-local-rpc"


def _rows(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, Mapping) or str(payload.get("ErrorId")) != "0":
        return ()
    value = payload.get("Value")
    if isinstance(value, Mapping):
        value = value.get("Data", value.get("Rows", value.get("Value")))
    if isinstance(value, Mapping):
        value = [value]
    if not isinstance(value, list):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _lookup(row: Mapping[str, Any], *names: str) -> Any:
    normalized = {
        str(key).casefold().replace("_", "").replace(" ", ""): value
        for key, value in row.items()
    }
    for name in names:
        value = normalized.get(name.casefold().replace("_", "").replace(" ", ""))
        if value not in (None, "", "--", "-"):
            return value
    return None


def _symbol(value: Any) -> str | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).strip().split(".", 1)[0]
    return text if len(text) == 6 and text.isdigit() else None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def parse_tdx_formula_batch(
    payload: Any,
    *,
    formula_name: str,
    fetched_at: datetime,
) -> tuple[TdxFormulaPoint, ...]:
    rows = _rows(payload)
    if not rows:
        raise TdxFormulaDataUnavailable("TDX formula result is empty")
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    points: list[TdxFormulaPoint] = []
    for row in rows:
        symbol = _symbol(_lookup(row, "Code", "StockCode", "Symbol", "证券代码"))
        if symbol is None:
            continue
        name_value = _lookup(row, "Name", "StockName", "证券简称")
        values: dict[str, Decimal] = {}
        for key, value in row.items():
            key_text = str(key).strip()
            if key_text.casefold() in {
                "code", "stockcode", "symbol", "证券代码", "name", "stockname", "证券简称"
            }:
                continue
            parsed = _decimal(value)
            if parsed is not None:
                values[key_text] = parsed
        points.append(TdxFormulaPoint(
            symbol=symbol,
            name=str(name_value).strip() if name_value is not None else None,
            formula_name=formula_name,
            values=values,
            fetched_at=fetched_at,
        ))
    if not points:
        raise TdxFormulaDataUnavailable("TDX formula result has no valid symbols")
    return tuple(points)


class TdxLocalFormulaSource:
    """Read-only local TdxQuant formula batch source."""

    def __init__(self, rpc_factory, *, clock=lambda: datetime.now(timezone.utc)) -> None:
        self.rpc_factory = rpc_factory
        self.clock = clock

    def fetch(
        self,
        *,
        formula_name: str,
        stock_codes: tuple[str, ...],
    ) -> tuple[TdxFormulaPoint, ...]:
        if not stock_codes:
            raise TdxFormulaDataUnavailable("TDX formula stock list is empty")
        rpc = self.rpc_factory()
        if rpc is None or not getattr(rpc, "available", lambda: False)():
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
            raise TdxFormulaDataUnavailable("TDX local bridge unavailable")
        try:
            payload = rpc.call(
                formula_name,
                {"stock_list": [f"{code}.{'SH' if code.startswith('6') else 'SZ'}" for code in stock_codes]},
            )
            return parse_tdx_formula_batch(
                payload,
                formula_name=formula_name,
                fetched_at=self.clock(),
            )
        finally:
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
