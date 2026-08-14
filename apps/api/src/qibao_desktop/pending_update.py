from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import shutil


PERSISTENT_DIRECTORIES = frozenset(
    {"config", "data", "news", "cache", "logs", "models", "exports", "backups"}
)


@dataclass(frozen=True)
class ReplacementFile:
    relative: PurePosixPath
    bytes: int


@dataclass(frozen=True)
class PendingUpdate:
    version: str
    staged_root: Path
    target_root: Path
    created_at: datetime

    def replacement_files(self) -> list[PurePosixPath]:
        return [item.relative for item in self.replacement_plan()]

    def replacement_plan(self) -> list[ReplacementFile]:
        files: list[ReplacementFile] = []
        for path in self.staged_root.rglob("*"):
            if not path.is_file():
                continue
            relative = PurePosixPath(path.relative_to(self.staged_root).as_posix())
            if relative.parts and relative.parts[0] in PERSISTENT_DIRECTORIES:
                continue
            target = self.target_root / Path(*relative.parts)
            if target.is_file() and _same_file(path, target):
                continue
            files.append(ReplacementFile(relative=relative, bytes=path.stat().st_size))
        return sorted(files, key=lambda item: str(item.relative))

    def obsolete_files(self) -> list[PurePosixPath]:
        staged = {
            PurePosixPath(path.relative_to(self.staged_root).as_posix())
            for path in self.staged_root.rglob("*")
            if path.is_file()
        }
        obsolete: list[PurePosixPath] = []
        for path in self.target_root.rglob("*"):
            if not path.is_file():
                continue
            relative = PurePosixPath(path.relative_to(self.target_root).as_posix())
            if relative.parts and relative.parts[0] in PERSISTENT_DIRECTORIES:
                continue
            if relative not in staged:
                obsolete.append(relative)
        return sorted(obsolete, key=str)

    def apply(self) -> int:
        rollback_root = self.target_root.parent / f".{self.target_root.name}-rollback-{self.version}"
        if rollback_root.exists():
            shutil.rmtree(rollback_root)
        rollback_root.mkdir(parents=True)
        replaced: list[PurePosixPath] = []
        created: list[PurePosixPath] = []
        removed: list[PurePosixPath] = []
        try:
            for relative in self.obsolete_files():
                target = self.target_root / Path(*relative.parts)
                backup = rollback_root / Path(*relative.parts)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                target.unlink()
                removed.append(relative)
            for item in self.replacement_plan():
                relative = item.relative
                source = self.staged_root / Path(*relative.parts)
                target = self.target_root / Path(*relative.parts)
                backup = rollback_root / Path(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                    replaced.append(relative)
                else:
                    created.append(relative)
                temporary = target.with_name(f".{target.name}.update-tmp")
                shutil.copy2(source, temporary)
                os.replace(temporary, target)
            return len(removed) + len(replaced) + len(created)
        except Exception:
            for relative in created:
                try:
                    (self.target_root / Path(*relative.parts)).unlink(missing_ok=True)
                except OSError:
                    pass
            for relative in (*removed, *replaced):
                backup = rollback_root / Path(*relative.parts)
                target = self.target_root / Path(*relative.parts)
                if backup.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
            raise
        finally:
            if rollback_root.exists():
                shutil.rmtree(rollback_root, ignore_errors=True)


def load_pending_update(manifest: Path, *, allowed_dist_root: Path) -> PendingUpdate:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    allowed = allowed_dist_root.resolve()
    staged = Path(payload["staged_root"]).resolve()
    target = Path(payload["target_root"]).resolve()
    if not staged.is_relative_to(allowed):
        raise ValueError("staged_root is outside allowed dist root")
    if not target.is_relative_to(allowed):
        raise ValueError("target_root is outside allowed dist root")
    if staged == target or not staged.is_dir():
        raise ValueError("staged_root is invalid")
    return PendingUpdate(
        version=str(payload["version"]),
        staged_root=staged,
        target_root=target,
        created_at=datetime.fromisoformat(payload["created_at"]),
    )


def _same_file(left: Path, right: Path, *, chunk_size: int = 1024 * 1024) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as first, right.open("rb") as second:
        while True:
            first_chunk = first.read(chunk_size)
            second_chunk = second.read(chunk_size)
            if first_chunk != second_chunk:
                return False
            if not first_chunk:
                return True
