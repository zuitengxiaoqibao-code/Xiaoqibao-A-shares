from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path


PERSISTENT_DIRECTORIES = (
    "config", "data", "news", "cache", "logs", "models", "exports", "backups",
)
REBUILDABLE_DIRECTORIES = ("cache", "logs")
PROTECTED_DIRECTORIES = tuple(
    sorted(set(PERSISTENT_DIRECTORIES) - set(REBUILDABLE_DIRECTORIES))
)
DATABASE_SUFFIXES = {".duckdb", ".sqlite", ".sqlite3", ".db"}


class OperationsReadModel:
    """Bounded, read-mostly inventory for the portable runtime."""

    def __init__(self, root: Path, *, max_entries: int = 5_000) -> None:
        self.root = root.expanduser().resolve()
        self.max_entries = max_entries

    def _directory_inventory(self, directory: Path) -> dict:
        if not directory.is_dir():
            return {"exists": False, "file_count": 0, "bytes": 0, "truncated": False}
        file_count = 0
        total_bytes = 0
        latest_modified: datetime | None = None
        truncated = False
        pending = [directory]
        while pending and file_count < self.max_entries:
            current = pending.pop()
            try:
                entries = tuple(os.scandir(current))
            except OSError:
                continue
            for entry in entries:
                if file_count >= self.max_entries:
                    truncated = True
                    break
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                file_count += 1
                total_bytes += stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                if latest_modified is None or modified > latest_modified:
                    latest_modified = modified
        if pending:
            truncated = True
        return {
            "exists": True,
            "file_count": file_count,
            "bytes": total_bytes,
            "latest_modified_at": latest_modified.isoformat() if latest_modified else None,
            "truncated": truncated,
        }

    def snapshot(self) -> dict:
        directories = {
            name: self._directory_inventory(self.root / name)
            for name in PERSISTENT_DIRECTORIES
        }
        databases: dict[str, dict] = {}
        for folder_name in ("data", "news"):
            folder = self.root / folder_name
            if not folder.is_dir():
                continue
            try:
                entries = tuple(folder.iterdir())
            except OSError:
                continue
            for path in entries:
                if path.is_symlink() or not path.is_file() or path.suffix.lower() not in DATABASE_SUFFIXES:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                databases[path.relative_to(self.root).as_posix()] = {
                    "bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "directories": directories,
            "databases": databases,
            "scan_limit": self.max_entries,
            "release": self.release_inventory(),
        }

    def release_inventory(self) -> dict:
        directory_bytes = {
            name: self._directory_inventory(self.root / name)["bytes"]
            for name in PERSISTENT_DIRECTORIES
        }
        persistent_bytes = sum(directory_bytes.values())
        rebuildable_bytes = sum(
            directory_bytes[name] for name in REBUILDABLE_DIRECTORIES
        )
        total_bytes = self._directory_inventory(self.root)["bytes"]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_bytes": total_bytes,
            "program_bytes": max(0, total_bytes - persistent_bytes),
            "persistent_bytes": persistent_bytes,
            "rebuildable_bytes": rebuildable_bytes,
            "protected_directories": list(PROTECTED_DIRECTORIES),
            "rebuildable_directories": list(REBUILDABLE_DIRECTORIES),
        }

    def _cleanup_candidates(self, *, older_than_hours: int) -> list[tuple[str, Path, int]]:
        if older_than_hours < 0 or older_than_hours > 24 * 365:
            raise ValueError("cache retention must be between 0 and 8760 hours")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        candidates: list[tuple[str, Path, int]] = []
        for category in REBUILDABLE_DIRECTORIES:
            category_root = (self.root / category).resolve()
            if not category_root.is_dir() or not category_root.is_relative_to(self.root):
                continue
            for path in category_root.rglob("*"):
                try:
                    resolved = path.resolve()
                    if path.is_symlink() or not path.is_file() or not resolved.is_relative_to(category_root):
                        continue
                    stat = path.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    if modified <= cutoff:
                        candidates.append((category, path, stat.st_size))
                except OSError:
                    continue
        return candidates

    def cleanup_preview(self, *, older_than_hours: int) -> dict:
        candidates = self._cleanup_candidates(older_than_hours=older_than_hours)
        categories = {name: 0 for name in REBUILDABLE_DIRECTORIES}
        for category, _, _ in candidates:
            categories[category] += 1
        categories = {name: count for name, count in categories.items() if count}
        return {
            "candidate_count": len(candidates),
            "candidate_bytes": sum(size for _, _, size in candidates),
            "categories": categories,
        }

    def cleanup_rebuildable(self, *, older_than_hours: int) -> dict:
        candidates = self._cleanup_candidates(older_than_hours=older_than_hours)
        removed_count = 0
        removed_bytes = 0
        for _, path, size in candidates:
            try:
                path.unlink()
            except OSError:
                continue
            removed_count += 1
            removed_bytes += size
        return {"removed_count": removed_count, "removed_bytes": removed_bytes}

    def cleanup_cache(self, *, older_than_hours: int) -> dict:
        return self.cleanup_rebuildable(older_than_hours=older_than_hours)
