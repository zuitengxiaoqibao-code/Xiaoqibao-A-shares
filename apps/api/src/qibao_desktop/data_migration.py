import shutil
from datetime import datetime, timezone
from collections.abc import Callable
from pathlib import Path

from qibao_api.runtime.layout import RuntimeLayout


CURRENT_MIGRATION_VERSION = 1
MIGRATION_FILENAME = ".migration-version"


def read_migration_version(root: Path) -> int:
    try:
        value = int((root / MIGRATION_FILENAME).read_text(encoding="ascii").strip())
    except (FileNotFoundError, ValueError, OSError):
        return 0
    return max(0, value)


def apply_migrations(
    root: Path,
    target_version: int,
    *,
    migrate: Callable[[int], None] | None = None,
) -> int:
    if target_version < 0:
        raise ValueError("target migration version must not be negative")
    root.mkdir(parents=True, exist_ok=True)
    current = read_migration_version(root)
    if target_version <= current:
        return current
    migrate_fn = migrate or (lambda _version: None)
    for version in range(current + 1, target_version + 1):
        migrate_fn(version)
        temporary = root / f"{MIGRATION_FILENAME}.tmp"
        temporary.write_text(str(version), encoding="ascii")
        temporary.replace(root / MIGRATION_FILENAME)
        current = version
    return current


def promote_previous_data_layout(layout: RuntimeLayout) -> None:
    previous = layout.previous_data_dir
    if not previous.is_dir():
        return

    archive_root = None
    for source in sorted(previous.iterdir(), key=lambda path: path.name):
        target = layout.data_dir / source.name
        if target.exists():
            if archive_root is None:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                archive_root = layout.backups_dir / f"previous-data-{stamp}"
                archive_root.mkdir(parents=True, exist_ok=False)
            shutil.move(str(source), str(archive_root / source.name))
        else:
            shutil.move(str(source), str(target))

    previous.rmdir()
