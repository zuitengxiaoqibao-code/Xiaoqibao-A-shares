from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_tdx_formula_source, get_tdx_ipo_source
from qibao_api.gongbu.tdx_formula import TdxFormulaDataUnavailable, TdxFormulaPoint
from qibao_api.gongbu.tdx_local_calendar import TdxCalendarDataUnavailable, TdxIpoEvent
from qibao_api.routes.tdx_local import router


NOW = datetime(2026, 8, 6, 8, 0, tzinfo=timezone.utc)


class IpoSource:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def fetch(self):
        if self.fail:
            raise TdxCalendarDataUnavailable("secret endpoint detail")
        return (TdxIpoEvent(
            code="732001", name="测试新股", kind="新股",
            subscription_date=date(2026, 8, 7), listing_date=None,
            allotment_date=None, fetched_at=NOW,
        ),)


class FormulaSource:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def fetch(self, *, formula_name, stock_codes):
        self.calls.append((formula_name, stock_codes))
        if self.fail:
            raise TdxFormulaDataUnavailable("secret endpoint detail")
        return (TdxFormulaPoint(
            symbol="600000", name="浦发银行", formula_name=formula_name,
            values={"MACD": Decimal("0.25")}, fetched_at=NOW,
        ),)


def client(ipo_source=None, formula_source=None) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_tdx_ipo_source] = lambda: ipo_source or IpoSource()
    application.dependency_overrides[get_tdx_formula_source] = lambda: formula_source or FormulaSource()
    return TestClient(application)


def test_tdx_local_routes_return_explicit_calendar_and_formula_fields() -> None:
    formula_source = FormulaSource()
    api = client(formula_source=formula_source)

    calendar = api.get("/api/v1/tdx/local/ipo-calendar")
    formula = api.get(
        "/api/v1/tdx/local/formula",
        params=[("formula_name", "formula_process_mul_zb"), ("stock_codes", "600000")],
    )

    assert calendar.status_code == 200
    assert calendar.json()["events"][0]["subscription_date"] == "2026-08-07"
    assert formula.status_code == 200
    assert formula.json()["points"][0]["values"] == {"MACD": "0.25"}
    assert formula_source.calls == [("formula_process_mul_zb", ("600000",))]


def test_tdx_local_routes_hide_internal_failure_details() -> None:
    api = client(ipo_source=IpoSource(fail=True), formula_source=FormulaSource(fail=True))

    calendar = api.get("/api/v1/tdx/local/ipo-calendar")
    formula = api.get(
        "/api/v1/tdx/local/formula",
        params=[("formula_name", "formula_process_mul_zb"), ("stock_codes", "600000")],
    )

    assert calendar.json()["status"] == "unavailable"
    assert formula.json()["status"] == "unavailable"
    assert "secret" not in calendar.text
    assert "secret" not in formula.text
