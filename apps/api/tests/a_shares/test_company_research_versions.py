from datetime import date, datetime, timezone
from decimal import Decimal

from qibao_api.a_shares.company_research_versions import CompanyResearchVersionRepository, _encoded_semantics
from qibao_api.contracts.company_research import CompanyResearchSection
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from tests.routes.test_company_research import sample_response


SECTION_KEYS = (
    ("business_model", "商业模式"),
    ("industry_space", "行业空间"),
    ("financial_trend", "财务趋势"),
    ("profit_quality", "利润质量"),
    ("competitive_position", "竞争地位"),
    ("valuation_percentile", "估值分位"),
    ("future_catalysts", "未来催化"),
    ("contrary_risks", "反方风险"),
    ("invalidation_conditions", "失效条件"),
    ("verification_checklist", "核验清单"),
)


def sections(business_summary: str, business_status: str = "ready") -> tuple[CompanyResearchSection, ...]:
    return tuple(CompanyResearchSection(
        key=key,
        label=label,
        status=business_status if key == "business_model" else "ready",
        summary=business_summary if key == "business_model" else f"{label}证据结论",
        facts=("主营业务证据",) if key == "business_model" else (),
        evidence_ids=("f10-1",) if key == "business_model" else (),
    ) for key, label in SECTION_KEYS)


def test_company_research_versions_are_append_only_and_compare_real_changes(tmp_path) -> None:
    repository = CompanyResearchVersionRepository(tmp_path / "company-research-versions.sqlite3")
    original = sample_response().model_copy(update={
        "as_of": date(2026, 8, 11),
        "generated_at": datetime(2026, 8, 11, 15, tzinfo=timezone.utc),
        "research_sections": sections("主营高端白酒"),
    })

    first = repository.append(original)
    duplicate = repository.append(original.model_copy(update={
        "generated_at": datetime(2026, 8, 11, 15, 5, tzinfo=timezone.utc),
    }))
    changed = repository.append(original.model_copy(update={
        "as_of": date(2026, 8, 12),
        "generated_at": datetime(2026, 8, 12, 15, tzinfo=timezone.utc),
        "evidence_coverage": Decimal("0.60"),
        "base_score": Decimal("71.00"),
        "final_score": Decimal("71.00"),
        "research_sections": sections("主营高端白酒，渠道结构出现变化", "partial"),
    }))

    assert first.research_version is not None
    assert first.research_version.version_number == 1
    assert duplicate.research_version.snapshot_id == first.research_version.snapshot_id
    assert changed.research_version.version_number == 2
    assert changed.research_version.previous_snapshot_id == first.research_version.snapshot_id
    assert any(item.category == "conclusion" and item.label == "商业模式" for item in changed.research_version.changes)
    assert any(item.category == "data" and item.label == "最终评分" for item in changed.research_version.changes)
    assert repository.history("600519", limit=10)[0].research_version.version_number == 2
    assert repository.verify_all() == 2
    repository.close()


def test_company_research_version_registers_new_and_reused_financial_snapshot(tmp_path) -> None:
    calls = []

    class Registry:
        def record(self, kind, **payload):
            calls.append((kind, payload))

    repository = CompanyResearchVersionRepository(
        tmp_path / "company-research-versions.sqlite3",
        shared_snapshot_registry=Registry(),
    )
    value = sample_response().model_copy(update={
        "as_of": date(2026, 8, 12),
        "generated_at": datetime(2026, 8, 12, 15, tzinfo=timezone.utc),
        "research_sections": sections("主营高端白酒"),
    })

    repository.append(value)
    repository.append(value)

    assert [kind for kind, _payload in calls] == [
        "financial_valuation", "financial_valuation",
    ]
    assert calls[0][1]["reused"] is False
    assert calls[1][1]["reused"] is True
    assert calls[0][1]["coverage_percent"] == 15.0
    repository.close()


def test_company_research_semantics_ignore_new_provenance_watermark_fields() -> None:
    legacy = sample_response().model_copy(update={
        "evidence_ledger": (EvidenceLedgerEntry(
            source="legacy-source",
            operation="company_research",
            status="partial",
            observed_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
            sample_count=1,
            limitations=("历史记录",),
        ),),
    })
    enriched = legacy.model_copy(update={
        "evidence_ledger": (legacy.evidence_ledger[0].model_copy(update={
            "total_count": 10,
            "coverage_percent": 10.0,
        }),),
    })

    assert _encoded_semantics(legacy) == _encoded_semantics(enriched)
