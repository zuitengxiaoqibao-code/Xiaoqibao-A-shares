import asyncio

import pytest

from qibao_api.bootstrap.lazy_service import AsyncLazyService


@pytest.mark.asyncio
async def test_lazy_service_constructs_once_on_first_use() -> None:
    calls = 0

    class Service:
        async def value(self) -> str:
            return "ready"

    def factory() -> Service:
        nonlocal calls
        calls += 1
        return Service()

    lazy = AsyncLazyService(factory)

    assert calls == 0
    assert await asyncio.gather(lazy.call("value"), lazy.call("value")) == ["ready", "ready"]
    assert calls == 1


@pytest.mark.asyncio
async def test_lazy_service_allows_retry_after_initialization_failure() -> None:
    calls = 0

    class Service:
        async def value(self) -> str:
            return "ready"

    def factory() -> Service:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("not ready")
        return Service()

    lazy = AsyncLazyService(factory)

    with pytest.raises(RuntimeError, match="not ready"):
        await lazy.call("value")
    assert await lazy.call("value") == "ready"
    assert calls == 2


@pytest.mark.asyncio
async def test_lazy_service_close_does_not_initialize_unused_service() -> None:
    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    lazy = AsyncLazyService(factory)
    lazy.close()

    assert calls == 0


@pytest.mark.asyncio
async def test_lazy_service_proxies_a_wrapped_method_named_get() -> None:
    class Service:
        async def get(self, symbol: str) -> str:
            return f"research:{symbol}"

    lazy = AsyncLazyService(Service)

    assert await lazy.get("600519") == "research:600519"
