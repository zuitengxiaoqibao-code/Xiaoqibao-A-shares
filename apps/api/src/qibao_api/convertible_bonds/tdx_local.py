import asyncio
import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from qibao_api.contracts.convertible_bond import ClauseDates, ConvertibleBondContract
from qibao_api.contracts.instruments import validate_a_share_code, validate_convertible_bond_code
from qibao_api.convertible_bonds.adapters import ClauseDataUnavailable
from qibao_api.convertible_bonds.models import BondClauseSnapshot, StrongRedemptionEvidence


def _unwrap(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        nested = value.get("Value")
        if isinstance(nested, Mapping):
            return nested
        if isinstance(nested, list):
            return next((row for row in nested if isinstance(row, Mapping)), {})
        return value
    if isinstance(value, list):
        return next((row for row in value if isinstance(row, Mapping)), {})
    return {}


def _lookup(row: Mapping[str, Any], *keys: str) -> Any:
    normalized = {str(key).casefold().replace("_", ""): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.casefold().replace("_", ""))
        if value not in (None, "", "--", "-"):
            return value
    return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _date(value: Any) -> date | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).strip().split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _bond_exchange(code: str) -> str:
    return "SH" if code.startswith("11") else "SZ"


def parse_tdx_kzz_info(
    payload: Any,
    *,
    bond_code: str,
    fetched_at: datetime,
) -> BondClauseSnapshot:
    validate_convertible_bond_code(bond_code)
    row = _unwrap(payload)
    linked_stock = _lookup(
        row, "linked_stock", "linked_stock_code", "underlying_code",
        "convert_stock_code", "CONVERT_STOCK_CODE", "正股代码", "正股代码SH",
    )
    linked_stock = str(linked_stock).split(".", 1)[0] if linked_stock is not None else None
    if linked_stock is not None:
        try:
            linked_stock = validate_a_share_code(linked_stock)
        except ValueError:
            linked_stock = None
    conversion_price = _decimal(_lookup(
        row, "conversion_price", "transfer_value", "转股价", "SWAPPRICE",
    ))
    maturity = _date(_lookup(row, "maturity", "expire_date", "到期日", "HONOUR_DATE"))
    conversion_start = _date(_lookup(
        row, "conversion_start", "transfer_start_date", "转股起始日", "TRANSFER_START_DATE",
    ))
    remaining_size = _decimal(_lookup(
        row, "remaining_size", "bond_balance", "剩余规模", "BOND_BALANCE",
    ))
    if not all((linked_stock, conversion_price, maturity, conversion_start, remaining_size is not None)):
        raise ClauseDataUnavailable("TDX convertible-bond clause fields are incomplete")
    raw_payload = json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence_fields = {
        f"TDX_KZZ_INFO.{key}": str(value)
        for key, value in row.items()
        if any(token in str(key).upper() for token in ("REDEEM", "TRIGGER", "NOTICE", "EXECUTE"))
        and value not in (None, "", "0")
    }
    return BondClauseSnapshot(
        contract=ConvertibleBondContract(
            bond_code=bond_code,
            linked_stock=linked_stock,
            conversion_price=conversion_price,
            maturity=maturity,
            remaining_size=remaining_size,
            clause_dates=ClauseDates(conversion_start=conversion_start),
            as_of=fetched_at,
        ),
        raw_payload=raw_payload,
        content_hash=hashlib.sha256(raw_payload).hexdigest(),
        source="tdx-local-rpc",
        fetched_at=fetched_at,
        parser_version="tdx-local-kzz-v1",
        strong_redemption=StrongRedemptionEvidence(
            state="announced" if evidence_fields else "unknown",
            clause_present=bool(evidence_fields),
            evidence_fields=evidence_fields,
            clause_text=(str(_lookup(row, "redeem_clause", "强赎条款")) if _lookup(row, "redeem_clause", "强赎条款") else None),
        ),
    )


class TdxLocalClauseSource:
    """Read-only TdxQuant convertible-bond clause source."""

    def __init__(self, rpc_factory, *, clock=lambda: datetime.now(timezone.utc)) -> None:
        self.rpc_factory = rpc_factory
        self.clock = clock

    async def fetch(self, bond_code: str) -> BondClauseSnapshot:
        rpc = self.rpc_factory()
        if rpc is None or not getattr(rpc, "available", lambda: False)():
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
            raise ClauseDataUnavailable("TDX local bridge unavailable")
        try:
            payload = await asyncio.to_thread(
                rpc.call,
                "get_kzz_info",
                {"stock_code": f"{bond_code}.{_bond_exchange(bond_code)}"},
            )
            return parse_tdx_kzz_info(payload, bond_code=bond_code, fetched_at=self.clock())
        finally:
            close = getattr(rpc, "close", None)
            if callable(close):
                close()


class FallbackClauseSource:
    def __init__(self, *sources) -> None:
        self.sources = tuple(sources)

    async def fetch(self, bond_code: str) -> BondClauseSnapshot:
        errors: list[Exception] = []
        for source in self.sources:
            try:
                return await source.fetch(bond_code)
            except (ClauseDataUnavailable, OSError, ValueError) as error:
                errors.append(error)
        raise ClauseDataUnavailable("all read-only clause sources unavailable") from (errors[-1] if errors else None)
