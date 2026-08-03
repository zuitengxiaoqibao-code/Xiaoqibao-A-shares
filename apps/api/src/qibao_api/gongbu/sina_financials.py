from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from qibao_api.contracts.company_research import FinancialHistory, FinancialPeriod


class SinaReportRow:
    def __init__(
        self,
        *,
        period: date,
        revenue: Decimal | None = None,
        revenue_yoy: Decimal | None = None,
        operating_cost: Decimal | None = None,
        net_profit: Decimal | None = None,
        net_profit_yoy: Decimal | None = None,
        operating_cash_flow: Decimal | None = None,
        total_assets: Decimal | None = None,
        total_liabilities: Decimal | None = None,
        total_equity: Decimal | None = None,
    ) -> None:
        self.period = period
        self.revenue = revenue
        self.revenue_yoy = revenue_yoy
        self.operating_cost = operating_cost
        self.net_profit = net_profit
        self.net_profit_yoy = net_profit_yoy
        self.operating_cash_flow = operating_cash_flow
        self.total_assets = total_assets
        self.total_liabilities = total_liabilities
        self.total_equity = total_equity


_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("营业收入", "营业总收入", "主营业务收入"),
    "operating_cost": ("营业成本", "主营业务成本"),
    "net_profit": (
        "归属于母公司股东的净利润",
        "归属于上市公司股东的净利润",
        "净利润",
    ),
    "operating_cash_flow": (
        "经营活动产生的现金流量净额",
        "经营活动现金流量净额",
    ),
    "total_assets": ("资产总计", "资产合计"),
    "total_liabilities": ("负债合计", "负债总计"),
    "total_equity": (
        "归属于母公司股东权益合计",
        "归属于母公司所有者权益合计",
        "所有者权益合计",
    ),
}


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _period(value: Any) -> date | None:
    text = str(value or "").strip()
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def _report_list(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    result = payload.get("result")
    if not isinstance(result, Mapping):
        return {}
    data = result.get("data")
    if not isinstance(data, Mapping):
        return {}
    reports = data.get("report_list")
    return reports if isinstance(reports, Mapping) else {}


def parse_sina_report(
    payload: Mapping[str, Any], *, report_type: str, limit: int = 8
) -> tuple[SinaReportRow, ...]:
    rows: list[SinaReportRow] = []
    for raw_period in sorted(_report_list(payload), reverse=True)[:limit]:
        period = _period(raw_period)
        if period is None:
            continue
        container = _report_list(payload).get(raw_period)
        items = container.get("data", []) if isinstance(container, Mapping) else []
        values: dict[str, Decimal | None] = {}
        yoy: dict[str, Decimal | None] = {}
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("item_title") or "").strip()
            for field, aliases in _ALIASES.items():
                if title in aliases:
                    values[field] = _decimal(item.get("item_value"))
                    yoy[field] = _decimal(item.get("item_tongbi"))
        rows.append(SinaReportRow(
            period=period,
            revenue=values.get("revenue"),
            revenue_yoy=yoy.get("revenue"),
            operating_cost=values.get("operating_cost"),
            net_profit=values.get("net_profit"),
            net_profit_yoy=yoy.get("net_profit"),
            operating_cash_flow=values.get("operating_cash_flow"),
            total_assets=values.get("total_assets"),
            total_liabilities=values.get("total_liabilities"),
            total_equity=values.get("total_equity"),
        ))
    return tuple(rows)


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, Decimal("0")):
        return None
    return numerator / denominator


def _cagr(first: Decimal | None, last: Decimal | None, intervals: int) -> Decimal | None:
    if first is None or last is None or first <= 0 or last <= 0 or intervals <= 0:
        return None
    return (last / first) ** (Decimal("1") / Decimal(intervals)) - Decimal("1")


def _period_model(row: SinaReportRow) -> FinancialPeriod:
    revenue = row.revenue
    return FinancialPeriod(
        period=row.period,
        revenue=revenue,
        revenue_yoy=row.revenue_yoy,
        operating_cost=row.operating_cost,
        net_profit=row.net_profit,
        net_profit_yoy=row.net_profit_yoy,
        operating_cash_flow=row.operating_cash_flow,
        total_assets=row.total_assets,
        total_liabilities=row.total_liabilities,
        total_equity=row.total_equity,
        gross_margin=(
            (revenue - row.operating_cost) / revenue
            if revenue not in (None, Decimal("0")) and row.operating_cost is not None
            else None
        ),
        cash_to_profit=_ratio(row.operating_cash_flow, row.net_profit),
        debt_ratio=_ratio(row.total_liabilities, row.total_assets),
    )


def merge_financial_reports(
    income: tuple[SinaReportRow, ...],
    balance: tuple[SinaReportRow, ...],
    cashflow: tuple[SinaReportRow, ...],
    *,
    observed_at: datetime | None = None,
    source: str = "sina-finance",
) -> FinancialHistory:
    by_period: dict[date, SinaReportRow] = {}
    for rows in (income, balance, cashflow):
        for row in rows:
            current = by_period.setdefault(row.period, SinaReportRow(period=row.period))
            for field in (
                "revenue", "revenue_yoy", "operating_cost", "net_profit",
                "net_profit_yoy", "operating_cash_flow", "total_assets",
                "total_liabilities", "total_equity",
            ):
                value = getattr(row, field)
                if value is not None:
                    setattr(current, field, value)
    periods = tuple(_period_model(by_period[key]) for key in sorted(by_period))
    annual = tuple(item for item in periods if item.period.month == 12 and item.period.day == 31)
    annual = annual[-5:]
    latest = periods[-1] if periods else None
    reasons: list[str] = []
    if not periods:
        reasons.append("新浪财报接口未返回可识别报告期")
    if len(annual) < 3:
        reasons.append("可识别年度报告期少于3年")
    status = "ready" if periods and not reasons else "partial" if periods else "unavailable"
    return FinancialHistory(
        status=status,
        periods=periods,
        annual_periods=annual,
        latest_period=latest,
        revenue_cagr_3y=(
            _cagr(annual[0].revenue, annual[-1].revenue, len(annual) - 1)
            if len(annual) >= 3 else None
        ),
        net_profit_cagr_3y=(
            _cagr(annual[0].net_profit, annual[-1].net_profit, len(annual) - 1)
            if len(annual) >= 3 else None
        ),
        source=source,
        observed_at=observed_at or datetime.now(timezone.utc),
        reasons=tuple(reasons),
    )


class SinaFinancialHistorySource:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        client_factory: Callable[[], httpx.Client] | None = None,
        timeout: float = 15,
    ) -> None:
        self._client = client
        self._client_factory = client_factory or (lambda: httpx.Client(timeout=timeout))
        self._timeout = timeout
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def fetch(self, symbol: str, limit: int = 20) -> FinancialHistory:
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        client = self._client or self._client_factory()
        rows: list[tuple[str, tuple[SinaReportRow, ...]]] = []
        try:
            for report_type in ("lrb", "fzb", "llb"):
                response = client.get(
                    "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022",
                    params={
                        "paperCode": f"{prefix}{symbol}",
                        "source": report_type,
                        "type": "0",
                        "page": "1",
                        "num": str(limit),
                    },
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=self._timeout,
                )
                response.raise_for_status()
                rows.append((report_type, parse_sina_report(response.json(), report_type=report_type, limit=limit)))
        finally:
            if self._owns_client and client is not self._client:
                client.close()
        by_type = {kind: values for kind, values in rows}
        return merge_financial_reports(
            by_type.get("lrb", ()), by_type.get("fzb", ()), by_type.get("llb", ()),
        )
