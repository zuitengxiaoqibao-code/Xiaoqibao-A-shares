from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.gongbu.tdx_client import create_tdx_client
from qibao_api.contracts.industry import ShenwanIndustry
from qibao_api.gongbu.shenwan_industry import resolve_shenwan_industry


class FundamentalSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    observed_at: datetime
    report_period: date | None = None
    data_updated_on: date | None = None
    industry: str | None = None
    shenwan_industry: ShenwanIndustry | None = None
    shenwan_mapping_status: str = "unmapped"
    eps: Decimal | None = None
    roe: Decimal | None = None
    net_profit: Decimal | None = None
    revenue: Decimal | None = None
    book_value_per_share: Decimal | None = None
    total_shares: Decimal | None = Field(default=None, ge=0)
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None
    market_cap_yi: Decimal | None = Field(default=None, ge=0)
    source: str


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "" or value == "--":
        return None
    if isinstance(value, float) and not isfinite(value):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _date_or_none(value: Any) -> date | None:
    text = str(value or "").strip()
    if len(text) != 8 or not text.isdigit() or text == "00000000":
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError:
        return None


def _industry_name_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if text and not text.isdigit() else None


def _tdx_money_scale(payload: Mapping[str, Any]) -> Decimal | None:
    net_assets = _decimal_or_none(payload.get("jingzichan"))
    total_shares = _decimal_or_none(payload.get("zongguben"))
    book_value_per_share = _decimal_or_none(payload.get("meigujingzichan"))
    if (
        net_assets is None or total_shares is None or book_value_per_share is None
        or total_shares <= 0 or book_value_per_share <= 0
    ):
        return None
    ratio = net_assets / total_shares / book_value_per_share
    for decoded_ratio, scale in (
        (Decimal("10"), Decimal("0.1")),
        (Decimal("1"), Decimal("1")),
    ):
        if abs(ratio - decoded_ratio) <= decoded_ratio * Decimal("0.15"):
            return scale
    return None


def parse_tdx_finance(
    payload: Mapping[str, Any],
    symbol: str,
    observed_at: datetime,
) -> FundamentalSnapshot:
    money_scale = _tdx_money_scale(payload)
    net_profit_raw = _decimal_or_none(payload.get("jinglirun"))
    revenue_raw = _decimal_or_none(payload.get("zhuyingshouru"))
    net_assets_raw = _decimal_or_none(payload.get("jingzichan"))
    net_profit = (
        net_profit_raw * money_scale
        if net_profit_raw is not None and money_scale is not None else None
    )
    revenue = (
        revenue_raw * money_scale
        if revenue_raw is not None and money_scale is not None else None
    )
    net_assets = (
        net_assets_raw * money_scale
        if net_assets_raw is not None and money_scale is not None else None
    )
    total_shares = _decimal_or_none(payload.get("zongguben"))
    eps = (
        net_profit / total_shares
        if net_profit is not None and total_shares is not None and total_shares > 0
        else None
    )
    roe = (
        net_profit / net_assets * Decimal("100")
        if net_profit is not None and net_assets is not None and net_assets > 0
        else None
    )
    assignment = resolve_shenwan_industry(payload.get("industry"), "mootdx-finance", observed_at=observed_at)
    return FundamentalSnapshot(
        symbol=symbol,
        observed_at=observed_at,
        report_period=None,
        data_updated_on=_date_or_none(payload.get("updated_date")),
        industry=_industry_name_or_none(payload.get("industry")),
        shenwan_industry=assignment.industry,
        shenwan_mapping_status="verified" if assignment.is_verified else "unmapped",
        eps=eps,
        roe=roe,
        net_profit=net_profit,
        revenue=revenue,
        book_value_per_share=_decimal_or_none(payload.get("meigujingzichan")),
        total_shares=total_shares,
        source="mootdx-finance",
    )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "empty") and value.empty:
        return {}
    if hasattr(value, "iloc"):
        row = value.iloc[0]
        if hasattr(row, "to_dict"):
            return row.to_dict()
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return result
    raise ValueError("unsupported mootdx finance response")


def _unwrap_tdx_rpc(value: Any) -> Mapping[str, Any]:
    """Return one row from a TdxQuant response without inventing fields."""
    if isinstance(value, Mapping):
        nested = value.get("Value")
        if isinstance(nested, list):
            for row in nested:
                if isinstance(row, Mapping):
                    return row
        if isinstance(nested, Mapping):
            return nested
        return value
    if isinstance(value, list):
        return next((row for row in value if isinstance(row, Mapping)), {})
    return {}


def _lookup(mapping: Mapping[str, Any], *keys: str) -> Any:
    normalized = {str(key).casefold().replace("_", ""): value for key, value in mapping.items()}
    for key in keys:
        value = normalized.get(key.casefold().replace("_", ""))
        if value not in (None, "", "--"):
            return value
    return None


def parse_tdx_rpc_security(
    *,
    more_info: Any,
    stock_info: Any,
    symbol: str,
    observed_at: datetime,
) -> FundamentalSnapshot:
    """Parse optional local TdxQuant detail responses into the shared finance contract."""
    more = _unwrap_tdx_rpc(more_info)
    info = _unwrap_tdx_rpc(stock_info)
    merged = {**info, **more}
    industry = _industry_name_or_none(_lookup(info, "industry", "industry_name", "行业", "所属行业"))
    values = {
        "pe_ttm": _decimal_or_none(_lookup(merged, "pe_ttm", "pe", "市盈率", "pettm")),
        "pb": _decimal_or_none(_lookup(merged, "pb", "市净率")),
        "market_cap_yi": _decimal_or_none(_lookup(merged, "market_cap_yi", "market_cap", "总市值", "zongshizhi")),
        "eps": _decimal_or_none(_lookup(merged, "eps", "每股收益")),
        "roe": _decimal_or_none(_lookup(merged, "roe", "净资产收益率")),
        "revenue": _decimal_or_none(_lookup(merged, "revenue", "营业收入", "zhuyingshouru")),
        "net_profit": _decimal_or_none(_lookup(merged, "net_profit", "净利润", "jinglirun")),
        "book_value_per_share": _decimal_or_none(_lookup(merged, "book_value_per_share", "每股净资产", "meigujingzichan")),
        "total_shares": _decimal_or_none(_lookup(merged, "total_shares", "总股本", "zongguben")),
    }
    if not any(value is not None for value in values.values()) and industry is None:
        raise ValueError("tdx rpc detail response has no usable fields")
    assignment = resolve_shenwan_industry(industry, "tdx-local-rpc-detail", observed_at=observed_at)
    return FundamentalSnapshot(
        symbol=symbol,
        observed_at=observed_at,
        industry=industry,
        shenwan_industry=assignment.industry,
        shenwan_mapping_status="verified" if assignment.is_verified else "unmapped",
        source="tdx-local-rpc-detail",
        **values,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TdxFinanceSource:
    def __init__(
        self,
        client_factory: Callable[[], Any] = create_tdx_client,
        clock: Callable[[], datetime] = _utc_now,
        observer: Callable[[SourceAttemptEvent], None] | None = None,
        local_rpc_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.client_factory = client_factory
        self.clock = clock
        self.observer = observer
        self.local_rpc_factory = local_rpc_factory

    def fetch(self, symbol: str) -> FundamentalSnapshot:
        local_snapshot = self._fetch_local_rpc(symbol)
        if local_snapshot is not None:
            return local_snapshot
        client = self.client_factory()
        if self.observer is not None and hasattr(client, "observer"):
            client.observer = self.observer
        try:
            payload = client.finance(symbol=symbol)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        mapping = _as_mapping(payload)
        if not mapping:
            raise ValueError("mootdx finance response is empty")
        snapshot = parse_tdx_finance(mapping, symbol, self.clock())
        usable_fields = (
            snapshot.data_updated_on,
            snapshot.industry,
            snapshot.eps,
            snapshot.roe,
            snapshot.net_profit,
            snapshot.revenue,
            snapshot.book_value_per_share,
            snapshot.total_shares,
        )
        if all(value is None for value in usable_fields):
            raise ValueError("mootdx finance response has no usable fields")
        return snapshot

    def _fetch_local_rpc(self, symbol: str) -> FundamentalSnapshot | None:
        if self.local_rpc_factory is None:
            return None
        rpc = None
        try:
            rpc = self.local_rpc_factory()
            if rpc is None or not getattr(rpc, "available", lambda: False)():
                return None
            exchange = "SH" if symbol.startswith(("5", "6", "9")) else "SZ"
            code = f"{symbol}.{exchange}"
            more_info = rpc.call("get_more_info", {"stock_code": code})
            stock_info = rpc.call("get_stock_info", {"stock_code": code})
            snapshot = parse_tdx_rpc_security(
                more_info=more_info,
                stock_info=stock_info,
                symbol=symbol,
                observed_at=self.clock(),
            )
            if not any(
                getattr(snapshot, field) is not None
                for field in (
                    "pe_ttm", "pb", "market_cap_yi", "eps", "roe", "revenue",
                    "net_profit", "book_value_per_share", "total_shares",
                )
            ):
                return None
            return snapshot
        except Exception:
            # The optional local bridge must never hide the established mootdx fallback.
            return None
        finally:
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
