from datetime import date, datetime, timezone

from qibao_api.a_shares.factor_registry import build_default_factor_registry
from qibao_api.a_shares.quant_research_snapshot import QuantResearchSnapshotStore
from qibao_api.contracts.quant_research import QuantResearchSnapshot


NOW = datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def snapshot(*, status: str = "partial") -> QuantResearchSnapshot:
    return QuantResearchSnapshot(
        status=status,
        as_of=date(2026, 8, 21),
        observed_at=NOW,
        generated_at=NOW,
        snapshot_source="computed",
        refresh_state="ready",
        factor_registry=build_default_factor_registry(
            registered_at=NOW,
        ).snapshot(as_of=NOW),
        limitations=("因子健康样本正在积累",),
    )


def test_research_snapshot_round_trip_is_atomic_and_date_scoped(tmp_path) -> None:
    store = QuantResearchSnapshotStore(tmp_path / "quant-research.json")
    expected = snapshot()

    store.save(expected)

    assert store.load(trading_date=date(2026, 8, 21)) == expected
    assert store.load(trading_date=date(2026, 8, 20)) is None
    assert not (tmp_path / "quant-research.json.tmp").exists()


def test_research_snapshot_keeps_last_good_when_error_snapshot_arrives(tmp_path) -> None:
    store = QuantResearchSnapshotStore(tmp_path / "quant-research.json")
    expected = snapshot()
    store.save(expected)

    store.save(snapshot(status="error"))

    assert store.load(trading_date=date(2026, 8, 21)) == expected


def test_research_snapshot_ignores_corrupt_payload(tmp_path) -> None:
    path = tmp_path / "quant-research.json"
    path.write_text("{not-json", encoding="utf-8")

    assert QuantResearchSnapshotStore(path).load(
        trading_date=date(2026, 8, 21),
    ) is None
