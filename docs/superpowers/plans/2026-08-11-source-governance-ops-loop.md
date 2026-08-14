# Source Governance and Operations Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Turn the previously accepted recommendations into a durable operations loop that makes every data source, refresh, quantitative result, and portable release measurable and understandable.

**Architecture:** Reuse the existing FastAPI source-health repository, local TDX/DuckDB adapters, React settings page, date-scoped quant snapshots, and portable EXE scripts. Add only focused contracts and panels where an existing endpoint already provides real evidence; do not invent data or add a second data pipeline.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite operations log, React + TypeScript, Vitest, pytest, Vite/PyInstaller portable EXE.

## Global Constraints

- The Windows EXE remains the only user-facing delivery entry point.
- Local TDX/DuckDB data is preferred; unavailable fields remain unavailable with a reason.
- Red means A-share rise/improvement/inflow; green means fall/deterioration/outflow.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` during rebuilds.
- Never close, restart, or control the user's TongdaXin process.
- Every behavior change starts with a failing test and ends with targeted plus full verification.

---

### Task 1: Expose Source Health in Data Settings

**Files:**
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Create: `apps/web/src/features/data-settings/SourceHealthPanel.tsx`
- Create: `apps/web/src/features/data-settings/SourceHealthPanel.test.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`

**Interfaces:**
- Consumes existing `SourceHealthLoader` and `SourceHealthResponse` from `features/data-settings/types.ts`.
- Produces a compact source matrix showing source, operation, target, status, success rate, latest latency, latest trade date, validation, and last error code.

- [x] Write a failing component test for ready/degraded/unavailable rows and empty-source state.
- [x] Run the focused Vitest test and confirm it fails because the panel is not rendered.
- [x] Implement the panel with stable columns, readable type, explicit `--` values, and red/green semantic status colors.
- [x] Render it in `DataSettingsView` when `loadSourceHealth` is supplied; load once on mount and provide an explicit refresh action.
- [x] Run the focused Vitest tests and the full web suite.

### Task 2: Startup and Refresh Diagnostics

**Files:**
- Modify: `apps/api/src/qibao_desktop/startup_progress.py`
- Modify: `apps/api/tests/desktop/test_startup_progress.py`
- Modify: `apps/api/src/qibao_desktop/window.py`
- Modify: `apps/api/tests/desktop/test_window.py`

**Interfaces:**
- The existing desktop startup shell consumes verified startup progress events and displays stage elapsed milliseconds without blocking navigation.
- Startup progress remains monotonic and records elapsed milliseconds for each logged milestone.

- [x] Add failing tests for logged milestone elapsed milliseconds and failed-stage reason.
- [x] Keep the existing startup shell as a non-blocking status element; do not remount the active workspace during updates.
- [x] Add milestone timing fields to the existing startup progress record without changing the EXE launch contract.
- [x] Verify startup timing output through the portable smoke script.

### Task 3: Quantitative Result Governance

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/backtest.py`
- Modify: `apps/api/src/qibao_api/zhongshu/backtest.py`
- Modify: `apps/api/tests/zhongshu/test_backtest.py`
- Modify: `apps/web/src/features/backtest/BacktestPanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`

**Interfaces:**
- Backtest responses expose `sample_policy`, `in_sample`, `validation`, `out_of_sample`, and `lookahead_check` as structured evidence.
- Metrics remain unavailable until the declared closed-trade minimum is met.

- [x] Add failing tests for minimum-sample gating and look-ahead rejection.
- [x] Persist an immutable request snapshot and source-bar count with each result.
- [x] Render explicit “样本不足/样本外未通过/可观察” labels beside the metrics.
- [x] Verify no future-bar data enters signal-day calculations through next-open execution tests and the explicit lookahead check.

### Task 4: Release Diagnostics and Acceptance

**Files:**
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/build-portable.ps1`
- Create: `docs/verification/2026-08-11-source-governance-ops-loop.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

**Interfaces:**
- Smoke output records source health status, startup milestones, quant candidate retention, EXE hash, and process boundaries.

- [x] Add smoke assertions for source-health response shape and persistent directory preservation.
- [x] Rebuild the portable EXE and run the release-data smoke plus eight-request refresh probe.
- [x] Run API/web full suites, production build, UTF-8 scan, vault validation, and `git diff --check`.
- [x] Record confirmed results and residual unavailable sources in the verification document and project memory.
