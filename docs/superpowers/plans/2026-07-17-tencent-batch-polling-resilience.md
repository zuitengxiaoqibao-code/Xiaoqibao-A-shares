# Tencent Batch Polling Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce transient A-share intraday polling failures without allowing incomplete quote batches to appear successful, and explain relevant failures in beginner-readable Chinese.

**Architecture:** Replace per-symbol Tencent requests with one batch request followed by one targeted retry for missing or invalid symbols. Preserve all-or-nothing scope success, persist focus/universe error codes independently, expose them through the decisions API, and render only the live scope relevant to the current view.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, httpx, pytest, React 19, TypeScript 5, Vitest, Testing Library.

## Global Constraints

- A 股 remains primary and convertible bonds remain isolated.
- Do not add accounts, funds, positions, orders, broker connectivity, or automatic trading.
- Missing quotes remain explicit; never fabricate zeroes or mark a partial universe successful.
- AI may explain frozen deterministic evidence but cannot change results, numbers, confidence, attribution, or risk gates.
- Polling health changes must not create decision versions.
- Edit Chinese files with `apply_patch`, then run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree and do not commit, stage, push, reset, or revert unrelated changes.

---

### Task 1: Lock Batch Fetch Completeness

**Files:**
- Modify: `apps/api/tests/shangshu/test_decision_runtime.py`
- Modify: `apps/api/src/qibao_api/shangshu/decision_runtime.py`

**Interfaces:**
- Consumes: unique A-share symbols, optional cutoff, Tencent GBK response.
- Produces: complete ordered `MarketFeedSnapshot` tuple or a typed failure.

- [x] **Step 1: Write failing batch and targeted-retry tests**

Cover one request for two symbols, response statement parsing, original-order output, a first response missing one symbol followed by a one-symbol retry, persistent missing data, empty input and strict validation.

- [x] **Step 2: Run focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/shangshu/test_decision_runtime.py -q`

Expected: batch URL, targeted retry and completeness assertions fail against the per-symbol implementation.

- [x] **Step 3: Implement batch parsing and one targeted retry**

Add a small typed incomplete-batch exception and private request/parse helpers. Preserve compliance checks, cutoff checks, strict GBK decoding and requested order.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/shangshu/test_decision_runtime.py -q`

Expected: all focused tests pass.

### Task 2: Persist Scope-Specific Failure Reasons

**Files:**
- Modify: `apps/api/tests/shangshu/test_intraday_monitor.py`
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`

**Interfaces:**
- Consumes: polling scope and raised exception.
- Produces: independent focus/universe failure counts and error codes.

- [x] **Step 1: Write failing state-transition tests**

Fail focus and universe with different exception classes, recover one range, and assert the other range remains degraded with its original code.

- [x] **Step 2: Run focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/shangshu/test_intraday_monitor.py -q`

Expected: new scope error fields are absent or overwritten.

- [x] **Step 3: Add fields and transition semantics**

Retain `last_error_code` for persisted-state compatibility. Failure updates only its scope field; success clears only its scope field and derives global mode from the other failure count.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/shangshu/test_intraday_monitor.py -q`

Expected: all focused tests pass.

### Task 3: Expose and Explain Relevant Polling Health

**Files:**
- Modify: `apps/api/tests/routes/test_decisions.py`
- Modify: `apps/api/src/qibao_api/routes/decisions.py`
- Modify: `apps/web/src/features/decision-workbench/types.ts`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.test.tsx`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: persisted focus/universe error fields and selected-symbol scope.
- Produces: stable API fields and beginner-readable live-scope status.

- [x] **Step 1: Write failing API and component tests**

Assert both API fields, relevant-scope Chinese failure text, continuous failure count, known error explanation and suppression of the unrelated scope.

- [x] **Step 2: Run focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_decisions.py -q`

Run: `pnpm --filter @qibao/web test -- DecisionWorkbench.test.tsx`

Expected: scope error fields and readable status are missing.

- [x] **Step 3: Implement the API contract and UI mapping**

Always serialize both nullable fields. In live intraday, select focus for a chosen symbol and universe otherwise. Show a compact warning only for relevant failures and replace raw English polling mode in the rail.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the two focused commands above.

Expected: all focused tests pass.

### Task 4: Production Verification

**Files:**
- Modify: `docs/roadmap.md`
- Verify: all changed files and running application.

- [x] **Step 1: Run full automated checks**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests -q`

Run: `.venv\Scripts\python.exe -m ruff check apps/api/src apps/api/tests`

Run: `pnpm --filter @qibao/web test`

Run: `pnpm --filter @qibao/web build`

- [x] **Step 2: Run encoding and diff gates**

Strictly decode changed text files as UTF-8, scan source files for repeated question marks, replacement characters and common mojibake markers, then run `git diff --check`.

- [x] **Step 3: Verify real API and browser behavior**

Confirm the running poll state, batch request recovery, relevant-scope copy, no fabricated advice, no console errors, no dialogs and no page-level overflow at desktop and 390x844.

- [x] **Step 4: Update roadmap and verification record**

Record exact test counts and runtime evidence. Do not claim completion until every gate passes.

## Verification Record

- Focused regression: decision runtime 34 passed; intraday monitor 33 passed; decisions API 15 passed; decision workbench 17 passed.
- Full regression: API 734 passed and 1 skipped; Web 155 passed; Ruff and the production build passed.
- Encoding and diff gates: 105 changed text files decoded as strict UTF-8; 270 source files passed the mojibake scan; `git diff --check` passed.
- Live API: `current_phase=postclose`, `market_session=closed`; both scope error fields were present and null. The persisted legacy state remained `degraded` with one focus failure and no attributable historical scope error code, so the UI did not guess or surface it as a current live fault.
- Browser: desktop 1280x720 and mobile 390x844 had no page-level horizontal overflow, console errors or dialogs. The selected-stock page loaded verified quotes, an observation action, evidence and risks without prices, positions or order instructions. Live-scope error copy and targeted retry remain covered by the focused regression fixtures because the real market was closed during verification.
