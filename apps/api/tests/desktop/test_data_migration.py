from pathlib import Path

from qibao_desktop.data_migration import apply_migrations, read_migration_version


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    assert read_migration_version(tmp_path) == 0
    assert apply_migrations(tmp_path, 2) == 2
    assert read_migration_version(tmp_path) == 2
    assert apply_migrations(tmp_path, 2) == 2
    assert read_migration_version(tmp_path) == 2


def test_failed_migration_keeps_previous_version(tmp_path: Path) -> None:
    apply_migrations(tmp_path, 1)
    try:
        apply_migrations(tmp_path, 2, migrate=lambda version: (_ for _ in ()).throw(RuntimeError("boom")) if version == 2 else None)
    except RuntimeError:
        pass
    assert read_migration_version(tmp_path) == 1

