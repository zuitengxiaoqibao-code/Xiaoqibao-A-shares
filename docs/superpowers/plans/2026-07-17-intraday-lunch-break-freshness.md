# Intraday Lunch-Break Freshness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the last valid morning-session quote usable during the A-share lunch break without weakening the normal 180-second intraday freshness gate.

**Architecture:** Add one deterministic freshness helper to `DeterministicIntradayEvaluator`. It accepts ordinary quotes up to 180 seconds old, and during 11:30-13:00 China time also accepts same-day quotes observed no earlier than 11:27; all advice calculations and stored quantitative precision remain unchanged.

**Tech Stack:** Python 3.12, Pydantic, pytest.

## Global Constraints

- A shares remain separate from convertible bonds.
- Missing or genuinely stale quotes must produce an explicit blocked result.
- AI must not alter deterministic evidence or actions.
- Chinese source text must be edited with `apply_patch`, then scanned as strict UTF-8 and checked for mojibake.
- Do not commit or push the dirty worktree.

---

### Task 1: Lunch-Break Quote Freshness

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/decision_runtime.py`
- Test: `apps/api/tests/shangshu/test_decision_runtime.py`

**Interfaces:**
- Consumes: `MarketFeedSnapshot.observed_at`, `IntradayEvaluationContext.now`, `CHINA_TZ`.
- Produces: `DeterministicIntradayEvaluator._quote_is_fresh(quote, now) -> bool`.

- [ ] **Step 1: Write the failing tests**

Add a parametrized evaluator test with a quote observed at 11:30 China time. Assert `ready` at 11:40, and assert `blocked` when the quote is from 11:26 or when evaluation occurs at 13:00.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\shangshu\test_decision_runtime.py -q`

Expected: the 11:40 case fails with `status == "blocked"` before implementation.

- [ ] **Step 3: Implement the minimal freshness helper**

Use the normal age rule first. For 11:30 <= local time < 13:00, require the quote to be from the same China-local date and observed at or after 11:27. Replace the inline 180-second expression with this helper.

- [ ] **Step 4: Run focused and complete verification**

Run the decision runtime and intraday monitor tests, then all backend tests, Ruff, frontend tests, production build, strict UTF-8/mojibake scans, and `git diff --check`.

- [ ] **Step 5: Verify the production path**

Restart the API, run the real intraday manual job, refresh the `600519` cockpit, and verify a current two-decimal intraday explanation, stable 6/6 and 9/9 coverage, and no browser console errors.

### Task 2: Persist Recovery Without Advice Churn

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Test: `apps/api/tests/shangshu/test_intraday_monitor.py`

**Interfaces:**
- Consumes: the latest stored cycle status and a new `IntradayEvaluationResult`.
- Produces: an empty-delta `ready` cycle when a prior `blocked` or `partial` cycle recovers without semantic advice changes.

- [ ] **Step 1: Reproduce the blocked-to-ready loss**

Persist a blocked cycle, then evaluate an unchanged ready advice result. Assert that a second ready cycle exists with no delta advice.

- [ ] **Step 2: Preserve the recovery transition**

Bypass the unchanged-advice early return only when the latest cycle is not ready and the new result is ready. Keep ready-to-ready quote-only updates deduplicated.

- [ ] **Step 3: Run focused monitor tests**

Run: `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\shangshu\test_intraday_monitor.py -q`

Expected: all monitor tests pass.

### Task 3: Render Legacy Intraday Text From Structured Values

**Files:**
- Create: `apps/web/src/features/decision-workbench/explanation.ts`
- Test: `apps/web/src/features/decision-workbench/explanation.test.ts`
- Modify: `apps/web/src/features/stock-cockpit/PhaseTimeline.tsx`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.tsx`
- Modify: `apps/web/src/features/beginner-shell/HistoryReview.tsx`

**Interfaces:**
- Consumes: frozen `Advice.quantitative_result.price` and `change_percent`.
- Produces: `beginnerAdviceExplanation(advice, phase) -> string | null`.

- [ ] **Step 1: Reproduce the legacy long-decimal display**

Use a frozen intraday advice with a high-precision percentage and assert a two-decimal human-facing sentence while retaining the original structured value.

- [ ] **Step 2: Add the shared presentation helper**

Rebuild text only for the intraday phase when both structured values are valid. Preserve recorded text for premarket, postclose, and incomplete legacy records.

- [ ] **Step 3: Use the helper in every beginner decision view**

Apply it to the stock phase timeline, current decision workbench, and history review.

- [ ] **Step 4: Run focused and full frontend verification**

Run focused tests for the helper and three consumers, then all web tests and the production build.
