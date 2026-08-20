from datetime import date
from decimal import Decimal
import threading
import time

from qibao_api.gongbu.sina_financials import (
    SinaFinancialHistorySource,
    merge_financial_reports,
    parse_sina_report,
)


def payload(periods: dict[str, list[dict]]) -> dict:
    return {
        "result": {
            "data": {
                "report_list": {
                    period: {"data": items}
                    for period, items in periods.items()
                }
            }
        }
    }


def item(title: str, value: str, yoy: str | None = None) -> dict:
    result = {"item_title": title, "item_value": value}
    if yoy is not None:
        result["item_tongbi"] = yoy
    return result


def test_parse_sina_report_maps_known_income_aliases_and_keeps_unknown_out() -> None:
    rows = parse_sina_report(
        payload({
            "20251231": [
                item("营业总收入", "1000000000", "12.5"),
                item("营业成本", "600000000"),
                item("归属于母公司股东的净利润", "180000000", "9.2"),
                item("无法识别的自定义科目", "999"),
            ]
        }),
        report_type="lrb",
        limit=8,
    )

    assert len(rows) == 1
    assert rows[0].period == date(2025, 12, 31)
    assert rows[0].revenue == Decimal("1000000000")
    assert rows[0].revenue_yoy == Decimal("12.5")
    assert rows[0].operating_cost == Decimal("600000000")
    assert rows[0].net_profit == Decimal("180000000")
    assert rows[0].net_profit_yoy == Decimal("9.2")
    assert rows[0].operating_cash_flow is None


def test_parse_sina_report_rejects_invalid_numbers_without_guessing() -> None:
    rows = parse_sina_report(
        payload({"20250930": [item("营业收入", "--"), item("净利润", "not-a-number")]}),
        report_type="lrb",
        limit=8,
    )

    assert rows[0].revenue is None
    assert rows[0].net_profit is None


def test_merge_financial_reports_calculates_ratios_and_annual_series() -> None:
    income = parse_sina_report(
        payload({
            "20251231": [item("营业收入", "1200"), item("营业成本", "720"), item("净利润", "240")],
            "20241231": [item("营业收入", "1000"), item("营业成本", "650"), item("净利润", "200")],
            "20231231": [item("营业收入", "800"), item("营业成本", "560"), item("净利润", "160")],
            "20250930": [item("营业收入", "900", "10"), item("净利润", "150", "5")],
        }),
        report_type="lrb",
        limit=8,
    )
    balance = parse_sina_report(
        payload({
            "20251231": [item("资产总计", "2000"), item("负债合计", "800"), item("所有者权益合计", "1200")],
            "20241231": [item("资产总计", "1800"), item("负债合计", "810"), item("所有者权益合计", "990")],
            "20231231": [item("资产总计", "1600"), item("负债合计", "800"), item("所有者权益合计", "800")],
        }),
        report_type="fzb",
        limit=8,
    )
    cashflow = parse_sina_report(
        payload({
            "20251231": [item("经营活动产生的现金流量净额", "300")],
            "20241231": [item("经营活动产生的现金流量净额", "180")],
            "20231231": [item("经营活动产生的现金流量净额", "120")],
        }),
        report_type="llb",
        limit=8,
    )

    history = merge_financial_reports(income, balance, cashflow)

    assert [row.period for row in history.annual_periods] == [
        date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31)
    ]
    latest_annual = history.annual_periods[-1]
    assert latest_annual.gross_margin == Decimal("0.4")
    assert latest_annual.cash_to_profit == Decimal("1.25")
    assert latest_annual.debt_ratio == Decimal("0.4")
    assert history.revenue_cagr_3y == Decimal("0.224744871391589049098642037")
    assert history.net_profit_cagr_3y == Decimal("0.224744871391589049098642037")
    assert history.latest_period.period == date(2025, 12, 31)


def test_sina_financial_history_fetches_three_reports_concurrently() -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return payload({"20251231": []})

    class Client:
        def __init__(self) -> None:
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def get(self, *_args, **_kwargs) -> Response:
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.05)
            with self.lock:
                self.active -= 1
            return Response()

    client = Client()
    result = SinaFinancialHistorySource(client=client).fetch("600519")

    assert result.periods
    assert client.max_active == 3
