from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from qibao_api.contracts.instruments import validate_a_share_code


QuotePulseStatus = Literal["ready", "stale", "unavailable"]


class StockQuotePulse(BaseModel):
    """轻量个股行情快照，供个股观察的秒级行情区域使用。"""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(pattern=r"^\d{6}$")
    name: str = ""
    price: Decimal | None = None
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    volume: Decimal | None = None
    turnover_rate: Decimal | None = None
    market_cap_yi: Decimal | None = None
    observed_at: datetime | None = None
    fetched_at: datetime
    source: str = "tencent"
    status: QuotePulseStatus
    freshness: Literal["live", "stale", "unavailable"]
    age_seconds: float | None = None
    reason: str | None = None


class StockRealtimeQuoteService:
    """后台共享行情快照。

    请求线程只读取内存；上游请求由一个后台任务批量完成。多个页面观察
    同一股票时不会产生重复请求，短暂的上游失败也不会抹掉最后一笔有效行情。
    """

    def __init__(
        self,
        source: Any,
        *,
        poll_interval_seconds: float = 3.0,
        stale_after_seconds: float = 12.0,
        active_ttl_seconds: float = 180.0,
        clock: Callable[[], datetime] | None = None,
        bus: Any | None = None,
    ) -> None:
        if poll_interval_seconds <= 0 or stale_after_seconds <= 0 or active_ttl_seconds <= 0:
            raise ValueError("refresh intervals must be positive")
        self.source = source
        self.poll_interval_seconds = poll_interval_seconds
        self.stale_after_seconds = stale_after_seconds
        self.active_ttl_seconds = active_ttl_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.bus = bus
        self._active: dict[str, datetime] = {}
        self._quotes: dict[str, TencentLikeSnapshot] = {}
        self._errors: dict[str, str] = {}
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._closed = False
        self._refresh_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._closed = False
            self._task = asyncio.create_task(self._loop(), name="stock-realtime-quotes")

    async def close(self) -> None:
        self._closed = True
        self._wake.set()
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def watch(self, symbol: str) -> None:
        symbol = validate_a_share_code(symbol)
        self._active[symbol] = self.clock()
        self._wake.set()

    def snapshot(self, symbol: str) -> StockQuotePulse:
        symbol = validate_a_share_code(symbol)
        now = self.clock()
        quote = self._quotes.get(symbol)
        if quote is None:
            return StockQuotePulse(
                symbol=symbol,
                fetched_at=now,
                status="unavailable",
                freshness="unavailable",
                reason=self._errors.get(symbol) or "正在等待首笔实时行情",
            )
        observed_at = _aware(quote.observed_at)
        age = max(0.0, (now - observed_at).total_seconds())
        stale = symbol in self._errors or age > self.stale_after_seconds
        return StockQuotePulse(
            symbol=symbol,
            name=quote.name,
            price=quote.price,
            previous_close=quote.previous_close,
            change=quote.price - quote.previous_close,
            change_percent=(quote.price - quote.previous_close) / quote.previous_close * Decimal("100"),
            volume=quote.volume,
            turnover_rate=quote.turnover_rate,
            market_cap_yi=quote.market_cap_yi,
            observed_at=observed_at,
            fetched_at=now,
            source=quote.source,
            status="stale" if stale else "ready",
            freshness="stale" if stale else "live",
            age_seconds=round(age, 3),
            reason=self._errors.get(symbol) if stale else None,
        )

    async def refresh_once(self) -> None:
        async with self._refresh_lock:
            now = self.clock()
            self._active = {
                symbol: touched
                for symbol, touched in self._active.items()
                if (now - touched).total_seconds() <= self.active_ttl_seconds
            }
            symbols = tuple(sorted(self._active))
            if not symbols:
                return
            try:
                fetch_many = getattr(self.source, "fetch_snapshots", None)
                if fetch_many is None:
                    values = await asyncio.gather(
                        *(self.source.fetch_snapshot(symbol) for symbol in symbols),
                        return_exceptions=True,
                    )
                    result = {
                        symbol: value
                        for symbol, value in zip(symbols, values)
                        if not isinstance(value, BaseException)
                    }
                    failures = {
                        symbol: value
                        for symbol, value in zip(symbols, values)
                        if isinstance(value, BaseException)
                    }
                else:
                    fetched = await fetch_many(symbols)
                    result = _normalise_snapshots(fetched)
                    failures = {}
                    for symbol in symbols:
                        if symbol not in result:
                            failures[symbol] = RuntimeError("行情源未返回该股票")
            except Exception as error:  # upstream failure must not erase valid data
                result = {}
                failures = {symbol: error for symbol in symbols}
            for symbol, value in result.items():
                if value is None:
                    failures[symbol] = RuntimeError("行情源未返回该股票")
                    continue
                self._quotes[symbol] = value
                self._errors.pop(symbol, None)
            for symbol, error in failures.items():
                self._errors[symbol] = "行情源暂不可用，保留最近一次有效快照" if symbol in self._quotes else "实时行情暂不可用"
            if self.bus is not None and result:
                payload = {symbol: self.snapshot(symbol).model_dump(mode="json") for symbol in result}
                self.bus.publish(
                    "stock_quotes",
                    {"quotes": payload},
                    observed_at=now,
                    source="stock-realtime-cache",
                    freshness="live",
                )

    async def _loop(self) -> None:
        while not self._closed:
            await self.refresh_once()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                pass
            self._wake.clear()


class TencentLikeSnapshot:
    name: str
    price: Decimal
    previous_close: Decimal
    volume: Decimal | None
    turnover_rate: Decimal | None
    market_cap_yi: Decimal | None
    observed_at: datetime
    source: str


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _normalise_snapshots(values: Any) -> dict[str, TencentLikeSnapshot]:
    if isinstance(values, dict):
        values = values.values()
    result: dict[str, TencentLikeSnapshot] = {}
    for value in values or ():
        symbol = str(getattr(value, "symbol", ""))
        if symbol:
            result[symbol] = value
    return result
