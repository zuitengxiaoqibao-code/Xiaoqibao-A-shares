from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import (
    get_tdx_formula_source,
    get_tdx_ipo_source,
    get_tdx_professional_source,
)
from qibao_api.gongbu.tdx_formula import TdxFormulaDataUnavailable, TdxFormulaPoint
from qibao_api.gongbu.tdx_local_calendar import TdxCalendarDataUnavailable, TdxIpoEvent
from qibao_api.gongbu.tdx_local_professional import (
    TdxProfessionalDataUnavailable,
    TdxProfessionalRow,
)
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


class ProfessionalSource:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def fetch(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise TdxProfessionalDataUnavailable("secret endpoint detail")
        return (TdxProfessionalRow(
            method=kwargs["method"], symbol="600000",
            values={"Fn193": Decimal("12.5")}, fetched_at=NOW,
        ),)


def client(ipo_source=None, formula_source=None, professional_source=None) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_tdx_ipo_source] = lambda: ipo_source or IpoSource()
    application.dependency_overrides[get_tdx_formula_source] = lambda: formula_source or FormulaSource()
    application.dependency_overrides[get_tdx_professional_source] = lambda: professional_source or ProfessionalSource()
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


def test_tdx_local_professional_route_returns_verified_rows_and_table_list() -> None:
    professional_source = ProfessionalSource()
    api = client(professional_source=professional_source)
    response = api.get(
        "/api/v1/tdx/local/professional",
        params=[
            ("method", "get_financial_data"),
            ("table_list", "Fn193"),
            ("stock_codes", "600000.SH"),
        ],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["rows"][0]["values"] == {"Fn193": "12.5"}
    assert professional_source.calls[0]["method"] == "get_financial_data"
    assert professional_source.calls[0]["fields"] == ("Fn193",)


def test_tdx_local_professional_route_hides_internal_failure_details() -> None:
    api = client(professional_source=ProfessionalSource(fail=True))
    response = api.get(
        "/api/v1/tdx/local/professional",
        params=[
            ("method", "get_financial_data"),
            ("table_list", "Fn193"),
            ("stock_codes", "600000"),
        ],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert "secret" not in response.text


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
