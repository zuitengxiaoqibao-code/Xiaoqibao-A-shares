from datetime import UTC, datetime

from qibao_api.contracts.market import AssetKind
from qibao_api.dongchang.models import AuditInput, SourceObservation
from qibao_api.dongchang.repository import AuditFindingRepository
from qibao_api.dongchang.audit import AuditEngine


def test_source_conflict_summary_is_append_only_and_deterministic(tmp_path):
    repository = AuditFindingRepository(tmp_path / "audit.sqlite3")
    observed_at = datetime(2026, 8, 13, 9, 30, tzinfo=UTC)
    payload = AuditInput(
        audit_run_id="audit-conflict-1",
        asset=AssetKind.A_SHARE,
        recommendation={
            "snapshot_id": "recommendation-1", "asset": "a_share", "symbol": "600000",
            "conclusion": "bullish", "evidence_link": "local://recommendation",
            "captured_at": observed_at,
        },
        outcome={
            "snapshot_id": "outcome-1", "asset": "a_share", "symbol": "600000",
            "conclusion": "neutral", "evidence_link": "local://outcome",
            "captured_at": observed_at.replace(minute=31),
        },
        source_observations=(
            SourceObservation(symbol="600000", as_of=observed_at, field="price", value="10.00", source="tdx", evidence_link="local://tdx"),
            SourceObservation(symbol="600000", as_of=observed_at, field="price", value="10.10", source="tencent", evidence_link="local://tencent"),
        ),
    )
    repository.append_audit(payload, AuditEngine(clock=lambda: observed_at).audit(payload))

    summary = repository.source_conflict_summary(asset=AssetKind.A_SHARE)

    assert summary["conflict_count"] == 1
    assert summary["conflicts"][0]["field"] == "price"
    assert summary["conflicts"][0]["candidate_sources"] == ["tdx", "tencent"]
    assert summary["conflicts"][0]["selected_source"] == "tdx"
    assert summary["conflicts"][0]["selection_reason"] == "source_priority_then_freshness"
    repository.close()
