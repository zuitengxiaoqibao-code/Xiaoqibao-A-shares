from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from threading import RLock
from typing import Any


class AsyncLazyService:
    """Initialize an optional service on first use without caching failures."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._instance: Any | None = None
        self._lock = asyncio.Lock()
        self._close_lock = RLock()

    async def resolve(self) -> Any:
        if self._instance is not None:
            return self._instance
        async with self._lock:
            if self._instance is None:
                candidate = self._factory()
                if inspect.isawaitable(candidate):
                    candidate = await candidate
                self._instance = candidate
        return self._instance

    async def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        service = await self.resolve()
        result = getattr(service, method)(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        async def invoke(*args: Any, **kwargs: Any) -> Any:
            return await self.call(name, *args, **kwargs)

        return invoke

    def close(self) -> None:
        with self._close_lock:
            service = self._instance
            self._instance = None
        if service is None:
            return
        close = getattr(service, "close", None)
        if close is not None:
            close()
