from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class QuantScanInput:
    database_path: Path
    parquet_path: Path
    source_size: int
    source_mtime_ns: int
    as_of: date
    created_at: datetime


class QuantScanSnapshotManager:
    """Build immutable, reusable inputs for the process-isolated market scan."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = RLock()

    @classmethod
    def default(cls) -> "QuantScanSnapshotManager":
        root = Path(tempfile.gettempdir()) / "qibao-quant-scan"
        return cls(root)

    @staticmethod
    def _signature(database_path: Path, as_of: date) -> tuple[str, int, int]:
        stat = database_path.stat()
        identity = hashlib.sha256(
            str(database_path.resolve()).encode("utf-8")
        ).hexdigest()[:12]
        fingerprint = hashlib.sha256(
            f"{identity}:{stat.st_size}:{stat.st_mtime_ns}:{as_of.isoformat()}".encode("ascii")
        ).hexdigest()[:20]
        return fingerprint, stat.st_size, stat.st_mtime_ns

    @staticmethod
    def _read_existing(target: Path, source_size: int, source_mtime_ns: int, as_of: date) -> QuantScanInput | None:
        database_path = target / "market.duckdb"
        manifest_path = target / "snapshot.json"
        if not database_path.is_file() or not manifest_path.is_file():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                int(payload["source_size"]) != source_size
                or int(payload["source_mtime_ns"]) != source_mtime_ns
                or payload["as_of"] != as_of.isoformat()
            ):
                return None
            return QuantScanInput(
                database_path=database_path,
                parquet_path=target / "parquet",
                source_size=source_size,
                source_mtime_ns=source_mtime_ns,
                as_of=as_of,
                created_at=datetime.fromisoformat(payload["created_at"]),
            )
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
            return None

    def prepare(self, repository, *, as_of: date) -> QuantScanInput:
        source_database = Path(repository.database_path)
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            fingerprint, source_size, source_mtime_ns = self._signature(source_database, as_of)
            target = self.root / fingerprint
            existing = self._read_existing(target, source_size, source_mtime_ns, as_of)
            if existing is not None:
                return existing

            staging = self.root / f".staging-{uuid4().hex}"
            try:
                staging.mkdir(parents=True, exist_ok=False)
                repository.snapshot_database_to(staging / "market.duckdb")
                (staging / "parquet").mkdir(exist_ok=True)
                fingerprint, source_size, source_mtime_ns = self._signature(source_database, as_of)
                target = self.root / fingerprint
                existing = self._read_existing(target, source_size, source_mtime_ns, as_of)
                if existing is not None:
                    return existing
                created_at = datetime.now(UTC)
                (staging / "snapshot.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "as_of": as_of.isoformat(),
                            "created_at": created_at.isoformat(),
                            "source_size": source_size,
                            "source_mtime_ns": source_mtime_ns,
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                staging.rename(target)
                result = QuantScanInput(
                    database_path=target / "market.duckdb",
                    parquet_path=target / "parquet",
                    source_size=source_size,
                    source_mtime_ns=source_mtime_ns,
                    as_of=as_of,
                    created_at=created_at,
                )
                self._prune(keep=target)
                return result
            finally:
                shutil.rmtree(staging, ignore_errors=True)

    def _prune(self, *, keep: Path) -> None:
        candidates = sorted(
            (
                path for path in self.root.iterdir()
                if path.is_dir() and not path.name.startswith(".staging-") and path != keep
            ),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for path in candidates[2:]:
            shutil.rmtree(path, ignore_errors=True)

