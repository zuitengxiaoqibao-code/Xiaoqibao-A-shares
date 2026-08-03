from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    CompanyResearchDimension,
    CompanyResearchResponse,
    CounterCaseItem,
    FinancialHistory,
    ValuationObservation,
)


def counter_case(index: int) -> CounterCaseItem:
    return CounterCaseItem(
        key=f"risk_{index}",
        title=f"风险检查 {index}",
        status="unavailable",
        detail="缺少证据，无法核验。",
        threshold=None,
        penalty=Decimal("0"),
        evidence_ids=(),
    )


def response(**overrides) -> CompanyResearchResponse:
    values = {
        "status": "partial",
        "symbol": "600519",
        "name": "贵州茅台",
        "as_of": date(2026, 8, 3),
        "generated_at": datetime(2026, 8, 3, tzinfo=timezone.utc),
        "dimensions": (
            CompanyResearchDimension(
                key="growth",
                label="增长质量",
                weight=15,
                status="ready",
                score=Decimal("80"),
                summary="年度营收和利润保持增长。",
                metrics={},
                evidence_ids=("financial:2025-12-31",),
                reason=None,
            ),
        ),
        "evidence_coverage": Decimal("0.15"),
        "base_score": Decimal("80"),
        "risk_penalty": Decimal("0"),
        "final_score": None,
        "financial_history": FinancialHistory(
            status="unavailable", periods=(), annual_periods=(),
            latest_period=None, revenue_cagr_3y=None,
            net_profit_cagr_3y=None, source="sina-finance",
            observed_at=None, reasons=("财务历史不可用",),
        ),
        "valuation": ValuationObservation(
            status="unavailable", pe_ttm=None, pb=None,
            market_cap_yi=None, observation_range_status="unavailable",
            observation_range_reason="缺少历史估值和前向盈利预测。",
            source="tencent", observed_at=None,
        ),
        "counter_case": tuple(counter_case(index) for index in range(10)),
        "profile": CompanyProfileEvidence(
            status="unavailable", company_overview=None,
            industry_analysis=None, latest_tips=None,
            source="mootdx-f10", observed_at=None,
            reasons=("F10不可用",),
        ),
        "sources": (),
        "reasons": (),
    }
    values.update(overrides)
    return CompanyResearchResponse(**values)


def test_company_research_requires_exactly_ten_counter_case_slots() -> None:
    with pytest.raises(ValidationError):
        response(counter_case=tuple(counter_case(index) for index in range(9)))


def test_company_research_rejects_score_when_coverage_is_below_sixty_percent() -> None:
    with pytest.raises(ValidationError):
        response(final_score=Decimal("80"))


def test_company_research_allows_null_score_when_evidence_is_incomplete() -> None:
    assert response().final_score is None
