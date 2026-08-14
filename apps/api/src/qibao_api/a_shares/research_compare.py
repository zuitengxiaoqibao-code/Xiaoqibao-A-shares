from decimal import Decimal

from qibao_api.contracts.research_compare import ResearchCompareCompany, ResearchCompareResponse


def _section(value, key: str):
    return next((item for item in value.research_sections if item.key == key), None)


def build_research_comparison(values, *, as_of, generated_at) -> ResearchCompareResponse:
    companies = []
    sources = set()
    for value in values:
        latest = value.financial_history.latest_period
        business = _section(value, "business_model")
        industry = _section(value, "industry_space")
        catalysts = _section(value, "future_catalysts")
        risks = _section(value, "contrary_risks")
        sources.update(item.source for item in value.sources if item.status != "unavailable")
        limitations = list(value.reasons)
        if value.status != "ready":
            limitations.append("公司研究输入未达到完整可用状态")
        companies.append(ResearchCompareCompany(
            symbol=value.symbol,
            name=value.name,
            status=value.status,
            evidence_coverage_percent=(value.evidence_coverage * Decimal("100")).quantize(Decimal("0.01")),
            final_score=value.final_score,
            business_model=business.summary if business else None,
            industry_space=industry.summary if industry else None,
            latest_revenue_yoy_percent=latest.revenue_yoy if latest else None,
            latest_net_profit_yoy_percent=latest.net_profit_yoy if latest else None,
            latest_operating_cash_flow=latest.operating_cash_flow if latest else None,
            pe_ttm=value.valuation.pe_ttm,
            pb=value.valuation.pb,
            catalysts=catalysts.facts[:5] if catalysts else (),
            risks=risks.facts[:5] if risks else (),
            limitations=tuple(dict.fromkeys(limitations)),
        ))
    ready = sum(item.status == "ready" for item in companies)
    available = sum(item.status != "unavailable" for item in companies)
    status = "ready" if ready == len(companies) else "partial" if available else "unavailable"
    return ResearchCompareResponse(
        status=status,
        as_of=as_of,
        generated_at=generated_at,
        companies=tuple(companies),
        sources=tuple(sorted(sources)),
        limitations=("比较结果只整理同口径事实和证据，不直接给出买卖结论",),
    )

