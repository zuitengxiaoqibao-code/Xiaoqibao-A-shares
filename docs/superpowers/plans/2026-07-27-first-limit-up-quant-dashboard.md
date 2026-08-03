# First Limit-Up Quant Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real-data-first ECharts quantitative dashboard below the First Limit-Up navigation entry.

**Architecture:** Expose retained intraday polling snapshots through a read-only API. The React page composes the existing first-limit-up board, intraday ticks, and backtest result into four isolated panels; missing evidence remains explicitly unavailable.

**Tech Stack:** FastAPI, Pydantic, SQLite, React 19, TypeScript 5.8, ECharts 5, Vitest, Testing Library.

## Global Constraints

- A-share only; convertible bonds stay isolated.
- No broker connection, automatic order, simulated capital, or fabricated market data.
- Chinese source files remain UTF-8 and are edited with `apply_patch`.
- Desktop 2×2 layout; responsive double or single column on smaller screens.
- Respect reduced-motion preferences.

---

### Task 1: Intraday tick read API

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Test: `apps/api/tests/shangshu/test_intraday_monitor.py`
- Test: `apps/api/tests/routes/test_research.py`

- [ ] Write repository and route tests for symbol/date filtering, chronological order, cutoff enforcement, and missing repository behavior.
- [ ] Run the focused tests and verify they fail because the read API is absent.
- [ ] Add `PollStateRepository.intraday_snapshots(...)`, a dependency, and `GET /api/v1/a-shares/{symbol}/intraday-ticks`.
- [ ] Run focused tests and verify they pass.

### Task 2: Navigation and page contract

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Create: `apps/web/src/features/quant-analysis/types.ts`
- Create: `apps/web/src/features/quant-analysis/api.ts`
- Test: `apps/web/src/features/dashboard/Dashboard.test.tsx`

- [ ] Write a failing test for the nested navigation entry and `/first-limit-up/quant-analysis` route.
- [ ] Add the new view key, path mapping, loaders, and page mount point.
- [ ] Run the focused navigation test until green.

### Task 3: Four-quadrant ECharts dashboard

**Files:**
- Create: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Create: `apps/web/src/features/quant-analysis/QuantChart.tsx`
- Create: `apps/web/src/features/quant-analysis/metrics.ts`
- Create: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`
- Modify: `apps/web/package.json`

- [ ] Write failing tests for the four panels, seven signal rows, candidate switching, and honest unavailable states.
- [ ] Add ECharts and implement reusable lifecycle-safe chart rendering.
- [ ] Compute metrics only from first-limit-up evidence and backtest results.
- [ ] Run the focused dashboard tests until green.

### Task 4: Visual system and responsive behavior

**Files:**
- Modify: `apps/web/src/app/theme.css`

- [ ] Add scoped cyberpunk design tokens, four-quadrant layout, scanline, restrained glow, focus states, and reduced-motion rules.
- [ ] Add double-column and single-column responsive breakpoints.
- [ ] Run the dashboard tests and production build.

### Task 5: Final verification

- [ ] Run the full API test suite.
- [ ] Run the full web test suite.
- [ ] Run the web production build.
- [ ] Run mojibake scan and `git diff --check`.
