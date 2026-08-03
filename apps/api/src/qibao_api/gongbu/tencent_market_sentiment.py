import hashlib
import time
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from statistics import median
from zoneinfo import ZoneInfo

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.market_sentiment import MarketBreadthObservation
from qibao_api.contracts.source_health import SourceAttemptEvent
from qibao_api.gongbu.tencent_quotes import market_prefix


CHINA_TZ = ZoneInfo("Asia/Shanghai")


class MarketSentimentSourceUnavailable(RuntimeError):
    pass


class RawSentimentBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    requested_symbols: tuple[str, ...]
    valid_count: int = Field(ge=0)
    fetched_at: AwareDatetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: bytes


class MarketSentimentFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation: MarketBreadthObservation
    raw_batches: tuple[RawSentimentBatch, ...]


class _Quote(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    price: Decimal
    previous_close: Decimal
    change_percent: Decimal
    high: Decimal
    low: Decimal
    amount_wan: Decimal
    limit_up: Decimal
    limit_down: Decimal
    observed_at: AwareDatetime


class TencentMarketSentimentSource:
    source_name = "tencent-market-sentiment"
    endpoint = "https://qt.gtimg.cn/q="

    def __init__(
        self,
        *,
        directory,
        client: httpx.Client,
        clock: Callable[[], datetime],
        observer: Callable[[SourceAttemptEvent], None] | None = None,
        batch_size: int = 80,
        wait: Callable[[float], None] = time.sleep,
        request_interval_seconds: float = 0.2,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch size must be positive")
        if request_interval_seconds < 0:
            raise ValueError("request interval cannot be negative")
        self.directory = directory
        self.client = client
        self.clock = clock
        self.observer = observer
        self.batch_size = batch_size
        self.wait = wait
        self.request_interval_seconds = request_interval_seconds

    def fetch(self, *, cutoff: datetime) -> MarketSentimentFetchResult:
        symbols = tuple(self.directory.active_symbols())
        if not symbols:
            raise MarketSentimentSourceUnavailable("active A-share universe is empty")
        if len(symbols) != len(set(symbols)):
            raise MarketSentimentSourceUnavailable("active A-share universe has duplicates")
        validated = tuple(validate_a_share_code(symbol) for symbol in symbols)
        quotes: dict[str, _Quote] = {}
        raw_batches: list[RawSentimentBatch] = []
        contributing_ids: list[str] = []
        for index, chunk in enumerate(self._chunks(validated)):
            if index:
                self.wait(self.request_interval_seconds)
            parsed, raw = self._attempt(chunk, cutoff=cutoff, target=f"batch-{index + 1}")
            raw_batches.append(raw)
            quotes.update(parsed)
            if parsed:
                contributing_ids.append(raw.snapshot_id)
            missing = tuple(symbol for symbol in chunk if symbol not in parsed)
            if missing:
                self.wait(self.request_interval_seconds)
                retry, retry_raw = self._attempt(
                    missing, cutoff=cutoff, target=f"batch-{index + 1}-retry"
                )
                raw_batches.append(retry_raw)
                quotes.update(retry)
                if retry:
                    contributing_ids.append(retry_raw.snapshot_id)
        ordered = tuple(quotes[symbol] for symbol in validated if symbol in quotes)
        fetched_at = self.clock()
        observed_at = max((item.observed_at for item in ordered), default=cutoff)
        changes = tuple(item.change_percent for item in ordered)
        return MarketSentimentFetchResult(
            observation=MarketBreadthObservation(
                requested_count=len(validated),
                valid_count=len(ordered),
                rising_count=sum(item.change_percent > 0 for item in ordered),
                falling_count=sum(item.change_percent < 0 for item in ordered),
                flat_count=sum(item.change_percent == 0 for item in ordered),
                median_change_percent=Decimal(median(changes)) if changes else None,
                total_amount_wan=(
                    sum((item.amount_wan for item in ordered), Decimal())
                    if ordered else None
                ),
                limit_up_count=sum(item.price >= item.limit_up for item in ordered),
                limit_down_count=sum(item.price <= item.limit_down for item in ordered),
                broken_limit_up_count=sum(
                    item.high >= item.limit_up and item.price < item.limit_up
                    for item in ordered
                ),
                max_limit_streak=None,
                observed_at=observed_at,
                fetched_at=fetched_at,
                source_snapshot_ids=tuple(dict.fromkeys(contributing_ids)),
            ),
            raw_batches=tuple(raw_batches),
        )

    def _chunks(self, symbols: tuple[str, ...]):
        for start in range(0, len(symbols), self.batch_size):
            yield symbols[start:start + self.batch_size]

    def _attempt(
        self, symbols: tuple[str, ...], *, cutoff: datetime, target: str
    ) -> tuple[dict[str, _Quote], RawSentimentBatch]:
        started = time.perf_counter()
        fetched_at = self.clock()
        content = b""
        error_code = None
        try:
            instruments = tuple(
                f"{market_prefix(symbol)}{symbol}" for symbol in symbols
            )
            response = self.client.get(f"{self.endpoint}{','.join(instruments)}")
            response.raise_for_status()
            content = response.content
            raw = content.decode("gbk", errors="strict")
            parsed = self._parse(raw, symbols, cutoff=cutoff)
            status = "ready" if parsed else "empty"
            if not parsed:
                error_code = "EmptyResponse"
        except UnicodeError:
            parsed = {}
            status = "error"
            error_code = "UnicodeError"
        except httpx.HTTPError as error:
            parsed = {}
            status = "error"
            error_code = type(error).__name__
        digest = hashlib.sha256(content).hexdigest()
        snapshot_id = f"tencent-market-{digest[:24]}"
        batch = RawSentimentBatch(
            snapshot_id=snapshot_id,
            requested_symbols=symbols,
            valid_count=len(parsed),
            fetched_at=fetched_at,
            content_sha256=digest,
            content=content,
        )
        self._emit(SourceAttemptEvent(
            source=self.source_name,
            operation="market_breadth",
            target=target,
            status=status,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            observed_at=fetched_at,
            error_code=error_code,
            metadata={
                "requested_count": len(symbols),
                "valid_count": len(parsed),
                "content_sha256": digest,
            },
        ))
        return parsed, batch

    @staticmethod
    def _parse(
        body: str, requested_symbols: tuple[str, ...], *, cutoff: datetime
    ) -> dict[str, _Quote]:
        expected = {
            f"{market_prefix(symbol)}{symbol}": symbol for symbol in requested_symbols
        }
        parsed = {}
        for statement in body.split(";"):
            statement = statement.strip()
            if not statement.startswith("v_") or '="' not in statement:
                continue
            key, payload = statement.split('="', 1)
            if not payload.endswith('"'):
                continue
            symbol = expected.get(key.removeprefix("v_"))
            if symbol is None:
                continue
            try:
                quote = TencentMarketSentimentSource._parse_quote(payload[:-1])
            except (IndexError, InvalidOperation, ValueError):
                continue
            if quote.symbol != symbol:
                continue
            local_cutoff = cutoff.astimezone(quote.observed_at.tzinfo)
            if (
                quote.observed_at > cutoff
                or quote.observed_at.date() != local_cutoff.date()
            ):
                continue
            parsed[symbol] = quote
        return parsed

    @staticmethod
    def _parse_quote(payload: str) -> _Quote:
        fields = payload.split("~")
        if len(fields) < 53:
            raise ValueError("Tencent sentiment quote is incomplete")
        symbol = validate_a_share_code(fields[2])
        values = {
            "price": Decimal(fields[3]),
            "previous_close": Decimal(fields[4]),
            "change_percent": Decimal(fields[32]),
            "high": Decimal(fields[33]),
            "low": Decimal(fields[34]),
            "amount_wan": Decimal(fields[37]),
            "limit_up": Decimal(fields[47]),
            "limit_down": Decimal(fields[48]),
        }
        if any(values[name] <= 0 for name in (
            "price", "previous_close", "high", "low", "limit_up", "limit_down"
        )):
            raise ValueError("Tencent sentiment quote has non-positive prices")
        if values["amount_wan"] < 0:
            raise ValueError("Tencent sentiment quote has negative amount")
        observed_at = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(
            tzinfo=CHINA_TZ
        )
        return _Quote(symbol=symbol, observed_at=observed_at, **values)

    def _emit(self, event: SourceAttemptEvent) -> None:
        if self.observer is None:
            return
        try:
            self.observer(event)
        except Exception:
            pass
