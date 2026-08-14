import json
import os
from datetime import datetime

import pytest

from qibao_desktop.pending_update import PendingUpdate, load_pending_update


def test_pending_update_rejects_stage_outside_dist_root(tmp_path) -> None:
    release = tmp_path / "dist" / "XiaoQiBao-Portable"
    release.mkdir(parents=True)
    manifest = release / "pending-update.json"
    manifest.write_text(json.dumps({
        "version": "v5",
        "staged_root": str(tmp_path / "outside"),
        "target_root": str(release),
        "created_at": "2026-08-12T08:00:00+08:00",
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="staged_root"):
        load_pending_update(manifest, allowed_dist_root=tmp_path / "dist")


def test_pending_update_plan_never_replaces_persistent_directories(tmp_path) -> None:
    dist = tmp_path / "dist"
    target = dist / "XiaoQiBao-Portable"
    stage = dist / "XiaoQiBao-Portable-staged-1" / "XiaoQiBao-Portable"
    (stage / "web").mkdir(parents=True)
    (stage / "data").mkdir()
    (stage / "web" / "index.html").write_text("new", encoding="utf-8")
    (stage / "data" / "market.duckdb").write_bytes(b"new-data")
    target.mkdir(parents=True)
    manifest = target / "pending-update.json"
    manifest.write_text(json.dumps({
        "version": "v5",
        "staged_root": str(stage),
        "target_root": str(target),
        "created_at": "2026-08-12T08:00:00+08:00",
    }), encoding="utf-8")

    update = load_pending_update(manifest, allowed_dist_root=dist)

    assert isinstance(update, PendingUpdate)
    assert [path.as_posix() for path in update.replacement_files()] == ["web/index.html"]


def test_pending_update_applies_program_files_and_preserves_persistent_data(tmp_path) -> None:
    dist = tmp_path / "dist"
    target = dist / "XiaoQiBao-Portable"
    stage = dist / "staged" / "XiaoQiBao-Portable"
    (target / "web").mkdir(parents=True)
    (target / "data").mkdir()
    (stage / "web").mkdir(parents=True)
    (stage / "data").mkdir()
    (target / "web" / "index.html").write_text("old", encoding="utf-8")
    (target / "data" / "market.duckdb").write_bytes(b"real-data")
    (stage / "web" / "index.html").write_text("new", encoding="utf-8")
    (stage / "data" / "market.duckdb").write_bytes(b"staged-data")
    update = PendingUpdate("v5", stage, target, datetime.fromisoformat("2026-08-12T08:00:00+08:00"))

    assert update.apply() == 1
    assert (target / "web" / "index.html").read_text(encoding="utf-8") == "new"
    assert (target / "data" / "market.duckdb").read_bytes() == b"real-data"


def test_pending_update_rolls_back_previous_files_when_replace_fails(tmp_path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    target = dist / "XiaoQiBao-Portable"
    stage = dist / "staged" / "XiaoQiBao-Portable"
    target.mkdir(parents=True)
    stage.mkdir(parents=True)
    (target / "a.txt").write_text("old-a", encoding="utf-8")
    (target / "b.txt").write_text("old-b", encoding="utf-8")
    (stage / "a.txt").write_text("new-a", encoding="utf-8")
    (stage / "b.txt").write_text("new-b", encoding="utf-8")
    update = PendingUpdate("v5", stage, target, datetime.fromisoformat("2026-08-12T08:00:00+08:00"))
    original = os.replace
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("locked")
        original(source, destination)

    monkeypatch.setattr("qibao_desktop.pending_update.os.replace", fail_second)

    with pytest.raises(OSError, match="locked"):
        update.apply()
    assert (target / "a.txt").read_text(encoding="utf-8") == "old-a"
    assert (target / "b.txt").read_text(encoding="utf-8") == "old-b"


def test_pending_update_only_copies_changed_program_files(tmp_path) -> None:
    dist = tmp_path / "dist"
    target = dist / "XiaoQiBao-Portable"
    stage = dist / "staged" / "XiaoQiBao-Portable"
    (target / "web").mkdir(parents=True)
    (stage / "web").mkdir(parents=True)
    (target / "web" / "same.js").write_bytes(b"same")
    (stage / "web" / "same.js").write_bytes(b"same")
    (target / "web" / "changed.js").write_bytes(b"old")
    (stage / "web" / "changed.js").write_bytes(b"new-content")
    update = PendingUpdate(
        "v6", stage, target,
        datetime.fromisoformat("2026-08-12T08:00:00+08:00"),
    )

    plan = update.replacement_plan()

    assert [item.relative.as_posix() for item in plan] == ["web/changed.js"]
    assert plan[0].bytes == len(b"new-content")
    assert update.apply() == 1
    assert (target / "web" / "same.js").read_bytes() == b"same"


def test_pending_update_removes_obsolete_program_files_but_keeps_persistent_files(tmp_path) -> None:
    dist = tmp_path / "dist"
    target = dist / "XiaoQiBao-Portable"
    stage = dist / "staged" / "XiaoQiBao-Portable"
    (target / "web").mkdir(parents=True)
    (target / "data").mkdir(parents=True)
    (stage / "web").mkdir(parents=True)
    (target / "web" / "obsolete.js").write_bytes(b"old-chunk")
    (target / "data" / "market.duckdb").write_bytes(b"real-data")
    (stage / "web" / "index.js").write_bytes(b"new")
    update = PendingUpdate(
        "v6", stage, target,
        datetime.fromisoformat("2026-08-12T08:00:00+08:00"),
    )

    assert [path.as_posix() for path in update.obsolete_files()] == [
        "web/obsolete.js",
    ]
    assert update.apply() == 2
    assert not (target / "web" / "obsolete.js").exists()
    assert (target / "data" / "market.duckdb").read_bytes() == b"real-data"
