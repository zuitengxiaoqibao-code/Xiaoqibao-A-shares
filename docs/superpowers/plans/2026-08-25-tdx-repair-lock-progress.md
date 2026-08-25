# TDX Full Repair Lock and Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep one-click full repair truthful and live after local TDX scanning, including database-lock recovery and a visible completed-scan/waiting phase.

**Architecture:** The local importer emits a final scan-boundary event before any database watermark query. The official package service persists that boundary as a distinct waiting stage, retries transient local database reads with bounded exponential backoff, and finishes as partial with preserved scan evidence when the lock does not clear. The UI maps the new stage to Chinese copy and displays the scan totals instead of leaving the job at 5%.

**Tech Stack:** Python, Pydantic contracts, pytest, React/TypeScript, Vitest, Vite, PyInstaller portable EXE.

## Global Constraints

- Do not close, restart, or control the user's running TongdaXin or EXE.
- Preserve existing uncommitted changes and persistent data directories.
- Chinese source files must be edited with `apply_patch` and checked for mojibake.
- Production changes require a failing regression test first.
- Final delivery is the Windows EXE; run API/Web tests, portable build, and EXE smoke.

### Task 1: Emit a scan-boundary event

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`

- [ ] Add a test asserting `discovery_progress` receives a final event with `phase="scan_complete"`, all candidate counts, and no current file before `latest_dates` is called.
- [ ] Run that test and verify it fails because no boundary event exists.
- [ ] Emit progress for every candidate and one explicit boundary event before the incremental watermark lookup.
- [ ] Run the focused importer tests and verify they pass.

### Task 2: Make database watermark reads recoverable

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_official_package.py`
- Modify: `apps/api/src/qibao_api/contracts/history_supplement.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`
- Test: `apps/api/tests/gongbu/test_tdx_official_package.py`

- [ ] Add a failing test for a transient `UnicodeDecodeError`/`OSError` database read that succeeds on a later attempt and emits waiting progress.
- [ ] Add a failing test for a persistent lock that returns a partial job with preserved `9497/9497` scan evidence and a Chinese actionable reason.
- [ ] Implement bounded retry with short exponential backoff and a `waiting_database` stage; do not swallow unrelated errors.
- [ ] Persist `stage="waiting_database"`, current scan totals, and “本机日线扫描已完成，正在等待本地行情数据库释放并自动重试”.
- [ ] On exhausted retries, return a partial repair result rather than falsely reporting a 5% failed scan; keep official/source evidence intact.
- [ ] Run focused tests and verify green.

### Task 3: Present the live stage clearly

**Files:**
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Test: `apps/web/src/features/operations/OperationsView.test.tsx`

- [ ] Add a failing UI test for the new stage label and completed scan detail.
- [ ] Map `waiting_database` to “等待本地数据库释放” and render scan completion counts/current phase without a false “正在扫描” label.
- [ ] Run the focused Vitest test and verify green.

### Task 4: Full verification and delivery

- [ ] Run API focused tests, then the full API suite.
- [ ] Run full Web Vitest and production build.
- [ ] Run UTF-8/mojibake scan and `git diff --check`.
- [ ] Run `scripts/build-portable.ps1` and `scripts/run-portable-smoke.ps1` against the staged EXE.
- [ ] Confirm no new `xiaoqibao.exe` residue and do not alter the user's running processes.
