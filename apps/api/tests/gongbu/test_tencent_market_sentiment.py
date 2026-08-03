from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib

import httpx

from qibao_api.gongbu.tencent_market_sentiment import TencentMarketSentimentSource


CHINA_TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 7, 18, 10, 30, tzinfo=CHINA_TZ)


class Directory:
    def __init__(self, symbols: tuple[str, ...]) -> None:
        self.symbols = symbols

    def active_symbols(self) -> tuple[str, ...]:
        return self.symbols


class Response:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "failed",
                request=httpx.Request("GET", "https://qt.gtimg.cn"),
                response=httpx.Response(self.status_code),
            )


class Client:
    def __init__(self, *responses: bytes | Exception) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def get(self, url: str):
        self.urls.append(url)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return Response(result)


def quote(
    symbol: str,
    *,
    price: str = "10.00",
    previous_close: str = "10.00",
    change_percent: str = "0.00",
    high: str | None = None,
    low: str = "9.50",
    amount_wan: str = "1000",
    limit_up: str = "11.00",
    limit_down: str = "9.00",
    observed_at: str = "20260718103000",
    response_symbol: str | None = None,
) -> str:
    fields = [""] * 53
    fields[1] = f"股票{symbol}"
    fields[2] = response_symbol or symbol
    fields[3] = price
    fields[4] = previous_close
    fields[30] = observed_at
    fields[32] = change_percent
    fields[33] = high or price
    fields[34] = low
    fields[37] = amount_wan
    fields[47] = limit_up
    fields[48] = limit_down
    prefix = "sh" if symbol.startswith("6") else "sz"
    return f'v_{prefix}{symbol}="{"~".join(fields)}";'


def payload(*rows: str) -> bytes:
    return "".join(rows).encode("gbk")


def source(symbols: tuple[str, ...], client: Client, *, observer=None, batch_size=80):
    return TencentMarketSentimentSource(
        directory=Directory(symbols),
        client=client,
        clock=lambda: NOW,
        observer=observer,
        batch_size=batch_size,
        wait=lambda _: None,
        request_interval_seconds=0,
    )


def test_aggregates_only_verified_active_a_share_quotes() -> None:
    raw = payload(
        quote("600000", price="11.00", high="11.00", change_percent="10.00"),
        quote(
            "000001", price="9.00", high="10.00", low="9.00",
            change_percent="-10.00",
        ),
        quote(
            "300750", price="20.00", high="22.00", change_percent="2.00",
            limit_up="22.00", limit_down="18.00", amount_wan="3000",
        ),
    )
    result = source(("600000", "000001", "300750"), Client(raw)).fetch(cutoff=NOW)

    assert result.observation.requested_count == 3
    assert result.observation.valid_count == 3
    assert result.observation.rising_count == 2
    assert result.observation.falling_count == 1
    assert result.observation.flat_count == 0
    assert result.observation.median_change_percent == Decimal("2.00")
    assert result.observation.total_amount_wan == Decimal("5000")
    assert result.observation.limit_up_count == 1
    assert result.observation.limit_down_count == 1
    assert result.observation.broken_limit_up_count == 1
    assert result.observation.max_limit_streak is None
    assert len(result.raw_batches) == 1
    assert result.raw_batches[0].content_sha256 == hashlib.sha256(raw).hexdigest()


def test_retries_only_missing_or_invalid_symbols_once() -> None:
    client = Client(
        payload(quote("600000", change_percent="1.00")),
        payload(quote("000001", change_percent="-1.00")),
    )
    result = source(("600000", "000001"), client).fetch(cutoff=NOW)

    assert result.observation.valid_count == 2
    assert len(client.urls) == 2
    assert "sh600000,sz000001" in client.urls[0]
    assert client.urls[1].endswith("q=sz000001")


def test_rejects_mismatched_future_and_non_current_quotes_without_inventing_rows() -> None:
    raw = payload(
        quote("600000", response_symbol="000001"),
        quote("000001", observed_at="20260718103100"),
        quote("300750", observed_at="20260717150000"),
    )
    client = Client(raw, payload())
    result = source(("600000", "000001", "300750"), client).fetch(cutoff=NOW)

    assert result.observation.valid_count == 0
    assert result.observation.source_snapshot_ids == ()
    assert result.observation.total_amount_wan is None


def test_strict_gbk_failure_returns_zero_coverage_and_emits_a_safe_error() -> None:
    events = []
    client = Client(b"\xff\xff", payload())
    result = source(("600000",), client, observer=events.append).fetch(cutoff=NOW)

    assert result.observation.valid_count == 0
    assert all(event.source == "tencent-market-sentiment" for event in events)
    assert any(
        event.status == "error" and event.error_code == "UnicodeError"
        for event in events
    )


def test_fixed_batch_size_and_observer_failure_cannot_change_the_result() -> None:
    symbols = tuple(f"60{index:04d}" for index in range(81))
    first = payload(*(quote(symbol) for symbol in symbols[:80]))
    second = payload(quote(symbols[80]))

    def broken_observer(_event) -> None:
        raise RuntimeError("observer offline")

    client = Client(first, second)
    result = source(symbols, client, observer=broken_observer).fetch(cutoff=NOW)

    assert result.observation.valid_count == 81
    assert len(client.urls) == 2
    assert client.urls[0].count(",") == 79
    assert client.urls[1].count(",") == 0
