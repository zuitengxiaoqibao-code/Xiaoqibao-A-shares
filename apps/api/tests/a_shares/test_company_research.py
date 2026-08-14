import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.company_research import CompanyResearchService
from qibao_api.a_shares.diagnosis import AShareDiagnosis, DiagnosisSection, SECTION_NAMES
from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    CompanyResearchVersion,
    FinancialHistory,
    FinancialPeriod,
)
from qibao_api.gongbu.tdx_latest_tips import parse_latest_tips
from qibao_api.gongbu.research_enrichment import (
    HolderRecord, MarginRecord, PeerCandidateRecord, ResearchReportRecord, UnlockRecord,
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
        latest_tips = "●最新公告：2026-08-05 公司签署合作协议 | ●业绩预告：2026-07-15 预计净利润同比下降"
        return CompanyProfileEvidence(
            status="ready", company_overview="主营高端白酒",
            industry_analysis="行业需求仍在增长", latest_tips=latest_tips,
            latest_tip_items=parse_latest_tips(latest_tips, source="mootdx-f10", observed_at=NOW),
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
    evidence = {item.field_path: item for item in result.field_evidence}
    assert evidence["final_score"].value == result.final_score
    assert evidence["final_score"].formula == "base_score - risk_penalty"
    assert evidence["valuation.pe_ttm"].value == result.valuation.pe_ttm
    assert evidence["financial_history.latest_period.revenue"].source == result.financial_history.source
    assert tuple(item.key for item in result.research_sections) == (
        "business_model",
        "industry_space",
        "financial_trend",
        "profit_quality",
        "competitive_position",
        "valuation_percentile",
        "future_catalysts",
        "contrary_risks",
        "invalidation_conditions",
        "verification_checklist",
    )
    sections = {item.key: item for item in result.research_sections}
    assert "主营高端白酒" in sections["business_model"].summary
    assert "行业需求仍在增长" in sections["industry_space"].summary
    assert any("经营现金流" in fact for fact in sections["profit_quality"].facts)
    assert sections["competitive_position"].status == "unavailable"
    assert "历史估值序列" in sections["valuation_percentile"].limitation
    assert sections["verification_checklist"].facts


@pytest.mark.asyncio
async def test_company_research_classifies_conclusions_by_evidence_strength() -> None:
    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    conclusions = {item.key: item for item in result.conclusions}
    assert conclusions["business_model"].kind == "fact"
    assert "主营高端白酒" in conclusions["business_model"].claim
    assert conclusions["business_model"].evidence_ids
    assert conclusions["business_model"].observed_at == NOW
    assert conclusions["competitive_position"].kind == "unavailable"
    assert conclusions["competitive_position"].evidence_ids == ()
    assert conclusions["competitive_position"].limitations
    assert all(
        item.kind == "unavailable" or (item.evidence_ids and item.observed_at)
        for item in result.conclusions
    )


@pytest.mark.asyncio
async def test_company_research_field_evidence_covers_profile_tips_and_forward_valuation() -> None:
    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    evidence = {item.field_path: item for item in result.field_evidence}
    assert {"profile.company_overview", "profile.industry_analysis", "profile.latest_tips"} <= evidence.keys()
    assert "valuation.forward_pe" in evidence
    assert evidence["profile.latest_tips"].source == "mootdx-f10"


@pytest.mark.asyncio
async def test_company_research_freezes_a_version_after_deterministic_analysis() -> None:
    appended = []

    class Versions:
        def append(self, value):
            appended.append(value)
            return value.model_copy(update={
                "research_version": CompanyResearchVersion(
                    snapshot_id="version-1", version_number=1,
                    previous_snapshot_id=None, content_hash="a" * 64,
                    generated_at=value.generated_at, changes=(),
                ),
            })

    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), version_repository=Versions(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    assert len(appended) == 1
    assert result.research_version is not None
    assert result.research_version.snapshot_id == "version-1"


@pytest.mark.asyncio
async def test_company_research_keeps_latest_frozen_version_when_core_refresh_fails() -> None:
    cached = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 2))

    class DiagnosisFailure:
        async def diagnose(self, _symbol, _as_of):
            raise OSError("local history unavailable")

    class Versions:
        def latest(self, symbol):
            assert symbol == "600519"
            return cached

    result = await CompanyResearchService(
        DiagnosisFailure(), FinancialSource(financial_history()), ProfileSource(),
        version_repository=Versions(), clock=lambda: NOW,
    ).get("600519", date(2026, 8, 3))

    assert result.as_of == date(2026, 8, 2)
    assert result.status == "partial"
    assert any("沿用最近冻结研究版本" in reason for reason in result.reasons)


@pytest.mark.asyncio
async def test_company_research_returns_cached_enrichment_without_waiting_for_remote_refresh() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class Repository:
        def latest(self, _symbol):
            return type("Snapshot", (), {
                "observed_at": NOW,
                "stock_reports": (ResearchReportRecord(
                    report_id="r1", title="公司研报", publish_date=date(2026, 8, 1),
                    organization="机构", eps_next_year=Decimal("2.5"),
                ),),
                "industry_reports": (),
                "industry_name": "白酒",
                "industry_code": "451",
                "industry_board_code": "BK0896",
                "peer_candidates": (PeerCandidateRecord(
                    symbol="600809", name="山西汾酒", industry="白酒",
                    price=Decimal("180"), pe_ttm=Decimal("28"), pb=Decimal("7"),
                    market_cap_yi=Decimal("2200"), change_percent=Decimal("1.2"),
                ),),
                "unlocks": (UnlockRecord(free_date=date(2026, 9, 1), ratio_percent=Decimal("2.1")),),
                "margin": (MarginRecord(trade_date=date(2026, 8, 1), financing_balance=Decimal("100")),),
                "holders": (HolderRecord(period=date(2026, 6, 30), holder_count=Decimal("50000")),),
                "sources": ("eastmoney-reportapi", "eastmoney-datacenter"),
                "warnings": (),
            })()

        def append(self, _snapshot):
            return None

    class Source:
        async def fetch(self, _symbol):
            started.set()
            await release.wait()

    service = CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), enrichment_source=Source(),
        enrichment_repository=Repository(), clock=lambda: NOW + timedelta(hours=13),
    )
    result = await service.get("600519")

    assert result.enrichment.status == "ready"
    assert result.enrichment.stock_reports[0].eps_next_year == Decimal("2.5")
    assert result.enrichment.peer_candidates[0].symbol == "600809"
    assert result.enrichment.unlocks[0].ratio_percent == Decimal("2.1")
    await asyncio.wait_for(started.wait(), timeout=1)
    service.close()
    assert len(result.counter_case) == 10
    assert all(item.status in {"clear", "triggered", "unavailable"} for item in result.counter_case)
    assert next(item for item in result.dimensions if item.key == "business_model").score is None
    assert result.valuation.observation_range_status == "unavailable"
    catalyst = next(item for item in result.dimensions if item.key == "catalysts")
    assert catalyst.summary == "已识别 2 项事件：催化 1 · 中性 0 · 风险 1"
    ledger = {item.key: item for item in result.decision_ledger}
    assert tuple(ledger) == ("peer_context", "valuation", "catalysts", "contrary", "invalidation")
    assert ledger["peer_context"].status == "ready"
    assert any("600809" in fact and "山西汾酒" in fact for fact in ledger["peer_context"].facts)
    assert ledger["catalysts"].status == "ready"
    assert any("签署合作协议" in fact for fact in ledger["catalysts"].facts)


@pytest.mark.asyncio
async def test_company_research_calculates_forward_pe_only_from_three_unique_organizations() -> None:
    class Repository:
        def latest(self, _symbol):
            reports = (
                ResearchReportRecord(report_id="r1", title="研报1", publish_date=date(2026, 8, 3), organization="机构甲", eps_next_year=Decimal("2.0")),
                ResearchReportRecord(report_id="r2", title="研报2", publish_date=date(2026, 8, 2), organization="机构乙", eps_next_year=Decimal("2.5")),
                ResearchReportRecord(report_id="r3", title="研报3", publish_date=date(2026, 8, 1), organization="机构丙", eps_next_year=Decimal("3.0")),
                ResearchReportRecord(report_id="r4", title="研报4", publish_date=date(2026, 7, 1), organization="机构甲", eps_next_year=Decimal("99")),
            )
            peers = (
                PeerCandidateRecord(symbol="600809", name="山西汾酒", industry="白酒", price=Decimal("180"), pe_ttm=Decimal("28"), pb=Decimal("7"), market_cap_yi=Decimal("2200")),
                PeerCandidateRecord(symbol="000858", name="五粮液", industry="白酒", price=Decimal("120"), pe_ttm=Decimal("22"), pb=Decimal("5"), market_cap_yi=Decimal("4600")),
            )
            return type("Snapshot", (), {
                "observed_at": NOW, "stock_reports": reports, "industry_reports": (),
                "industry_name": "白酒", "industry_code": "451", "industry_board_code": "BK0896",
                "peer_candidates": peers, "unlocks": (), "margin": (), "holders": (),
                "sources": ("eastmoney-reportapi", "eastmoney-push2"), "warnings": (),
            })()

    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), enrichment_repository=Repository(), clock=lambda: NOW,
    ).get("600519")

    assert result.valuation.forward_eps_median == Decimal("2.5")
    assert result.valuation.forward_eps_sample_count == 3
    assert result.valuation.forward_pe == Decimal("600.00")
    assert result.valuation.forward_pe_status == "available"
    assert result.valuation.peer_pe_median == Decimal("25")
    assert result.valuation.peer_pb_median == Decimal("6")
    assert result.valuation.scenario_range.status == "available"
    assert result.valuation.scenario_range.conservative == Decimal("50.00")
    assert result.valuation.scenario_range.neutral == Decimal("62.50")
    assert result.valuation.scenario_range.optimistic == Decimal("75.00")
    assert "不是目标价" in result.valuation.scenario_range.reason
    valuation_ledger = next(item for item in result.decision_ledger if item.key == "valuation")
    assert valuation_ledger.status == "ready"
    assert any("3家机构" in fact and "前向 PE 600.00" in fact for fact in valuation_ledger.facts)


@pytest.mark.asyncio
async def test_company_research_withholds_forward_pe_when_consensus_sample_is_thin() -> None:
    class Repository:
        def latest(self, _symbol):
            return type("Snapshot", (), {
                "observed_at": NOW,
                "stock_reports": (
                    ResearchReportRecord(report_id="r1", title="研报1", publish_date=date(2026, 8, 3), organization="机构甲", eps_next_year=Decimal("2.0")),
                    ResearchReportRecord(report_id="r2", title="研报2", publish_date=date(2026, 8, 2), organization="机构乙", eps_next_year=Decimal("2.5")),
                ),
                "industry_reports": (), "industry_name": "白酒", "industry_code": "451",
                "industry_board_code": "BK0896", "peer_candidates": (), "unlocks": (),
                "margin": (), "holders": (), "sources": ("eastmoney-reportapi",), "warnings": (),
            })()

    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), enrichment_repository=Repository(), clock=lambda: NOW,
    ).get("600519")

    assert result.valuation.forward_eps_median == Decimal("2.25")
    assert result.valuation.forward_eps_sample_count == 2
    assert result.valuation.forward_pe is None
    assert result.valuation.forward_pe_status == "low_confidence"
    assert result.valuation.scenario_range.status == "unavailable"
    valuation_ledger = next(item for item in result.decision_ledger if item.key == "valuation")
    assert valuation_ledger.status == "partial"
    assert not any("前向 PE" in fact for fact in valuation_ledger.facts)
    assert any("2家" in fact and "未达到3家门槛" in fact for fact in valuation_ledger.facts)


@pytest.mark.asyncio
async def test_company_research_withholds_expired_forward_pe_and_reports_forecast_age() -> None:
    class Repository:
        def latest(self, _symbol):
            reports = tuple(
                ResearchReportRecord(
                    report_id=f"r{index}", title=f"研报{index}",
                    publish_date=date(2025, 12, 31), organization=f"机构{index}",
                    eps_next_year=Decimal("2.0"),
                )
                for index in range(3)
            )
            return type("Snapshot", (), {
                "observed_at": NOW, "stock_reports": reports, "industry_reports": (),
                "industry_name": "白酒", "industry_code": "451",
                "industry_board_code": "BK0896", "peer_candidates": (), "unlocks": (),
                "margin": (), "holders": (), "sources": ("eastmoney-reportapi",), "warnings": (),
            })()

    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), enrichment_repository=Repository(), clock=lambda: NOW,
    ).get("600519")

    assert result.valuation.forecast_latest_report_date == date(2025, 12, 31)
    assert result.valuation.forecast_age_days == 215
    assert result.valuation.forecast_freshness == "stale"
    assert result.valuation.forward_pe is None
    assert result.valuation.forward_pe_status == "unavailable"
    assert "超过 180 天" in result.valuation.forward_pe_reason


@pytest.mark.asyncio
async def test_company_research_ignores_future_dated_forecast_reports() -> None:
    class Repository:
        def latest(self, _symbol):
            return type("Snapshot", (), {
                "observed_at": NOW, "stock_reports": (
                    ResearchReportRecord(
                        report_id="future", title="未来研报", publish_date=date(2026, 8, 4),
                        organization="机构甲", eps_next_year=Decimal("9.0"),
                    ),
                ),
                "industry_reports": (), "industry_name": "白酒", "industry_code": "451",
                "industry_board_code": "BK0896", "peer_candidates": (), "unlocks": (),
                "margin": (), "holders": (), "sources": ("eastmoney-reportapi",), "warnings": (),
            })()

    result = await CompanyResearchService(
        DiagnosisService(diagnosis()), FinancialSource(financial_history()),
        ProfileSource(), enrichment_repository=Repository(), clock=lambda: NOW,
    ).get("600519")

    assert result.valuation.forecast_latest_report_date is None
    assert result.valuation.forecast_age_days is None
    assert result.valuation.forecast_freshness == "unavailable"
    assert result.valuation.forward_eps_sample_count == 0
    assert result.valuation.forward_pe is None


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
    evidence = {item.field_path: item for item in result.field_evidence}
    assert evidence["final_score"].status == "missing"
    assert evidence["final_score"].limitations
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
