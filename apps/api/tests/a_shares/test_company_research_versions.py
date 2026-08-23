import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from qibao_api.a_shares.company_research_versions import CompanyResearchVersionRepository, _encoded_semantics
from qibao_api.contracts.company_research import (
    CompanyResearchSection,
    CompanyResearchVersion,
    ResearchConclusion,
)
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
    assert any(item.change_type in {"strengthened", "weakened", "updated"} for item in changed.research_version.changes)
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


def test_company_research_version_publishes_new_snapshot_without_sqlite_registry(tmp_path) -> None:
    from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus

    bus = RealtimeSnapshotBus()
    repository = CompanyResearchVersionRepository(
        tmp_path / "company-research-versions.sqlite3",
        realtime_snapshot_bus=bus,
    )
    value = sample_response().model_copy(update={
        "as_of": date(2026, 8, 12),
        "generated_at": datetime(2026, 8, 12, 15, tzinfo=timezone.utc),
        "research_sections": sections("主营高端白酒"),
    })

    stored = repository.append(value)

    event = bus.latest("company_research")
    assert event is not None
    assert event["payload"]["symbol"] == stored.symbol
    assert event["payload"]["research_version"]["content_hash"] == stored.research_version.content_hash
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


def test_company_research_semantics_ignore_derived_conclusion_presentation() -> None:
    legacy = sample_response().model_copy(update={
        "research_sections": sections("主营高端白酒"),
    })
    enriched = legacy.model_copy(update={
        "conclusions": (
            ResearchConclusion(
                key="business_model", label="商业模式", kind="fact",
                claim="主营高端白酒", evidence_ids=("f10-1",), source_count=1,
                observed_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
            ),
        ),
    })

    assert _encoded_semantics(legacy) == _encoded_semantics(enriched)


def test_company_research_versions_accept_legacy_provenance_semantics(tmp_path) -> None:
    repository = CompanyResearchVersionRepository(tmp_path / "company-research-versions.sqlite3")
    value = sample_response().model_copy(update={
        "as_of": date(2026, 8, 14),
        "generated_at": datetime(2026, 8, 14, 7, 36, tzinfo=timezone.utc),
        "research_sections": sections("主营高端白酒"),
    })

    payload = value.model_dump(
        mode="json",
        exclude={"generated_at", "research_version", "conclusions"},
    )

    def strip_legacy_timestamps(item, *, in_evidence_ledger: bool = False):
        if isinstance(item, dict):
            return {
                key: strip_legacy_timestamps(
                    child,
                    in_evidence_ledger=in_evidence_ledger or key == "evidence_ledger",
                )
                for key, child in item.items()
                if key not in {"observed_at", "generated_at", "fetched_at", "normalized_at"}
                and not (in_evidence_ledger and key in {"total_count", "coverage_percent"})
            }
        if isinstance(item, list):
            return [
                strip_legacy_timestamps(child, in_evidence_ledger=in_evidence_ledger)
                for child in item
            ]
        return item

    legacy_semantics = json.dumps(
        strip_legacy_timestamps(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    legacy_hash = hashlib.sha256(legacy_semantics.encode("utf-8")).hexdigest()
    assert legacy_hash != hashlib.sha256(_encoded_semantics(value).encode("utf-8")).hexdigest()

    snapshot_id = "company-research-600519-legacy"
    version = CompanyResearchVersion(
        snapshot_id=snapshot_id,
        version_number=1,
        content_hash=legacy_hash,
        generated_at=value.generated_at,
    )
    stored = value.model_copy(update={"research_version": version})
    encoded = stored.model_dump_json()
    canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    with repository.connection:
        repository.connection.execute(
            """INSERT INTO company_research_versions(
            snapshot_id,symbol,version_number,content_hash,canonical_hash,payload,generated_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                snapshot_id,
                value.symbol,
                1,
                legacy_hash,
                canonical_hash,
                encoded,
                value.generated_at.isoformat(),
            ),
        )

    assert repository.latest("600519") == stored
    repository.close()


def test_latest_skips_a_corrupt_newest_row_and_returns_previous_verified_cache(tmp_path) -> None:
    repository = CompanyResearchVersionRepository(tmp_path / "company-research-versions.sqlite3")
    value = sample_response().model_copy(update={
        "as_of": date(2026, 8, 14),
        "generated_at": datetime(2026, 8, 14, 7, 36, tzinfo=timezone.utc),
        "research_sections": sections("主营高端白酒"),
    })
    stored = repository.append(value)
    payload = stored.model_dump_json()
    canonical_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with repository.connection:
        repository.connection.execute(
            """INSERT INTO company_research_versions(
            snapshot_id,symbol,version_number,content_hash,canonical_hash,payload,generated_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                "company-research-600519-corrupt",
                "600519",
                2,
                "corrupt-semantic-hash",
                canonical_hash,
                payload,
                value.generated_at.isoformat(),
            ),
        )

    assert repository.latest("600519") == stored
    repository.close()
