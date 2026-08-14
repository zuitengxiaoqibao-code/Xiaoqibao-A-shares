from datetime import date

from qibao_api.a_shares.quant_strategy import build_quant_strategy_dashboard
from qibao_api.a_shares.quant_strategy_snapshot import QuantStrategySnapshotStore

from .test_quant_strategy import NOW, board, overview


def test_quant_snapshot_round_trip_is_atomic_and_date_scoped(tmp_path) -> None:
    snapshot = build_quant_strategy_dashboard(
        overview(), board(), names={"600001": "样本股份"}, generated_at=NOW
    )
    store = QuantStrategySnapshotStore(tmp_path / "quant-strategy.json")

    store.save(snapshot)

    loaded = store.load(
        trading_date=date(2026, 7, 31),
        formula_version="a-share-short-strategy-v2.0",
    )
    assert loaded == snapshot
    assert store.load(
        trading_date=date(2026, 8, 1),
        formula_version="a-share-short-strategy-v2.0",
    ) is None
    assert store.load(
        trading_date=date(2026, 7, 31),
        formula_version="a-share-short-strategy-v1.0",
    ) is None
    assert not (tmp_path / "quant-strategy.json.tmp").exists()


def test_quant_snapshot_ignores_corrupt_payload(tmp_path) -> None:
    path = tmp_path / "quant-strategy.json"
    path.write_text("{not-json", encoding="utf-8")
    store = QuantStrategySnapshotStore(path)

    assert store.load(
        trading_date=date(2026, 7, 31),
        formula_version="a-share-short-strategy-v2.0",
    ) is None
