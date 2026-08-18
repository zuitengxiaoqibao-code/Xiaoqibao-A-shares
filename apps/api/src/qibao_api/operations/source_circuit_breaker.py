from __future__ import annotations

import time
from threading import RLock


class SourceCircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, recovery_seconds: float = 30) -> None:
        if failure_threshold < 1 or recovery_seconds <= 0:
            raise ValueError("failure_threshold and recovery_seconds must be positive")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._lock = RLock()
        self._state = "closed"
        self._failures = 0
        self._opened_at: float | None = None
        self._last_success_at: float | None = None

    def before_request(self, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "half_open":
                return False
            if self._opened_at is not None and current - self._opened_at >= self.recovery_seconds:
                self._state = "half_open"
                return True
            return False

    def record_success(self, *, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        with self._lock:
            self._state = "closed"
            self._failures = 0
            self._opened_at = None
            self._last_success_at = current

    def record_failure(self, *, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        with self._lock:
            self._failures += 1
            if self._state == "half_open" or self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = current

    def status(self, *, now: float | None = None) -> dict[str, int | float | str | None]:
        current = time.monotonic() if now is None else now
        with self._lock:
            retry_in = None
            if self._state == "open" and self._opened_at is not None:
                retry_in = max(0.0, self.recovery_seconds - (current - self._opened_at))
            return {
                "state": self._state,
                "failures": self._failures,
                "retry_in_seconds": retry_in,
                "last_success_at": self._last_success_at,
            }
