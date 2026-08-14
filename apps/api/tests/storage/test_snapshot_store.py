import json

from qibao_api.storage.snapshot_store import SnapshotStore


def test_partial_snapshot_does_not_replace_complete_snapshot(tmp_path) -> None:
    store = SnapshotStore(tmp_path / "research.json", schema_version=2)
    store.write(scope="company-research", symbol="600519", value={"score": 80}, completeness="complete")

    written = store.write(scope="company-research", symbol="600519", value={"score": 10}, completeness="partial")

    assert written is False
    assert store.read(scope="company-research", symbol="600519")["value"] == {"score": 80}


def test_snapshot_rejects_wrong_schema_symbol_and_malformed_payload(tmp_path) -> None:
    path = tmp_path / "research.json"
    store = SnapshotStore(path, schema_version=2)
    store.write(scope="company-research", symbol="600519", value={"score": 80})

    assert store.read(scope="company-research", symbol="000001") is None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.read(scope="company-research", symbol="600519") is None


def test_atomic_write_failure_keeps_previous_complete_snapshot(tmp_path, monkeypatch) -> None:
    path = tmp_path / "research.json"
    store = SnapshotStore(path, schema_version=2)
    store.write(scope="company-research", symbol="600519", value={"score": 80})

    monkeypatch.setattr(store, "_replace", lambda source, target: (_ for _ in ()).throw(OSError("locked")))
    assert store.write(scope="company-research", symbol="600519", value={"score": 90}) is False

    assert json.loads(path.read_text(encoding="utf-8"))["value"] == {"score": 80}
