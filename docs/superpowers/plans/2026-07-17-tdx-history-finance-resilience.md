# TDX History And Finance Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep mootdx first while making empty-node failover fast and rejecting malformed Baidu daily bars or unusable finance snapshots.

**Architecture:** The application owns one retry per configured TDX node, so the default mootdx node client disables its internal retry loop. Baidu remains the independent fallback behind strict whole-batch validation, and finance transport success is separated from usable snapshot success.

**Tech Stack:** Python 3.12, mootdx 0.11.7, httpx, pandas, Pydantic, pytest, Ruff

## Global Constraints

- Preserve source order: mootdx first, Baidu second.
- Never fabricate, fill, or infer market or finance values.
- AI cannot change source data, deterministic actions, confidence, numbers, or risk gates.
- Do not add accounts, positions, orders, simulated funds, broker connectivity, or automated trading.
- Preserve unrelated dirty-worktree changes and do not stage or commit this slice.
- Edit with `apply_patch`; run UTF-8 and mojibake checks after touching source or docs.

---

### Task 1: Remove Nested Mootdx Retries

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_client.py`
- Test: `apps/api/tests/gongbu/test_tdx_client.py`

**Interfaces:**
- Consumes: `Quotes.factory(market, server, timeout, auto_retry)` from mootdx 0.11.7.
- Produces: `create_tdx_client()` with the existing public signature and one application-owned attempt per node.

- [x] **Step 1: Write the failing default-factory test**

```python
def test_default_factory_disables_nested_retry(monkeypatch) -> None:
    calls = []
    underlying = FakeClient(finance={"updated_date": 20260331})
    monkeypatch.setattr(
        tdx_client.Quotes,
        "factory",
        lambda **kwargs: calls.append(kwargs) or underlying,
    )
    client = create_tdx_client(
        servers=[("only", 7709)], probe=lambda host, port: True
    )

    client.finance(symbol="600519")

    assert calls == [{
        "market": "std", "server": ("only", 7709),
        "timeout": 3, "auto_retry": False,
    }]
```

- [x] **Step 2: Run the test and confirm the unexpected factory arguments are missing**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_tdx_client.py::test_default_factory_disables_nested_retry -q`

Expected: FAIL because the current default path calls `Quotes.factory` with only `market` and `server`.

- [x] **Step 3: Add a focused default node factory**

```python
def _create_quotes_client(*, market: str, server: tuple[str, int]):
    return Quotes.factory(
        market=market,
        server=server,
        timeout=3,
        auto_retry=False,
    )
```

Use `_create_quotes_client` only when `create_tdx_client` receives no custom
factory. Keep custom factory calls limited to `market` and `server`.

- [x] **Step 4: Run all TDX client tests**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_tdx_client.py -q`

Expected: all tests pass.

### Task 2: Make Baidu Batch Validation Atomic

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/baidu_history.py`
- Test: `apps/api/tests/gongbu/test_baidu_history.py`

**Interfaces:**
- Consumes: Baidu `newMarketData.keys` plus comma-separated `marketData` rows.
- Produces: sorted `list[DailyBar]` only after the complete batch validates.

- [x] **Step 1: Write failing validation tests**

```python
from qibao_api.gongbu.tdx_history import DataSourceUnavailable


KEYS = [
    "timestamp", "time", "open", "close",
    "volume", "high", "low", "amount",
]


def baidu_client(payload):
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        )
    )


def market_payload(*rows: str, keys=KEYS):
    return {
        "ResultCode": "0",
        "Result": {"newMarketData": {
            "keys": keys,
            "marketData": ";".join(rows),
        }},
    }


def test_baidu_history_rejects_missing_required_keys() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01",
        keys=KEYS[:-1],
    )
    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="missing required keys"):
            BaiduHistorySource(client).fetch_daily("600000", 20)


def test_baidu_history_rejects_truncated_rows() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01"
    )
    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="row width"):
            BaiduHistorySource(client).fetch_daily("600000", 20)


def test_baidu_history_rejects_duplicate_dates() -> None:
    row = "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01,693325381.00"
    payload = market_payload(row, row)
    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="duplicate trade date"):
            BaiduHistorySource(client).fetch_daily("600000", 20)


def test_baidu_history_rejects_entire_batch_when_later_ohlc_is_invalid() -> None:
    payload = market_payload(
        "1783872000,2026-07-13,9.04,9.19,75761962,9.21,9.01,693325381.00",
        "1783958400,2026-07-14,9.20,9.30,1000,9.10,9.00,9000.00",
    )
    with baidu_client(payload) as client:
        with pytest.raises(DataSourceUnavailable, match="invalid OHLC bounds"):
            BaiduHistorySource(client).fetch_daily("600000", 20)
```

- [x] **Step 2: Run the Baidu tests and confirm each new case fails for the intended reason**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_baidu_history.py -q`

Expected: FAIL because the current parser silently zips short rows and has no
batch-level duplicate or OHLC validation.

- [x] **Step 3: Add strict parsing and validation**

```python
REQUIRED_KLINE_KEYS = frozenset(
    {"time", "open", "high", "low", "close", "volume", "amount"}
)


def _parse_batch(self, symbol: str, keys: list[str], rows: list[str]):
    missing = REQUIRED_KLINE_KEYS.difference(keys)
    if missing:
        raise DataSourceUnavailable("Baidu K-line source missing required keys")
    bars = []
    seen_dates = set()
    for row in rows:
        if len(row.split(",")) < len(keys):
            raise DataSourceUnavailable("Baidu K-line row width is invalid")
        try:
            bar = self._parse_row(symbol, keys, row)
        except (KeyError, ValueError, ArithmeticError) as error:
            raise DataSourceUnavailable("Baidu K-line row is invalid") from error
        if bar.trade_date in seen_dates:
            raise DataSourceUnavailable("Baidu K-line duplicate trade date")
        seen_dates.add(bar.trade_date)
        if (
            min(bar.open, bar.high, bar.low, bar.close) <= 0
            or bar.volume < 0
            or bar.amount < 0
            or bar.high < max(bar.open, bar.close)
            or bar.low > min(bar.open, bar.close)
            or bar.high < bar.low
        ):
            raise DataSourceUnavailable("Baidu K-line invalid OHLC bounds")
        bars.append(bar)
    return bars
```

Call `_parse_batch` for the complete response and apply `[-limit:]` only after
it returns successfully.

- [x] **Step 4: Run Baidu and fallback service tests**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_baidu_history.py apps/api/tests/gongbu/test_data_service.py -q`

Expected: all tests pass.

### Task 3: Reject Unusable Finance Transport Success

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/fundamentals.py`
- Test: `apps/api/tests/a_shares/test_fundamentals.py`

**Interfaces:**
- Consumes: `parse_tdx_finance(...) -> FundamentalSnapshot`.
- Produces: a snapshot with at least one usable observation, or a clear `ValueError`.

- [x] **Step 1: Write a failing metadata-only snapshot test**

```python
class MetadataOnlyFinanceClient:
    def finance(self, symbol):
        return {"market": 1, "code": symbol}

    def close(self):
        pass


def test_tdx_finance_rejects_nonempty_response_without_usable_fields() -> None:
    with pytest.raises(ValueError, match="no usable fields"):
        TdxFinanceSource(client_factory=MetadataOnlyFinanceClient).fetch("600000")
```

- [x] **Step 2: Run the test and confirm it currently returns an empty snapshot**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_fundamentals.py::test_tdx_finance_rejects_nonempty_response_without_usable_fields -q`

Expected: FAIL because the current source accepts any non-empty mapping.

- [x] **Step 3: Add the usable-field quality gate**

```python
snapshot = parse_tdx_finance(mapping, symbol, self.clock())
usable_fields = (
    snapshot.data_updated_on,
    snapshot.industry,
    snapshot.eps,
    snapshot.roe,
    snapshot.net_profit,
    snapshot.revenue,
    snapshot.book_value_per_share,
    snapshot.total_shares,
)
if all(value is None for value in usable_fields):
    raise ValueError("mootdx finance response has no usable fields")
return snapshot
```

- [x] **Step 4: Run finance and diagnosis tests**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_fundamentals.py apps/api/tests/a_shares/test_diagnosis.py -q`

Expected: all tests pass.

### Task 4: Real-Source And Repository Verification

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: production source implementations and all repository checks.
- Produces: an evidence-backed roadmap entry and verification record.

- [x] **Step 1: Run focused and complete API verification**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_tdx_client.py apps/api/tests/gongbu/test_tdx_history.py apps/api/tests/gongbu/test_baidu_history.py apps/api/tests/gongbu/test_data_service.py apps/api/tests/a_shares/test_fundamentals.py -q
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q
apps/api/.venv/Scripts/python.exe -m ruff check apps/api/src apps/api/tests
```

Expected: zero failures and zero Ruff errors.

- [x] **Step 2: Repeat real `600519` source checks**

Measure `create_tdx_client().bars(...)` until aggregate failure, then call
`TdxFinanceSource().fetch(...)` and `BaiduHistorySource.fetch_daily(...)`
independently. Confirm the TDX empty-node sweep no longer incurs nested retries,
finance contains usable fields, and Baidu returns valid current daily bars.

- [x] **Step 3: Run web regression and production build**

Run:

```powershell
pnpm --filter @qibao/web test -- --run
pnpm --filter @qibao/web build
```

Expected: zero test failures and a successful production build.

- [x] **Step 4: Run encoding and diff gates**

Decode every changed text file with strict UTF-8, scan scoped source and docs for
known mojibake markers and repeated question marks, then run `git diff --check`.

Expected: zero decode errors, zero mojibake matches, and no whitespace errors.

- [x] **Step 5: Record the verified behavior in the roadmap**

Append this exact delivered bullet:

```markdown
- TDX node failover now owns retries end to end: mootdx internal retries are disabled, malformed Baidu daily-bar batches are rejected atomically, and metadata-only finance responses remain unavailable instead of being accepted as evidence.
```
