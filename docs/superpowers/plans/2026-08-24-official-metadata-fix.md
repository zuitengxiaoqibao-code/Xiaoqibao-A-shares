# Official TDX Metadata Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the portable EXE reads the current official TongdaXin metadata without the stale UTF-8 response error.

**Architecture:** Keep the official endpoint as a byte response, decode UTF-8-SIG/GB18030/GBK in the API service, and verify the exact vendor JavaScript payload with a regression test. Rebuild the portable EXE while preserving all persistent directories, then run the real EXE smoke check.

**Tech Stack:** Python, httpx, pytest, React/Vite, PyInstaller, PowerShell.

## Global Constraints

- Do not delete or overwrite user data directories.
- Do not close, restart, or control the user's TongdaXin process.
- Keep user-facing errors in Chinese.
- Deliver the Windows EXE as the review entry point.

### Task 1: Vendor Metadata Regression

**Files:**
- Modify: `apps/api/tests/gongbu/test_tdx_official_package.py`
- Verify: `apps/api/src/qibao_api/gongbu/tdx_official_package.py`

- [x] Add a test using the exact current `window.HSJDAY_SOFT_SIZE` and `window.HSJDAY_SOFT_TIME` response.
- [x] Run the focused API test and confirm the current decoder parses it.

### Task 2: Portable Release Verification

**Files:**
- Build: `scripts/build-portable.ps1`
- Verify: `scripts/run-portable-smoke.ps1`

- [x] Run the complete API/Web checks through the normal build.
- [x] Build without `-SkipPersistentData` so `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` are preserved.
- [x] Run the actual rebuilt EXE smoke test and record the EXE hash.

**Verification:** API `1704 passed, 1 skipped`; Web `134` files / `779 passed`; desktop server regression `8 passed`; production build and 14-menu EXE smoke passed. Final EXE SHA-256 after shutdown fix: `1033CB2C35E1DCBE3DA8C4504F34DC379467E73191A3ECAD79CAC06EFDE3438`.
