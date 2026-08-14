from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from threading import RLock


class TdxAutoImportMonitor:
    """Detect local TDX daily-file changes and submit the existing import job.

    The monitor is deliberately conservative: the first poll establishes a
    baseline, only supported files are fingerprinted, and an active import
    always wins over a new automatic submission.
    """

    def __init__(
        self,
        paths_provider: Callable[[], Iterable[Path]],
        *,
        service,
        executor,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._paths_provider = paths_provider
        self._service = service
        self._executor = executor
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = RLock()
        self._fingerprint: tuple[tuple[str, int, int, int, str], ...] | None = None
        self._status: dict = {
            "state": "idle",
            "last_poll_at": None,
            "last_change_at": None,
            "last_submitted_at": None,
            "submitted_job_id": None,
            "skip_reason": None,
            "error": None,
            "file_count": 0,
        }

    def poll(self) -> dict:
        with self._lock:
            now = self._clock().isoformat()
            try:
                paths = tuple(Path(item).expanduser().resolve() for item in self._paths_provider())
                fingerprint = self._build_fingerprint(paths)
            except Exception as error:
                self._status = {
                    **self._status,
                    "state": "error",
                    "last_poll_at": now,
                    "error": str(error) or type(error).__name__,
                    "skip_reason": None,
                }
                return dict(self._status)

            previous = self._fingerprint
            self._fingerprint = fingerprint
            base = {
                **self._status,
                "last_poll_at": now,
                "file_count": len(fingerprint),
                "error": None,
                "skip_reason": None,
            }
            if previous is None:
                self._status = {**base, "state": "baseline"}
                return dict(self._status)
            if fingerprint == previous:
                self._status = {**base, "state": "unchanged"}
                return dict(self._status)

            active = self._service.current_job()
            if active is not None and active.state in {"pending", "running", "paused"}:
                self._status = {
                    **base,
                    "state": "skipped_active",
                    "skip_reason": "active_job",
                }
                return dict(self._status)

            try:
                job = self._service.create_job(paths)
                self._executor.submit(self._service.run, job.job_id)
            except Exception as error:
                self._status = {
                    **base,
                    "state": "error",
                    "last_change_at": now,
                    "error": str(error) or type(error).__name__,
                }
                return dict(self._status)

            self._status = {
                **base,
                "state": "submitted",
                "last_change_at": now,
                "last_submitted_at": now,
                "submitted_job_id": job.job_id,
            }
            return dict(self._status)

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)

    @staticmethod
    def _build_fingerprint(paths: Iterable[Path]) -> tuple[tuple[str, int, int, int, str], ...]:
        files: list[tuple[str, int, int, int, str]] = []
        seen: set[str] = set()
        for path in paths:
            candidates = (
                (path,)
                if path.is_file()
                else path.rglob("*")
                if path.is_dir()
                else ()
            )
            for candidate in candidates:
                if not candidate.is_file() or candidate.suffix.lower() not in {".day", ".zip"}:
                    continue
                normalized = str(candidate.resolve())
                key = normalized.casefold()
                if key in seen:
                    continue
                seen.add(key)
                stat = candidate.stat()
                # Windows can preserve both mtime and ctime for same-sized
                # in-place writes, so the monitor also records a content
                # digest. This is read-only and prevents stale local bars
                # from being silently missed.
                digest = hashlib.sha256()
                with candidate.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                files.append((normalized, int(stat.st_size), int(stat.st_mtime_ns), int(stat.st_ctime_ns), digest.hexdigest()))
        return tuple(sorted(files, key=lambda item: item[0].casefold()))
