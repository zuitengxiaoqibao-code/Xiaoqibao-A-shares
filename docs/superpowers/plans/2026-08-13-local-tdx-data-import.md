# Local TDX Data Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a truthful, resumable local TongdaXin daily-data import workflow that scans `vipdoc` and supported archives, validates and deduplicates records into the existing `market.duckdb`, exposes real progress and source evidence, and refreshes market watermarks after import.

**Architecture:** Reuse the existing `TdxLocalDailyBar` parser and `BarRepository`. A new import service owns discovery, archive extraction into a temporary directory, validation, append-only deduplicated writes, and an import ledger. The existing full-market history service remains the network backfill path; the UI shows local import and network repair as separate stages.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, DuckDB, React + TypeScript.

## Global Constraints

- Preserve existing `market.duckdb`; never replace it with a partial import.
- Prefer local TongdaXin data; never overwrite a verified local row with a network row.
- Do not close, restart, or control the TongdaXin desktop process.
- Every imported row records a truthful source label and every failure is visible.
- Existing routes and the portable EXE remain the user-facing delivery path.
- Chinese files remain UTF-8 and must pass the project mojibake scan.

### Task 1: Import contracts and ledger

**Files:**
- Create: `apps/api/src/qibao_api/contracts/tdx_import.py`
- Create: `apps/api/src/qibao_api/gongbu/tdx_import_repository.py`
- Test: `apps/api/tests/gongbu/test_tdx_import_repository.py`

- [ ] Define scan, file, job, and error models with source, counts, progress, and timestamps.
- [ ] Persist append-only job state in `data/tdx-import.sqlite3`.
- [ ] Test create/update/finish and restart recovery.

### Task 2: Local scanner and safe importer

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Modify: `apps/api/src/qibao_api/storage/bar_repository.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`

- [ ] Scan `sh/sz/bj/lday/*.day` and `.zip` archives containing valid `.day` files.
- [ ] Validate record size, date, OHLC range, positive prices, and A-share symbol format.
- [ ] Append only missing `(symbol, trade_date)` rows; local source outranks network source.
- [ ] Keep temporary extraction isolated and delete it after the run.
- [ ] Test malformed files, duplicate rows, archive import, and cancellation.

### Task 3: API and settings wiring

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/api/src/qibao_api/contracts/history_sync.py`
- Test: `apps/api/tests/routes/test_data.py`

- [ ] Add scan/start/current/pause/resume endpoints for local import.
- [ ] Add configurable archive directories while retaining current local-source settings.
- [ ] Return explicit stage, current file, counts, source, latest date, and blockers.

### Task 4: UI operations and data settings

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Test: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Test: `apps/web/src/features/operations/OperationsView.test.tsx`

- [ ] Add “扫描本地数据”“导入本地增量” controls.
- [ ] Show real progress stages, last completed time, source composition, and failure details.
- [ ] Keep old snapshot visible while import is running; refresh watermarks only after commit.

### Task 5: Rebuild and verification

- [ ] Run focused API/Web tests, full API/Web suites, UTF-8/mojibake scan, and production build.
- [ ] Run `scripts/build-portable.ps1`.
- [ ] Run `scripts/run-portable-smoke.ps1` against the rebuilt EXE.
- [ ] Verify persistent directories remain intact and TongdaXin process/listener is unchanged.

