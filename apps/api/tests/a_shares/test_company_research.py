from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.company_research import CompanyResearchService
from qibao_api.a_shares.diagnosis import AShareDiagnosis, DiagnosisSection, SECTION_NAMES
from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    FinancialHistory,
    FinancialPeriod,
)


NOW = datetime(2026, 8, 3, tzinfo=timezone.utc)


def section(name: str, metrics: dict | None = None, status: str = "ready") -> DiagnosisSection:
    return DiagnosisSection(
        status=status,
        observed_at=NOW,
        source=f"source-{name}",
        metrics=metrics or {},
        evidence_ids=(f"evidence-{name}",),
        explanation=f"{name} evidence",
    )


def diagnosis(**overrides: DiagnosisSection) -> AShareDiagnosis:
    sections = {name: section(name) for name in SECTION_NAMES}
    sections.update({
        "market": section("market", {"name": "贵州茅台", "price": Decimal("1500")}),
        "valuation": section("valuation", {
            "pe_ttm": Decimal("25"), "pb": Decimal("8"),
            "market_cap_yi": Decimal("18000"),
        }),
        "fundamentals": section("fundamentals", {"roe": Decimal("28")}),
        "trend": section("trend", {
            "volatility_20d": Decimal("0.03"), "drawdown_60d": Decimal("-0.08"),
        }),
        "events": section("events", {"event_count": 4, "adverse_event_count": 0}),
        "risk": section("risk", {"missing_section_count": 0}),
        **overrides,
    })
    return AShareDiagnosis(
        symbol="600519", as_of=date(2026, 8, 3), action="observe",
        overall_status="ready", sections=sections,
    )


def financial_history() -> FinancialHistory:
    annual = (
        FinancialPeriod(
            period=date(2023, 12, 31), revenue=Decimal("100"),
            net_profit=Decimal("20"), operating_cash_flow=Decimal("21"),
            gross_margin=Decimal("0.88"), cash_to_profit=Decimal("1.05"),
            debt_ratio=Decimal("0.20"),
        ),
        FinancialPeriod(
            period=date(2024, 12, 31), revenue=Decimal("115"),
            net_profit=Decimal("24"), operating_cash_flow=Decimal("25"),
            gross_margin=Decimal("0.89"), cash_to_profit=Decimal("1.04"),
            debt_ratio=Decimal("0.19"),
        ),
        FinancialPeriod(
            period=date(2025, 12, 31), revenue=Decimal("132"),
            revenue_yoy=Decimal("14.8"), net_profit=Decimal("29"),
            net_profit_yoy=Decimal("20.8"), operating_cash_flow=Decimal("31"),
            gross_margin=Decimal("0.90"), cash_to_profit=Decimal("1.069"),
            debt_ratio=Decimal("0.18"),
        ),
    )
    return FinancialHistory(
        status="ready", periods=annual, annual_periods=annual,
        latest_period=annual[-1], revenue_cagr_3y=Decimal("0.1489"),
        net_profit_cagr_3y=Decimal("0.2041"), source="sina-finance",
        observed_at=NOW, reasons=(),
    )


class DiagnosisService:
    def __init__(self, value: AShareDiagnosis) -> None:
        self.value = value

    async def diagnose(self, symbol: str, as_of: date) -> AShareDiagnosis:
        return self.value


class FinancialSource:
    def __init__(self, value: FinancialHistory) -> None:
        self.value = value

    def fetch(self, symbol: str) -> FinancialHistory:
        return self.value


class ProfileSource:
    def fetch(self, symbol: str) -> CompanyProfileEvidence:
        return CompanyProfileEvidence(
            status="ready", company_overview="主营高端白酒",
            industry_analysis="行业需求仍在增长", latest_tips="最新财报已披露",
            source="mootdx-f10", observed_at=NOW, reasons=(),
        )


@pytest.mark.asyncio
async def test_company_research_scores_only_verified_dimensions() -> None:
    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    assert len(result.dimensions) == 9
    assert result.evidence_coverage == Decimal("0.65")
    assert result.base_score is not None
    assert result.final_score is not None
    assert len(result.counter_case) == 10
    assert all(item.status in {"clear", "triggered", "unavailable"} for item in result.counter_case)
    assert next(item for item in result.dimensions if item.key == "business_model").score is None
    assert result.valuation.observation_range_status == "unavailable"


@pytest.mark.asyncio
async def test_company_research_withholds_score_when_financial_evidence_is_missing() -> None:
    unavailable = FinancialHistory(
        status="unavailable", periods=(), annual_periods=(), latest_period=None,
        revenue_cagr_3y=None, net_profit_cagr_3y=None,
        source="sina-finance", observed_at=None, reasons=("source unavailable",),
    )
    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(unavailable),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    assert result.evidence_coverage < Decimal("0.60")
    assert result.final_score is None
    assert next(item for item in result.counter_case if item.key == "cash_to_profit").status == "unavailable"


@pytest.mark.asyncio
async def test_company_research_flags_cash_flow_debt_and_valuation_risks() -> None:
    history = financial_history()
    weak = history.model_copy(update={
        "latest_period": history.latest_period.model_copy(update={
            "operating_cash_flow": Decimal("-3"),
            "cash_to_profit": Decimal("-0.10"),
            "debt_ratio": Decimal("0.82"),
        }),
        "annual_periods": (*history.annual_periods[:-1], history.latest_period.model_copy(update={
            "operating_cash_flow": Decimal("-3"),
            "cash_to_profit": Decimal("-0.10"),
            "debt_ratio": Decimal("0.82"),
        })),
    })
    risky_diagnosis = diagnosis(
        valuation=section("valuation", {
            "pe_ttm": Decimal("120"), "pb": Decimal("15"),
            "market_cap_yi": Decimal("18000"),
        })
    )

    result = await CompanyResearchService(
        DiagnosisService(risky_diagnosis), FinancialSource(weak),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    triggered = {item.key for item in result.counter_case if item.status == "triggered"}
    assert {"profit_cash_mismatch", "cash_to_profit", "high_debt", "valuation_risk"}.issubset(triggered)
    assert result.risk_penalty > 0
    assert result.final_score < result.base_score
