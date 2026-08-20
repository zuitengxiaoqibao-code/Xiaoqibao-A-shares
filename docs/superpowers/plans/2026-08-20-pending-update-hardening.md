# Pending Update Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Prevent the portable EXE from showing an unhandled update exception when old multiprocessing children still hold the release executable, while preserving the pending update for a safe retry.

**Architecture:** The desktop entrypoint will identify executable processes that belong to the current release directory, wait for them to exit after the parent handoff, and use a bounded retry loop for replacement. Update application failures will be caught at the helper boundary, written to the release log in Chinese, and leave `pending-update.json` intact so the next launch can retry. The existing transactional file replacement and rollback in `PendingUpdate.apply()` remains the source of truth for file safety.

**Tech Stack:** Python 3.12, pytest, pathlib, Windows `tasklist`/PowerShell-compatible process inspection, PyInstaller portable EXE.

## Global Constraints

- Windows EXE remains the only user-facing delivery entry point.
- Do not close, restart, or control 通达信; do not control the mouse or desktop.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` during rebuilds.
- Chinese source files must be edited with UTF-8-safe patches and scanned for mojibake.
- No simulated market data or fake update success may be introduced.

### Task 1: Reproduce the stale-child update failure

**Files:**
- Modify: `apps/api/tests/desktop/test_entrypoint.py`
- Test helper behavior through `apps/api/src/qibao_desktop/entrypoint.py`

- [ ] Add a failing test that simulates the parent PID exiting while a same-release child process remains alive, and asserts the helper waits for the child before invoking `PendingUpdate.apply()`.
- [ ] Add a failing test that makes `load_pending_update()` or `apply()` raise and asserts `_run_update_helper()` returns a nonzero code, keeps the manifest, and logs a Chinese error instead of propagating an exception.
- [ ] Run the focused tests and verify they fail for the missing behavior.

### Task 2: Implement safe helper behavior

**Files:**
- Modify: `apps/api/src/qibao_desktop/entrypoint.py`
- Modify: `apps/api/src/qibao_desktop/pending_update.py` only if rollback cleanup needs a narrowly scoped hardening change.

- [ ] Add an injectable process-inspection helper that returns PIDs whose executable path is inside the target release directory, excluding the helper PID and current parent PID.
- [ ] Wait up to the existing bounded deadline for both the parent PID and same-directory residual children, polling every 100 ms.
- [ ] Catch update validation, replacement, launch, and manifest-removal errors at the helper boundary; write a Chinese log message with the manifest path and error type; return a stable nonzero code while leaving the manifest for retry.
- [ ] Keep transactional rollback behavior and launch the target only after a successful apply and manifest removal.
- [ ] Run the focused tests and verify they pass.

### Task 3: Regression and quality verification

**Files:**
- Modify: `apps/api/tests/desktop/test_entrypoint.py` if coverage reveals an uncovered branch.

- [ ] Run all desktop tests and the full API test suite.
- [ ] Run Ruff, Web tests/build, UTF-8/mojibake scan, and `git diff --check`.
- [ ] Record any real-data performance warnings without relabeling them as passes.

### Task 4: Portable EXE delivery verification

**Files:**
- Use: `scripts/build-portable.ps1`
- Use: `scripts/run-portable-smoke.ps1`

- [ ] Rebuild the portable EXE from the current worktree.
- [ ] Preserve all eight persistent directories and verify the release manifest hash.
- [ ] Run isolated smoke and, where bounded, release-data smoke; do not terminate unrelated processes.
- [ ] Confirm the EXE launches and the update helper failure path no longer produces an unhandled exception.

### Task 5: Project memory update

**Files:**
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`
- Modify: `D:/Users/90090/Documents/知识库/04-每日记录/2026/2026-08-20.md`

- [ ] Record confirmed root cause, fix, test evidence, EXE hash/path, and any partial real-data boundaries without credentials.
- [ ] Run vault validation, mojibake scan, and Git diff check.
