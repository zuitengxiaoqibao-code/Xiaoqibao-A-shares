# Full-Market A-Share Daily History Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a restart-safe background pipeline that fills and incrementally maintains verified daily bars for the active A-share universe, then exposes honest coverage to first-limit-up screening and the beginner UI.

**Architecture:** A persistent SQLite job repository owns job and per-symbol state. A synchronous orchestration service snapshots the instrument directory, fetches daily bars through mootdx with Baidu fallback, filters already stored dates, and writes DuckDB serially. FastAPI starts work in a bounded background executor, while coverage and job status remain readable without waiting for the sync.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite, DuckDB, mootdx, httpx, React, TypeScript, Vitest.

## Global Constraints

- Use only verified source responses; never synthesize bars, zero-fill missing values, or claim full-market coverage from a partial sample.
- Treat Chinese source as UTF-8-sensitive and edit it only with `apply_patch`.
- Initial backfill target is 300 daily bars per active A-share symbol.
- Analysis eligibility requires at least 250 distinct daily bars.
- Default source order is mootdx first, Baidu fallback second.
- DuckDB writes are serialized; background synchronization must not block ordinary API reads.
- Persist progress after every symbol so an API restart can resume safely.
- First-limit-up must disclose scan coverage and retain the last verified scan while a newer daily sync is incomplete.

---

### Task 1: Make mootdx node failover remember verified nodes

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_client.py`
- Test: `apps/api/tests/gongbu/test_tdx_client.py`

**Interfaces:**
- Consumes: existing `create_tdx_client()` and `TdxFailoverClient.bars()`.
- Produces: `TdxNodeHealth`, `TdxNodePool.ordered_servers()`, and successful-node promotion inside `TdxFailoverClient`.

- [ ] **Step 1: Write failing tests for empty-response failover and successful-node promotion**

```python
def test_successful_server_is_promoted_for_the_next_request():
    calls = []
    clients = {
        ("bad", 7709): EmptyClient(calls, "bad"),
        ("good", 7709): ReadyClient(calls, "good"),
    }
    pool = TdxNodePool((("bad", 7709), ("good", 7709)))
    client = TdxFailoverClient(
        pool=pool,
        probe=lambda *_: True,
        client_factory=lambda *, server, **_: clients[server],
    )
    client.bars(symbol="600519")
    client.bars(symbol="000001")
    assert calls == ["bad", "good", "good"]
```

- [ ] **Step 2: Run the focused test and confirm it fails because `TdxNodePool` does not exist**

Run: `python -m pytest apps/api/tests/gongbu/test_tdx_client.py -q`

Expected: FAIL during import or construction of `TdxNodePool`.

- [ ] **Step 3: Implement the minimal node pool and extend the static fallback list**

```python
@dataclass
class TdxNodeHealth:
    failures: int = 0
    retry_after: float = 0.0


class TdxNodePool:
    def __init__(self, servers, *, clock=time.monotonic, cooldown_seconds=60.0):
        self.servers = tuple(dict.fromkeys(servers))
        self.clock = clock
        self.cooldown_seconds = cooldown_seconds
        self.preferred = None
        self.health = {server: TdxNodeHealth() for server in self.servers}

    def ordered_servers(self):
        now = self.clock()
        ready = [server for server in self.servers if self.health[server].retry_after <= now]
        if self.preferred in ready:
            ready.remove(self.preferred)
            ready.insert(0, self.preferred)
        return tuple(ready or self.servers)

    def record_success(self, server):
        self.preferred = server
        self.health[server] = TdxNodeHealth()

    def record_failure(self, server):
        state = self.health[server]
        failures = state.failures + 1
        self.health[server] = TdxNodeHealth(
            failures=failures,
            retry_after=self.clock() + self.cooldown_seconds,
        )
```

Update `TdxFailoverClient` to consume a shared pool, record empty responses as failures, and promote only non-empty verified responses. Keep `servers=` backward compatible for existing tests.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest apps/api/tests/gongbu/test_tdx_client.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/gongbu/tdx_client.py apps/api/tests/gongbu/test_tdx_client.py
git commit -m "fix: strengthen mootdx node failover"
```

### Task 2: Add efficient daily-bar coverage queries and missing-only writes

**Files:**
- Modify: `apps/api/src/qibao_api/storage/bar_repository.py`
- Test: `apps/api/tests/storage/test_bar_repository.py`

**Interfaces:**
- Produces: `BarCoverage`, `BarRepository.coverage(symbols, target_date)`, and `BarRepository.append_missing(bars)`.

- [ ] **Step 1: Write failing repository tests**

```python
def test_append_missing_does_not_store_the_same_symbol_date_twice(tmp_path):
    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    bar = make_bar("600000", date(2026, 7, 24))
    assert repository.append_missing([bar]) == 1
    assert repository.append_missing([bar]) == 0
    assert repository.coverage(["600000"], date(2026, 7, 24))["600000"].bar_count == 1
```

- [ ] **Step 2: Run the focused test and confirm the missing methods fail**

Run: `python -m pytest apps/api/tests/storage/test_bar_repository.py -q`

Expected: FAIL with missing `append_missing` or `coverage`.

- [ ] **Step 3: Implement coverage and missing-only insertion**

```python
@dataclass(frozen=True)
class BarCoverage:
    symbol: str
    bar_count: int
    latest_trade_date: date | None


def coverage(self, symbols: Sequence[str], target_date: date) -> dict[str, BarCoverage]:
    validated = [validate_a_share_code(symbol) for symbol in symbols]
    result = {symbol: BarCoverage(symbol, 0, None) for symbol in validated}
    if not validated:
        return result
    placeholders = ", ".join("?" for _ in validated)
    with self._lock, self._connect() as connection:
        rows = connection.execute(
            f"""SELECT symbol, count(DISTINCT trade_date), max(trade_date)
                FROM daily_bars
                WHERE symbol IN ({placeholders}) AND trade_date <= ?
                GROUP BY symbol""",
            [*validated, target_date],
        ).fetchall()
    result.update({row[0]: BarCoverage(row[0], int(row[1]), row[2]) for row in rows})
    return result


def append_missing(self, bars: list[DailyBar]) -> int:
    if not bars:
        return 0
    grouped = {(bar.symbol, bar.trade_date): bar for bar in bars}
    symbols = sorted({symbol for symbol, _ in grouped})
    existing = {
        (bar.symbol, bar.trade_date)
        for symbol in symbols
        for bar in self.latest(symbol, max(1, len(grouped)))
    }
    missing = [bar for key, bar in grouped.items() if key not in existing]
    self.upsert(missing)
    return len(missing)
```

Keep the existing revision-preserving `upsert()` method for explicit correction workflows.

- [ ] **Step 4: Run storage tests**

Run: `python -m pytest apps/api/tests/storage/test_bar_repository.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/storage/bar_repository.py apps/api/tests/storage/test_bar_repository.py
git commit -m "feat: add daily history coverage queries"
```

### Task 3: Persist restart-safe full-market sync jobs

**Files:**
- Create: `apps/api/src/qibao_api/contracts/history_sync.py`
- Create: `apps/api/src/qibao_api/gongbu/history_sync_repository.py`
- Create: `apps/api/tests/gongbu/test_history_sync_repository.py`

**Interfaces:**
- Produces: `HistorySyncMode`, `HistorySyncState`, `HistorySyncJob`, `HistorySyncItem`, and `HistorySyncRepository`.

- [ ] **Step 1: Write failing tests for idempotency, progress, pause, and restart recovery**

```python
def test_incremental_job_is_idempotent_and_running_items_resume_as_pending(tmp_path):
    first = HistorySyncRepository(tmp_path / "history-sync.sqlite3")
    job = first.create_job("incremental", date(2026, 7, 24), ("000001", "600000"))
    assert first.create_job("incremental", date(2026, 7, 24), ("000001",)).job_id == job.job_id
    first.mark_running(job.job_id, "000001")
    first.close()

    reopened = HistorySyncRepository(tmp_path / "history-sync.sqlite3")
    reopened.recover_interrupted()
    assert reopened.next_pending(job.job_id).symbol == "000001"
```

- [ ] **Step 2: Run the new test and confirm imports fail**

Run: `python -m pytest apps/api/tests/gongbu/test_history_sync_repository.py -q`

Expected: FAIL because repository and contracts do not exist.

- [ ] **Step 3: Implement immutable API contracts and transactional SQLite state**

```python
class HistorySyncJob(BaseModel):
    model_config = ConfigDict(frozen=True)
    job_id: str
    mode: Literal["backfill", "incremental"]
    target_date: date
    state: Literal["pending", "running", "paused", "completed", "failed"]
    total_count: int
    ready_count: int
    failed_count: int
    skipped_count: int
    pending_count: int
    tdx_ready_count: int
    baidu_ready_count: int
    created_at: AwareDatetime
    updated_at: AwareDatetime
```

Use one transaction for item completion and aggregate job counters. Store only safe error codes in item rows.

- [ ] **Step 4: Run repository tests**

Run: `python -m pytest apps/api/tests/gongbu/test_history_sync_repository.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/contracts/history_sync.py apps/api/src/qibao_api/gongbu/history_sync_repository.py apps/api/tests/gongbu/test_history_sync_repository.py
git commit -m "feat: persist full-market history jobs"
```

### Task 4: Implement the full-market synchronization service

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/full_market_history.py`
- Create: `apps/api/tests/gongbu/test_full_market_history.py`
- Modify: `apps/api/src/qibao_api/gongbu/data_service.py`

**Interfaces:**
- Consumes: `AShareInstrumentDirectory.active_symbols()`, `BarRepository.coverage()`, `BarRepository.append_missing()`, `HistorySyncRepository`.
- Produces: `FullMarketHistoryService.create_backfill()`, `create_incremental(target_date)`, `run(job_id)`, `pause(job_id)`, `current_job()`, and `coverage(target_date)`.

- [ ] **Step 1: Write failing service tests**

```python
def test_backfill_skips_complete_symbols_and_falls_back_to_baidu(tmp_path):
    service = make_service(
        symbols=("000001", "600000"),
        coverage={"000001": 300, "600000": 0},
        tdx=FailingSource(),
        baidu=StaticSource(make_bars("600000", 300)),
    )
    job = service.create_backfill()
    service.run(job.job_id)
    result = service.job(job.job_id)
    assert result.skipped_count == 1
    assert result.baidu_ready_count == 1
    assert result.state == "completed"
```

Also test that a global source outage pauses after a bounded consecutive-failure threshold and does not attempt every symbol.

- [ ] **Step 2: Run the new tests and confirm the service is missing**

Run: `python -m pytest apps/api/tests/gongbu/test_full_market_history.py -q`

Expected: FAIL during import.

- [ ] **Step 3: Implement the orchestration loop**

```python
class FullMarketHistoryService:
    BACKFILL_BARS = 300
    ELIGIBLE_BARS = 250
    FAILURE_PAUSE_THRESHOLD = 20

    def create_backfill(self) -> HistorySyncJob:
        symbols = self.directory.active_symbols()
        return self.jobs.create_job("backfill", self.clock().date(), symbols)

    def create_incremental(self, target_date: date) -> HistorySyncJob:
        symbols = self.directory.active_symbols()
        return self.jobs.create_job("incremental", target_date, symbols)

    def run(self, job_id: str) -> HistorySyncJob:
        while (item := self.jobs.next_pending(job_id)) is not None:
            if self.jobs.is_pause_requested(job_id):
                return self.jobs.mark_paused(job_id)
            self._sync_item(job_id, item.symbol)
        return self.jobs.finish(job_id)
```

Fetch from mootdx first and Baidu second. Validate the complete returned batch before `append_missing`. Catch errors per symbol and persist `type(error).__name__`, not raw exception text.

- [ ] **Step 4: Run service tests**

Run: `python -m pytest apps/api/tests/gongbu/test_full_market_history.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/gongbu/full_market_history.py apps/api/src/qibao_api/gongbu/data_service.py apps/api/tests/gongbu/test_full_market_history.py
git commit -m "feat: synchronize full-market daily history"
```

### Task 5: Add non-blocking API routes and application lifecycle wiring

**Files:**
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/settings.py`
- Test: `apps/api/tests/routes/test_data.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces API endpoints:
  - `POST /api/v1/a-shares/history-sync/backfill`
  - `POST /api/v1/a-shares/history-sync/incremental`
  - `GET /api/v1/a-shares/history-sync/current`
  - `GET /api/v1/a-shares/history-sync/coverage`
  - `POST /api/v1/a-shares/history-sync/{job_id}/pause`

- [ ] **Step 1: Write failing route tests**

```python
def test_backfill_route_returns_before_background_work_finishes():
    service = RecordingFullMarketService()
    response = client(service).post("/api/v1/a-shares/history-sync/backfill")
    assert response.status_code == 202
    assert response.json()["state"] == "pending"
    assert service.run_calls == []
```

- [ ] **Step 2: Run route tests and confirm 404 responses**

Run: `python -m pytest apps/api/tests/routes/test_data.py -q`

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Implement routes and a single bounded executor**

Create jobs synchronously, submit `service.run(job_id)` to an application-owned `ThreadPoolExecutor(max_workers=1)`, and shut the executor down during lifespan cleanup. On startup call `recover_interrupted()` and resume the newest unfinished job. Reject creation of a second active job with HTTP 409.

- [ ] **Step 4: Run route and lifespan tests**

Run: `python -m pytest apps/api/tests/routes/test_data.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/routes/data.py apps/api/src/qibao_api/dependencies.py apps/api/src/qibao_api/main.py apps/api/src/qibao_api/settings.py apps/api/tests/routes/test_data.py apps/api/tests/libu_compliance/test_main_lifespan.py
git commit -m "feat: expose background history synchronization"
```

### Task 6: Gate first-limit-up scans on verified coverage

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/first_limit_up.py`
- Modify: `apps/api/src/qibao_api/a_shares/first_limit_up_repository.py`
- Modify: `apps/api/src/qibao_api/a_shares/first_limit_up_service.py`
- Test: `apps/api/tests/a_shares/test_first_limit_up_service.py`

**Interfaces:**
- Adds `universe_count`, `history_eligible_count`, `scan_coverage_count`, and `coverage_complete` to `FirstLimitUpBoard`.
- Persists coverage metadata with the cached scan.

- [ ] **Step 1: Write a failing partial-coverage test**

```python
@pytest.mark.asyncio
async def test_refresh_discloses_partial_universe_coverage(tmp_path):
    service = make_service(active_symbols=("000001", "600001"), histories={"600001": history})
    board = await service.refresh(AS_OF)
    assert board.universe_count == 2
    assert board.history_eligible_count == 1
    assert board.scan_coverage_count == 1
    assert board.coverage_complete is False
```

- [ ] **Step 2: Run the focused test and confirm the contract fields are absent**

Run: `python -m pytest apps/api/tests/a_shares/test_first_limit_up_service.py -q`

Expected: FAIL with missing fields.

- [ ] **Step 3: Inject an active-universe provider and persist scan coverage**

Only label coverage complete when every in-scope active symbol either has 250 bars or is explicitly classified as naturally history-insufficient. Do not infer completion from the number of detected limit-ups.

- [ ] **Step 4: Run first-limit-up tests**

Run: `python -m pytest apps/api/tests/a_shares/test_first_limit_up.py apps/api/tests/a_shares/test_first_limit_up_service.py apps/api/tests/routes/test_first_limit_up.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/contracts/first_limit_up.py apps/api/src/qibao_api/a_shares/first_limit_up_repository.py apps/api/src/qibao_api/a_shares/first_limit_up_service.py apps/api/tests/a_shares/test_first_limit_up_service.py
git commit -m "feat: disclose first-limit-up scan coverage"
```

### Task 7: Add beginner progress and coverage UI

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Modify: `apps/web/src/features/first-limit-up/types.ts`
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`

**Interfaces:**
- Consumes the history-sync current job, coverage summary, and extended first-limit-up board.
- Produces a start/pause control and explicit `covered / universe` display.

- [ ] **Step 1: Write failing UI tests**

```tsx
expect(screen.getByText("全市场日线覆盖")).toBeInTheDocument();
expect(screen.getByText("12 / 5,980")).toBeInTheDocument();
expect(screen.getByText("当前仅为部分市场结果")).toBeInTheDocument();
```

- [ ] **Step 2: Run focused tests and confirm the coverage UI is absent**

Run: `pnpm --dir apps/web exec vitest run src/features/data-settings/DataSettingsView.test.tsx src/features/first-limit-up/FirstLimitUpView.test.tsx`

Expected: FAIL on missing labels.

- [ ] **Step 3: Implement beginner-safe controls and warnings**

Show counts, percentage, job state, source counts, and a single primary start/resume action. Poll only while a job is pending or running. Keep the last verified data visible during polling failures and show a retryable warning.

- [ ] **Step 4: Run focused tests and build**

Run: `pnpm --dir apps/web exec vitest run src/features/data-settings/DataSettingsView.test.tsx src/features/first-limit-up/FirstLimitUpView.test.tsx`

Run: `pnpm --dir apps/web build`

Expected: tests and build pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/data-settings apps/web/src/features/first-limit-up apps/web/src/features/dashboard/Dashboard.tsx
git commit -m "feat: show full-market history coverage"
```

### Task 8: Schedule incremental sync before first-limit-up screening

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/scheduler.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/shangshu/test_scheduler.py`

**Interfaces:**
- Consumes: `FullMarketHistoryService.create_incremental()` and coverage state.
- Produces: post-close history job creation and deferred first-limit-up refresh until coverage is verified.

- [ ] **Step 1: Write a failing ordering test**

```python
def test_postclose_starts_history_sync_before_first_limit_up():
    scheduler.tick(POSTCLOSE)
    assert calls[0] == ("history", TRADING_DATE)
    assert "first-limit-up" not in calls
    history.complete(TRADING_DATE)
    scheduler.tick(POSTCLOSE_LATER)
    assert calls[-1] == ("first-limit-up", TRADING_DATE)
```

- [ ] **Step 2: Run scheduler tests and confirm current ordering fails**

Run: `python -m pytest apps/api/tests/shangshu/test_scheduler.py -q`

Expected: FAIL because first-limit-up runs without the coverage gate.

- [ ] **Step 3: Add idempotent history job creation and the coverage gate**

The scheduler may trigger the same post-close slot more than once; repository idempotency must return the existing job. First-limit-up is deferred, not marked completed, while history is pending or paused.

- [ ] **Step 4: Run scheduler tests**

Run: `python -m pytest apps/api/tests/shangshu/test_scheduler.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/shangshu/scheduler.py apps/api/src/qibao_api/main.py apps/api/tests/shangshu/test_scheduler.py
git commit -m "feat: refresh daily history before limit-up scan"
```

### Task 9: End-to-end verification and live smoke test

**Files:**
- Modify only if verification exposes a defect in the preceding tasks.

- [ ] **Step 1: Run all backend tests and scoped lint**

Run: `python -m pytest apps/api/tests -q`

Run: `python -m ruff check apps/api/src/qibao_api/gongbu apps/api/src/qibao_api/a_shares/first_limit_up_service.py apps/api/src/qibao_api/contracts/history_sync.py apps/api/src/qibao_api/routes/data.py`

Expected: zero failures.

- [ ] **Step 2: Run all frontend tests and production build**

Run: `pnpm --dir apps/web test`

Run: `pnpm --dir apps/web build`

Expected: 248 or more tests pass and the build exits zero.

- [ ] **Step 3: Run UTF-8, mojibake, and diff checks**

Strictly decode every touched Python, TypeScript, CSS, and Markdown file as UTF-8. Scan for replacement characters, repeated question marks, and established mojibake markers. Run `git diff --check`.

Expected: zero encoding, mojibake, and whitespace failures.

- [ ] **Step 4: Restart the local API and run a bounded live backfill smoke test**

Create a development job with three known symbols, verify at least one real source returns bars, verify persisted progress survives a restart, and query coverage. Do not claim full-market completion from this bounded smoke test.

- [ ] **Step 5: Start the real background backfill**

Start one full-market job through the production route. Report its job ID, total universe count, current progress, source state, and whether it is running or paused. The user must not need to keep the browser page open.
