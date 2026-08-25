# TDX Local Scan Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local TongdaXin daily-bar scan visibly progress through the existing repair job, with truthful counters and a highlighted active stage.

**Architecture:** Extend the existing TDX import job contract and repository updates with scan-specific counters and a progress callback. The official repair runner forwards those updates through its existing persisted job state, and the Operations view renders the current stage with a high-contrast active treatment plus scan details. No new polling endpoint, data source, or parallel scan is introduced.

**Tech Stack:** Python, Pydantic contracts, pytest, React/TypeScript, Vitest, existing task polling, PowerShell portable build scripts.

## Global Constraints

- The Windows desktop executable is the only user-facing delivery entry point.
- Use the existing task polling/SSE path; do not add an independent polling loop.
- Percentages must be truthful; when a total is unavailable, show counts and do not fabricate a percentage.
- Chinese source files must be edited with `apply_patch`, remain UTF-8, and pass mojibake scanning.
- Do not control, close, or modify TongdaXin; do not delete user data.

### Task 1: Extend scan progress contracts and service callback

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/history_supplement.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`

**Interfaces:**
- `HistorySupplementJob` gains additive scan counters and current-file evidence.
- `TdxLocalImportService.import_now(paths, discovery_progress=None)` accepts `Callable[[dict], None]` and emits updates while reading each discovered daily file.

- [x] **Step 1: Write the failing test**

Add a test that creates two `.day` files, calls `scan(..., progress=events.append)`, and asserts the callback contains increasing `scanned_files`, a current filename, discovered/readable counters, and a final scan result.

- [x] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/gongbu/test_tdx_local_import.py -k scan_progress -v`

Expected: FAIL because `scan` does not accept a progress callback and the contract has no scan counters.

- [x] **Step 3: Write minimal implementation**

Add optional scan fields with safe defaults. Count files in each candidate directory before processing when possible; otherwise use `None` for the total. Emit a progress dictionary after each `.day` candidate with `scanned_files`, `total_scan_files`, `day_files`, `readable_files`, `current_file`, `scan_speed`, and `scan_eta_seconds`.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/gongbu/test_tdx_local_import.py -k scan_progress -v`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/contracts/tdx_import.py apps/api/src/qibao_api/gongbu/tdx_local_import.py apps/api/tests/gongbu/test_tdx_local_import.py
git commit -m "feat: expose truthful TDX scan progress"
```

### Task 2: Forward scan evidence through the official repair job

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_official_package.py`
- Modify: `apps/api/src/qibao_api/contracts/history_supplement.py` (only if the existing job contract lacks fields)
- Test: `apps/api/tests/gongbu/test_tdx_official_package.py`

**Interfaces:**
- The existing `HistorySupplementJob` state exposes scan counters through additive optional fields or a `scan_detail` object.
- `OfficialTdxPackageService.run()` passes a scan callback into `TdxLocalImportService.scan` or the equivalent local import phase and updates the persisted job without changing the endpoint.

- [x] **Step 1: Write the failing test**

Use a fake local import service that emits two scan updates and assert `run()` persists the latest scan counters, current file, and a Chinese detail such as “已扫描 2 个文件，发现 2 个日线文件”.

- [x] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/gongbu/test_tdx_official_package.py -k local_scan_progress -v`

Expected: FAIL because the runner currently calls local import without forwarding scan evidence.

- [x] **Step 3: Write minimal implementation**

Add a local scan progress callback that updates the existing job state at the `scanning` stage, keeps the base stage percentage truthful when total is known, and stores count-only detail when total is unknown. Preserve the existing import callback and failure handling.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/gongbu/test_tdx_official_package.py -k local_scan_progress -v`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/gongbu/tdx_official_package.py apps/api/src/qibao_api/contracts/history_supplement.py apps/api/tests/gongbu/test_tdx_official_package.py
git commit -m "feat: persist local TDX scan evidence"
```

### Task 3: Render active repair stage and scan details

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/operations/OperationsView.test.tsx`

**Interfaces:**
- The view consumes additive scan fields and renders a `data-state="active"` stage card while a repair is running.

- [x] **Step 1: Write the failing test**

Render a running repair job at the scanning stage and assert the screen contains the highlighted active stage, “正在扫描本机通达信日线”, the scanned/total count, the latest filename, and no fixed “4.00%” when a truthful scan percentage is unavailable.

- [x] **Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test OperationsView.test.tsx -t "scan progress"`

Expected: FAIL because the current view only renders a plain progress bar and fixed stage text.

- [x] **Step 3: Write minimal implementation**

Add a compact scan detail row and active-stage class with a bright accent, subtle breathing border, and animated progress sheen. Keep completed/failed/pending states distinct, use Chinese labels, and retain the previous cached content while the task is running.

- [x] **Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test OperationsView.test.tsx -t "scan progress"`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/web/src/features/operations/types.ts apps/web/src/features/operations/OperationsView.tsx apps/web/src/features/operations/OperationsView.css apps/web/src/features/operations/OperationsView.test.tsx
git commit -m "feat: highlight active data repair progress"
```

### Task 4: Regression verification and Windows delivery

**Files:**
- Modify only if required by build/test failures.

- [x] **Step 1: Run focused API and Web tests**

Run: `pytest apps/api/tests/gongbu/test_tdx_local_import.py apps/api/tests/gongbu/test_tdx_official_package.py -v` and `pnpm --dir apps/web test OperationsView.test.tsx`.

- [x] **Step 2: Run full checks**

Run `git diff --check`, UTF-8/mojibake scans, full API tests, and full Web tests.

- [x] **Step 3: Rebuild the portable EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1` and preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups`.

- [x] **Step 4: Smoke-test the actual EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1 -ExePath dist/XiaoQiBao-Portable/xiaoqibao.exe` and verify launch, repair progress endpoint, and zero residual `xiaoqibao.exe` processes after exit.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-08-25-tdx-scan-progress-design.md
git commit -m "docs: plan truthful TDX scan progress"
```

## Self-Review

- Spec coverage: truthful scan counters, existing task transport, active-stage highlighting, completion/failure detail, regression tests, and EXE verification are all assigned above.
- Placeholder scan: no TBD/TODO or unspecified implementation step is used.
- Type consistency: callback fields and job state are additive; the view consumes the same names emitted by the runner.
