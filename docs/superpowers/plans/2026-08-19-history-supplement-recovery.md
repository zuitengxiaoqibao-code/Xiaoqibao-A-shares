# Historical Data Supplement Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make historical A-share supplementation recoverable, truthful, observable, and usable from the Data and Operations Center, then prove that the packaged EXE advances its real market-data date.

**Architecture:** Keep the live TongdaXin installation read-only. Import only supported A-share `.day` files into app-owned storage, download the official full daily package into an app-owned cache with integrity checks, and use the existing full-market sync only for remaining gaps. Background jobs expose real stage, byte/file progress, failure reasons, and audit metadata.

**Tech Stack:** FastAPI, Pydantic, SQLite, DuckDB/Parquet, httpx, React, TypeScript, Vitest, Pytest, Windows portable EXE packaging.

## Global Constraints

- Never fabricate bars, dates, symbols, coverage, progress, or ready states.
- Never write into or control the user's running TongdaXin installation.
- Preserve existing uncommitted global-freshness changes.
- Use `apply_patch` for Chinese source edits and verify UTF-8/mojibake afterward.
- Rebuild with `scripts/build-portable.ps1` and smoke with `scripts/run-portable-smoke.ps1 -UseReleaseData`.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups`.

---

### Task 1: Make local TDX import non-blocking and recoverable

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_import_repository.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`
- Test: `apps/api/tests/gongbu/test_tdx_import_repository.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: A job that skips unsupported ETF/benchmark files, records per-file errors, continues with valid A shares, and resumes orphaned queued/running work once after restart.

- [x] Write regression tests for unsupported files, corrupt files, repository failures, and orphan recovery.
- [x] Run focused tests and confirm the expected failures.
- [x] Filter with the repository's supported A-share validator and catch errors inside the per-file loop.
- [x] Record Chinese-safe errors without paths or secrets beyond the affected local file.
- [x] Recover pending/running imports and submit the current pending job exactly once at startup.
- [x] Run focused tests and confirm they pass.

### Task 2: Make failed full-market history symbols retryable

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/history_sync_repository.py`
- Modify: `apps/api/src/qibao_api/gongbu/full_market_history.py`
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Modify: `apps/api/src/qibao_api/contracts/history_sync.py`
- Test: `apps/api/tests/gongbu/test_history_sync_repository.py`
- Test: `apps/api/tests/routes/test_data.py`

**Interfaces:**
- Produces: `retry_failed(job_id)` that preserves ready items, requeues failed/pending items, increments attempt evidence, and allows a current-date repair to supersede a stale paused task without deleting audit history.

- [x] Write failing repository and route tests.
- [x] Run them and confirm failure is caused by missing retry behavior.
- [x] Add attempt-safe retry state and stale-task supersession.
- [x] Expose explicit retry and current-date restart routes.
- [x] Run focused tests and confirm they pass.

### Task 3: Add official TongdaXin package supplementation

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_official_package.py`
- Create: `apps/api/src/qibao_api/contracts/history_supplement.py`
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/gongbu/test_tdx_official_package.py`
- Test: `apps/api/tests/routes/test_data.py`

**Interfaces:**
- Consumes: `https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js` and `https://data.tdx.com.cn/vipdoc/hsjday.zip`.
- Produces: background supplement job with byte progress, SHA-256, package date, validated `.day` count, import result, and exact Chinese failure stage.

- [x] Write fake-transport tests for metadata, streaming, ZIP integrity, ZIP-slip rejection, `.day` validation, and atomic `.part` rename.
- [x] Run tests and confirm expected failures.
- [x] Implement app-owned download/cache and validation service with bounded retry/timeouts.
- [x] Chain validated ZIP import and remaining-gap repair without writing to TongdaXin.
- [x] Expose diagnostics/start/current endpoints.
- [x] Run focused tests and confirm they pass.

### Task 4: Add the Data and Operations supplement center

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Produces: one settings panel showing expected/current dates, dominant coverage, local TDX date, official package state, current job progress, failed/pending counts, and Chinese failure causes; actions are diagnose, official supplement, retry failures, pause, and resume.

- [x] Write failing component tests for truthful stale state, real progress, action wiring, and failure details.
- [x] Run tests and confirm expected failures.
- [x] Implement the panel in Data and Operations using existing dashboard props plus supplement APIs; remove the former Data Settings rendering.
- [x] Poll only while a job is active and preserve the last complete state while refreshing.
- [x] Add responsive styles with readable font sizes and red-up/green-down semantics only for market values.
- [x] Run focused tests and confirm they pass.

### Task 5: Verify, package, and advance real data

**Files:**
- Create: `docs/verification/2026-08-19-history-supplement-recovery.md`
- Update: `docs/superpowers/plans/2026-08-19-history-supplement-recovery.md`

**Interfaces:**
- Produces: fresh test/build/smoke evidence and before/after production data coverage with source URL, hash, timestamps, and errors.

- [x] Run focused and full API/Web tests, Ruff, TypeScript build, UTF-8/mojibake scan, and `git diff --check`.
- [x] Rebuild the portable EXE while preserving all eight persistent directories.
- [x] Run isolated smoke and release-data smoke without controlling TongdaXin or the desktop.
- [x] Trigger the official package supplement through the rebuilt EXE/API.
- [x] Verify the actual dominant trade date, target-date coverage, first-limit-up scan date, and audit evidence advance.
- [x] If the official source blocks or lacks a current package, record the exact external blocker and keep the product state partial/stale.
- [x] Update verification evidence and durable project memory using the redaction protocol.

## Completion Evidence

Implementation and real-data verification completed on 2026-08-19. Detailed evidence is recorded in `docs/verification/2026-08-19-history-supplement-recovery.md`.
