from pathlib import Path

from qibao_desktop.release_manifest import build_release_manifest
from qibao_desktop.data_migration import CURRENT_MIGRATION_VERSION


def test_release_manifest_contains_reproducibility_and_persistence_fields(tmp_path: Path) -> None:
    manifest = build_release_manifest(
        version="20260813T010000Z",
        commit="abc123",
        dependency_lock_hash="lock-hash",
        migration_version=4,
        persistent_dirs=("config", "data", "news", "cache", "logs", "models", "exports", "backups"),
        program_files=(
            {"path": "xiaoqibao.exe", "bytes": 10, "sha256": "exe-hash"},
        ),
    )

    assert manifest["version"] == "20260813T010000Z"
    assert manifest["commit"] == "abc123"
    assert manifest["source_state"] == "clean"
    assert manifest["working_tree_dirty"] is False
    assert manifest["dependency_lock_hash"] == "lock-hash"
    assert manifest["migration_version"] == 4
    assert manifest["persistent_dirs"] == ["config", "data", "news", "cache", "logs", "models", "exports", "backups"]
    assert manifest["program_sha256"] == "exe-hash"
    assert CURRENT_MIGRATION_VERSION == 1
