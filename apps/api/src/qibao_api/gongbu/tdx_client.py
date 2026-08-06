import socket
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from qibao_api.contracts.source_health import SourceAttemptEvent, SourceAttemptStatus

TDX_SERVERS: tuple[tuple[str, int], ...] = (
    ("119.97.185.59", 7709),
    ("124.70.133.119", 7709),
    ("116.205.183.150", 7709),
    ("123.60.73.44", 7709),
    ("116.205.163.254", 7709),
    ("121.36.225.169", 7709),
    ("123.60.70.228", 7709),
    ("124.71.9.153", 7709),
    ("110.41.147.114", 7709),
    ("124.71.187.122", 7709),
)


class _LazyQuotes:
    @staticmethod
    def factory(**kwargs):
        from mootdx.quotes import Quotes as _Quotes

        return _Quotes.factory(**kwargs)


# Keep the patchable module-level surface used by tests and integrations while
# avoiding mootdx/pandas import work until a real TDX request is made.
Quotes = _LazyQuotes()


class TdxOperationError(RuntimeError):
    pass


SourceAttemptObserver = Callable[[SourceAttemptEvent], None]


@dataclass(frozen=True)
class TdxNodeHealth:
    failures: int = 0
    retry_after: float = 0.0


class TdxNodePool:
    def __init__(
        self,
        servers: Sequence[tuple[str, int]],
        *,
        clock: Callable[[], float] = time.monotonic,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.servers = tuple(dict.fromkeys(servers))
        if not self.servers:
            raise ValueError("at least one mootdx server is required")
        self.clock = clock
        self.cooldown_seconds = cooldown_seconds
        self.preferred: tuple[str, int] | None = None
        self.health = {server: TdxNodeHealth() for server in self.servers}
        self._lock = threading.RLock()

    def ordered_servers(self) -> tuple[tuple[str, int], ...]:
        with self._lock:
            now = self.clock()
            ready = [
                server
                for server in self.servers
                if self.health[server].retry_after <= now
            ]
            if not ready:
                ready = list(self.servers)
            if self.preferred in ready:
                ready.remove(self.preferred)
                ready.insert(0, self.preferred)
            return tuple(ready)

    def record_success(self, server: tuple[str, int]) -> None:
        with self._lock:
            self.preferred = server
            self.health[server] = TdxNodeHealth()

    def record_failure(self, server: tuple[str, int]) -> None:
        with self._lock:
            failures = self.health[server].failures + 1
            self.health[server] = TdxNodeHealth(
                failures=failures,
                retry_after=self.clock() + self.cooldown_seconds,
            )


def _create_quotes_client(*, market: str, server: tuple[str, int]):
    return Quotes.factory(
        market=market,
        server=server,
        timeout=3,
        auto_retry=False,
    )


def probe_tdx_server(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def select_tdx_server(
    servers: Sequence[tuple[str, int]] = TDX_SERVERS,
    probe: Callable[[str, int], bool] = probe_tdx_server,
) -> tuple[str, int]:
    for host, port in servers:
        if probe(host, port):
            return host, port
    raise ConnectionError("no reachable mootdx server")


def _is_empty_response(response: Any) -> bool:
    if response is None:
        return True
    try:
        if bool(getattr(response, "empty", False)):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(response, (Mapping, Sequence)) and len(response) == 0


class TdxFailoverClient:
    def __init__(
        self,
        servers: Sequence[tuple[str, int]] | None,
        probe: Callable[[str, int], bool],
        client_factory: Callable[..., Any],
        observer: SourceAttemptObserver | None = None,
        pool: TdxNodePool | None = None,
    ) -> None:
        self.pool = pool or TdxNodePool(servers or ())
        self.servers = self.pool.servers
        self.probe = probe
        self.client_factory = client_factory
        self.observer = observer
        self._cleanup_errors: tuple[str, ...] = ()

    @property
    def cleanup_errors(self) -> tuple[str, ...]:
        return self._cleanup_errors

    def bars(self, *args, **kwargs):
        return self._execute("bars", *args, **kwargs)

    def finance(self, *args, **kwargs):
        return self._execute("finance", *args, **kwargs)

    def F10(self, *args, **kwargs):
        return self._execute(
            "F10",
            *args,
            _expected_mapping_key=kwargs.get("name"),
            **kwargs,
        )

    def close(self) -> None:
        pass

    def _record(
        self,
        *,
        operation: str,
        target: str,
        status: SourceAttemptStatus,
        started: float,
        error_code: str | None = None,
    ) -> None:
        if self.observer is None:
            return
        event = SourceAttemptEvent(
            source="mootdx",
            operation=operation,
            target=target,
            status=status,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            observed_at=datetime.now(timezone.utc),
            error_code=error_code,
        )
        try:
            self.observer(event)
        except Exception:
            # Telemetry must never make a valid source response unavailable.
            return

    def _execute(
        self,
        operation: str,
        *args,
        _expected_mapping_key: str | None = None,
        **kwargs,
    ):
        attempts: list[str] = []
        cleanup_errors: list[str] = []
        self._cleanup_errors = ()
        for host, port in self.pool.ordered_servers():
            server = (host, port)
            label = f"{host}:{port}"
            started = time.perf_counter()
            try:
                reachable = self.probe(host, port)
            except Exception as error:
                self.pool.record_failure(server)
                self._record(
                    operation=operation,
                    target=label,
                    status="error",
                    started=started,
                    error_code=type(error).__name__,
                )
                attempts.append(f"{label} (probe failed: {type(error).__name__})")
                continue
            if not reachable:
                self.pool.record_failure(server)
                self._record(
                    operation=operation,
                    target=label,
                    status="error",
                    started=started,
                    error_code="Unreachable",
                )
                attempts.append(f"{label} (unreachable)")
                continue

            try:
                client = self.client_factory(market="std", server=server)
            except Exception as error:
                self.pool.record_failure(server)
                self._record(
                    operation=operation,
                    target=label,
                    status="error",
                    started=started,
                    error_code=type(error).__name__,
                )
                attempts.append(
                    f"{label} (client creation failed: {type(error).__name__})"
                )
                continue

            operation_reason = None
            operation_error_code = None
            try:
                response = getattr(client, operation)(*args, **kwargs)
            except Exception as error:
                operation_reason = f"{operation} failed: {type(error).__name__}"
                operation_error_code = type(error).__name__

            cleanup_reason = None
            try:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
            except Exception as error:
                cleanup_reason = f"close failed: {type(error).__name__}"
                cleanup_errors.append(f"{label} ({cleanup_reason})")
                self._cleanup_errors = tuple(cleanup_errors)

            if operation_reason is not None:
                self.pool.record_failure(server)
                self._record(
                    operation=operation,
                    target=label,
                    status="error",
                    started=started,
                    error_code=operation_error_code,
                )
                reason = operation_reason
                if cleanup_reason is not None:
                    reason = f"{reason}; {cleanup_reason}"
                attempts.append(f"{label} ({reason})")
                continue

            response_is_empty = _is_empty_response(response)
            if (
                _expected_mapping_key
                and isinstance(response, Mapping)
                and _expected_mapping_key not in response
            ):
                response_is_empty = True
            if response_is_empty:
                self.pool.record_failure(server)
                self._record(
                    operation=operation,
                    target=label,
                    status="empty",
                    started=started,
                    error_code="EmptyResponse",
                )
                reason = "empty response"
                if cleanup_reason is not None:
                    reason = f"{reason}; {cleanup_reason}"
                attempts.append(f"{label} ({reason})")
                continue
            self.pool.record_success(server)
            self._record(
                operation=operation,
                target=label,
                status="ready",
                started=started,
            )
            return response

        detail = "; ".join(attempts) or "no servers configured"
        raise TdxOperationError(
            f"mootdx {operation} failed for all servers: {detail}"
        )


_DEFAULT_NODE_POOL = TdxNodePool(TDX_SERVERS)


def create_tdx_client(
    *,
    servers: Sequence[tuple[str, int]] = TDX_SERVERS,
    pool: TdxNodePool | None = None,
    probe: Callable[[str, int], bool] = probe_tdx_server,
    client_factory: Callable[..., Any] | None = None,
    observer: SourceAttemptObserver | None = None,
) -> TdxFailoverClient:
    selected_pool = pool
    if selected_pool is None and servers is TDX_SERVERS:
        selected_pool = _DEFAULT_NODE_POOL
    return TdxFailoverClient(
        servers=servers,
        pool=selected_pool,
        probe=probe,
        client_factory=client_factory or _create_quotes_client,
        observer=observer,
    )
