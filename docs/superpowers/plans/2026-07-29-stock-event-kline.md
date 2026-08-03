# Stock Event K-line Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a truthful stock-specific daily candlestick chart with time-aligned verified news and topic annotations to the A-share cockpit.

**Architecture:** A read-only `StockTimelineService` joins local daily bars with verified symbol-linked news and archived interpretations. A dedicated React feature fetches that contract independently from the cockpit and renders an ECharts candlestick/volume panel with a linked evidence list.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, DuckDB/SQLite repositories, React 19, TypeScript 5.8, ECharts 5.6, Vitest, pytest.

## Global Constraints

- Never create simulated market, news, topic, timestamp, or impact data.
- Plot only verified symbol-linked `market_news` with original timestamps.
- Keep `market_hotspot` collection timestamps off the chart.
- Use A-share colors: red up, green down; uncertain impact is gray.
- Preserve UTF-8 Chinese source text and run a mojibake scan after edits.

---

### Task 1: Backend timeline contract and service

**Files:**
- Create: `apps/api/src/qibao_api/contracts/stock_timeline.py`
- Create: `apps/api/src/qibao_api/a_shares/stock_timeline.py`
- Test: `apps/api/tests/a_shares/test_stock_timeline.py`

**Interfaces:**
- Consumes: `BarRepository.latest(symbol, limit, cutoff=...)`, `NewsRepository.effective_events_for_symbol(...)`, and `NewsRepository.interpretations_for_events(...)`.
- Produces: `StockTimelineService.get(symbol, as_of, cutoff, limit=120) -> StockTimelineResponse`.

- [ ] Write tests proving only verified `market_news` is returned, directions use the latest eligible interpretation, non-trading-day events remain unpinned, and bars are chronological.
- [ ] Run `pytest tests/a_shares/test_stock_timeline.py -q` and confirm the module is missing.
- [ ] Implement the Pydantic contract and local repository join.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: FastAPI route wiring

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Test: `apps/api/tests/routes/test_research.py`

**Interfaces:**
- Consumes: `get_stock_timeline_service`.
- Produces: `GET /api/v1/a-shares/{symbol}/timeline?as_of=YYYY-MM-DD`.

- [ ] Write a failing route test that checks validation, dependency delegation, and JSON fields.
- [ ] Run the focused route test and confirm failure because the route does not exist.
- [ ] Wire the service and route without external calls.
- [ ] Re-run the focused route test and confirm it passes.

### Task 3: ECharts event K-line

**Files:**
- Create: `apps/web/src/features/stock-timeline/types.ts`
- Create: `apps/web/src/features/stock-timeline/api.ts`
- Create: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Test: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`

**Interfaces:**
- Consumes: `StockTimelineResponse`.
- Produces: `stockTimelineOption(data, selectedEventId)` and `StockEventKline`.

- [ ] Write failing tests for candlestick colors, vertical labels, three-lane collision handling, uncertain gray, and selected event highlighting.
- [ ] Run the focused Vitest file and confirm missing-module failure.
- [ ] Implement the chart and linked evidence list with no placeholder series.
- [ ] Re-run the focused test and confirm it passes.

### Task 4: Cockpit integration and responsive styling

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `loadStockTimeline(symbol, asOf, signal)`.
- Produces: an independently loading event K-line directly below the stock identity/data-preparation area.

- [ ] Write a failing cockpit test proving stock changes trigger the timeline loader and the chart appears before the decision summary.
- [ ] Run the focused cockpit test and confirm failure.
- [ ] Add abortable loading, per-symbol cache, explicit empty/error states, and responsive two-column/one-column layout.
- [ ] Re-run focused frontend tests and confirm they pass.

### Task 5: Full verification

**Files:**
- Verify all modified files.

- [ ] Run backend focused and full test suites plus Ruff.
- [ ] Run frontend focused and full test suites plus production build.
- [ ] Scan modified Chinese files for repeated question marks and common mojibake patterns.
- [ ] Inspect desktop and small-screen screenshots and confirm chart, event list, labels, and text do not overlap.
