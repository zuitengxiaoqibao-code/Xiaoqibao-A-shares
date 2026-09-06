# Stock Observation Dual K-line Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a same-row intraday chart and latest-30-trading-day candlestick chart directly below the stock observation event K-line.

**Architecture:** Extend the existing stock timeline response with archived intraday snapshots from the existing poll-state repository, then render both new charts from the same loaded response so no duplicate daily-bar request is introduced. Keep intraday and daily availability independent, reuse the existing ECharts theme, and register the selected stock for background intraday sampling without blocking the visible timeline request.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, React, TypeScript, Vitest, Testing Library, ECharts, CSS, Pytest.

## Global Constraints

- Use only real local daily bars and real archived intraday snapshots; never generate placeholder prices.
- Keep A-share colors red-up and green-down.
- Preserve the existing event K-line and render the new two-chart row directly below it.
- Desktop layout is two equal columns; narrow layouts collapse to one column.
- One chart failing or having no data must not hide the other chart or block the page.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` during the portable rebuild.
- Do not close, restart, or control TongdaXin.

---

### Task 1: Extend the stock timeline contract with real intraday snapshots

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/stock_timeline.py`
- Modify: `apps/api/src/qibao_api/a_shares/stock_timeline.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/a_shares/test_stock_timeline.py`
- Test: `apps/api/tests/routes/test_research.py`

**Interfaces:**
- Consumes: `poll_state_repository.intraday_snapshots(symbol, trading_date, cutoff=cutoff)` and `trading_calendar.is_trading_day(date)`.
- Produces: `StockTimelineMinutePoint`, plus `StockTimelineResponse.intraday_status`, `intraday_points`, `intraday_sources`, and `intraday_warnings`.

- [x] **Step 1: Write failing service and route tests**

Add tests that construct ordered and out-of-order `MarketFeedSnapshot` rows for the selected date, verify the response sorts them by `observed_at`, and verify missing intraday data does not remove daily bars or events. Add a route assertion that the new response fields serialize.

- [x] **Step 2: Run tests to verify RED**

Run: `python -m pytest apps/api/tests/a_shares/test_stock_timeline.py apps/api/tests/routes/test_research.py -q`

Expected: FAIL because the timeline response has no intraday fields and the service does not read the poll-state repository.

- [x] **Step 3: Implement the minimal contract and service integration**

Define a frozen `StockTimelineMinutePoint` with the existing market snapshot fields. Add backward-compatible response defaults:

```python
intraday_status: Literal["ready", "waiting", "unavailable"] = "unavailable"
intraday_points: tuple[StockTimelineMinutePoint, ...] = ()
intraday_sources: tuple[str, ...] = ()
intraday_warnings: tuple[str, ...] = ()
```

Inject the poll-state repository and trading calendar into `StockTimelineService`, read only the requested date up to the route cutoff, sort by observation time, and return explicit waiting/unavailable warnings without changing daily bars or event status.

- [x] **Step 4: Run focused API tests to verify GREEN**

Run: `python -m pytest apps/api/tests/a_shares/test_stock_timeline.py apps/api/tests/routes/test_research.py -q`

Expected: PASS.

### Task 2: Build the independent dual-chart component

**Files:**
- Create: `apps/web/src/features/stock-timeline/StockTimeframeCharts.tsx`
- Create: `apps/web/src/features/stock-timeline/StockTimeframeCharts.test.tsx`
- Modify: `apps/web/src/features/stock-timeline/types.ts`

**Interfaces:**
- Consumes: one `StockTimelineResponse` already loaded by `StockEventKline`.
- Produces: `StockTimeframeCharts`, `stockIntradayOption`, and `stockThirtyDayOption`.

- [x] **Step 1: Write failing option and rendering tests**

Test that the intraday option contains a price line, previous-close mark line, and red/green volume; test that the 30-day option uses only the last 30 real bars and contains candlestick, MA5/MA10/MA20, and volume series. Test independent empty states for intraday and daily data.

- [x] **Step 2: Run tests to verify RED**

Run: `npm test -- --run src/features/stock-timeline/StockTimeframeCharts.test.tsx`

Expected: FAIL because the component and option builders do not exist.

- [x] **Step 3: Implement the minimal component**

Build stable A-share session labels, map real points by Shanghai time, derive previous close from the latest bar before the selected date, and calculate moving averages only from available closing prices. Render two separate cards so either side can show a Chinese empty reason without hiding the other.

- [x] **Step 4: Run focused Web tests to verify GREEN**

Run: `npm test -- --run src/features/stock-timeline/StockTimeframeCharts.test.tsx`

Expected: PASS.

### Task 3: Integrate the charts below the event K-line and register live focus

**Files:**
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`
- Modify: `apps/web/src/features/stock-timeline/api.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/web/src/app/theme.css`
- Modify: `apps/web/src/app/layout-safety.test.ts`

**Interfaces:**
- Consumes: `StockTimeframeCharts({ data })` and the existing `/intraday-focus` endpoint.
- Produces: selected-stock focus source `stock_observation` and a non-blocking focus registration helper.

- [x] **Step 1: Write failing integration and layout tests**

Verify that the event K-line region is followed by the two chart headings, the same response is used without a second timeline load, focus registration failure does not fail the timeline, desktop CSS uses two equal columns, and the responsive breakpoint switches to one column.

- [x] **Step 2: Run tests to verify RED**

Run: `npm test -- --run src/features/stock-timeline/StockEventKline.test.tsx src/app/layout-safety.test.ts`

Expected: FAIL because the two-chart row and focus source are not yet integrated.

- [x] **Step 3: Implement the minimal integration and styling**

Render `StockTimeframeCharts` immediately after the event panel using the already loaded timeline response. Start `stock_observation` focus registration without awaiting it before `loadStockTimeline`. Add equal-height responsive grid styles and keep all status text inside the affected card.

- [x] **Step 4: Run focused integration tests to verify GREEN**

Run: `npm test -- --run src/features/stock-timeline/StockEventKline.test.tsx src/features/stock-timeline/StockTimeframeCharts.test.tsx src/app/layout-safety.test.ts`

Expected: PASS.

### Task 4: Verify encoding, full test suites, production build, and portable EXE

**Files:**
- Modify only if a verification failure identifies a defect in files from Tasks 1–3.

**Interfaces:**
- Consumes: completed backend and frontend implementation.
- Produces: rebuilt `release/XiaoQiBao-Portable/xiaoqibao.exe` with preserved persistent directories and smoke-test evidence.

- [x] **Step 1: Run focused and full validation**

Run API Ruff and Pytest, Web Vitest and production build, `git diff --check`, and the project UTF-8/mojibake scan used by existing verification scripts.

- [x] **Step 2: Rebuild the portable executable**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`

Expected: portable release rebuilt while persistent directories remain present.

- [x] **Step 3: Smoke-test the actual executable**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`

Expected: the real EXE launches, API readiness and menu probes pass, then only the smoke-test application process exits.

- [x] **Step 4: Record final evidence**

Report exact test counts, build result, smoke timings, EXE path, and SHA-256. Confirm that no TongdaXin process was controlled.
