# Intraday Block Reasons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist deterministic intraday block reasons and explain them on the beginner A-share timeline without fabricating or replacing advice.

**Architecture:** The evaluator owns stable reason codes, the monitor persists and hashes them, and the frontend translates the frozen codes. The existing advice materialization remains unchanged so old verified advice is preserved while the current blocked state is explicit.

**Tech Stack:** Python 3.12, Pydantic, pytest, React 19, TypeScript 5.8, Vitest, Testing Library.

## Global Constraints

- Do not relax quote, risk, or compliance gates.
- Do not change actions, confidence, quantitative values, or frozen historical advice.
- Do not create simulated funds, orders, fills, or broker integration.
- Keep A-share and convertible-bond routes and state isolated.
- Edit Chinese files with `apply_patch`; run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree and do not commit or push.

---

### Task 1: Persist Deterministic Block Reasons

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Modify: `apps/api/src/qibao_api/shangshu/decision_runtime.py`
- Test: `apps/api/tests/shangshu/test_decision_runtime.py`
- Test: `apps/api/tests/shangshu/test_intraday_monitor.py`

**Interfaces:**
- Produces: `IntradayEvaluationResult.quality_reasons: tuple[str, ...]`.
- Produces: `DecisionCycleSnapshot.quality_reasons` copied from the evaluator.

- [x] **Step 1: Write failing evaluator tests**

Assert exact reason tuples for no quotes, non-ready quote quality, future quote time, stale quote time, unavailable risk, unavailable compliance, and denied compliance. Existing ready cases must keep `quality_reasons == ()`.

- [x] **Step 2: Verify evaluator RED**

Run: `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\shangshu\test_decision_runtime.py -q`

Expected: failures because `IntradayEvaluationResult` does not expose the required reasons.

- [x] **Step 3: Implement exact reason derivation**

Add the defaulted tuple field to `IntradayEvaluationResult`. In `DeterministicIntradayEvaluator.evaluate`, derive reasons in this order:

```python
quality_reasons = tuple(reason for reason, blocked in (
    ("live_quotes_unavailable", not context.quotes),
    ("live_quote_quality_blocked", quote_quality_blocked),
    ("live_quote_timestamp_invalid", quote_timestamp_invalid),
    ("live_quotes_stale", quote_stale),
    ("risk_unavailable", not risk_available),
    ("compliance_unavailable", not compliance_available),
    ("compliance_not_allowed", not compliance_allowed),
) if blocked)
```

Keep the existing ready/blocked decision and empty blocked advice behavior.

- [x] **Step 4: Write failing monitor persistence tests**

Create a blocked `IntradayEvaluationResult` with `quality_reasons=("live_quotes_unavailable",)`. Assert the stored snapshot contains it. Create a second blocked result with a different reason and identical other content; assert `_source_hash` differs.

- [x] **Step 5: Persist and hash reasons**

Pass `quality_reasons=result.quality_reasons` into `DecisionCycleSnapshot` and include the tuple in `_source_hash`.

- [x] **Step 6: Run focused backend tests**

Run: `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\shangshu\test_decision_runtime.py apps\api\tests\shangshu\test_intraday_monitor.py apps\api\tests\routes\test_decisions.py -q`

Expected: all focused tests pass.

### Task 2: Explain Blocked State In Beginner Views

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/cockpit.py`
- Modify: `apps/web/src/features/decision-workbench/PhaseContextPanel.tsx`
- Modify: `apps/web/src/features/decision-workbench/PhaseContextPanel.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/PhaseTimeline.tsx`
- Modify: `apps/web/src/features/stock-cockpit/PhaseTimeline.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/types.ts`
- Test: `apps/api/tests/a_shares/test_cockpit.py`

**Interfaces:**
- Produces: `qualityReasonLabel(reason: string): string`.
- Produces: `StockPhaseHistory.phase_status` and `StockPhaseHistory.quality_reasons`.
- Consumes: the latest cutoff-safe phase snapshot and materialized prior advice.

- [x] **Step 1: Write failing translation and timeline tests**

Assert the cockpit copies status/reasons only from the latest cutoff-safe aggregate. Assert the seven stable codes render beginner Chinese. Build a blocked intraday slot with prior advice and assert the timeline says the current run was blocked and the old judgment is retained. Build a blocked slot without advice and assert it does not claim the stock was absent from the phase.

- [x] **Step 2: Verify frontend RED**

Run: `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\a_shares\test_cockpit.py -q`

Run: `pnpm.cmd --filter @qibao/web exec vitest run src/features/decision-workbench/PhaseContextPanel.test.tsx src/features/stock-cockpit/PhaseTimeline.test.tsx`

Expected: failures because the translations and blocked timeline notice are missing.

- [x] **Step 3: Implement shared translation and blocked copy**

Extend both backend and TypeScript `StockPhaseHistory` with default `phase_status="empty"` and `quality_reasons=()`. Copy them from the latest included aggregate. Export `qualityReasonLabel`. In `PhaseTimeline`, derive the first recorded reason for the blocked notice, retain prior advice below it when present, and use the conservative unknown-code fallback.

- [x] **Step 4: Run focused frontend tests**

Run the command from Step 2 again.

Expected: all focused tests pass.

### Task 3: Production Verification

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:**
- Verifies the complete backend-to-browser reason chain.

- [x] **Step 1: Run complete automated verification**

Run all API tests, Ruff, all web tests, and the production build.

- [x] **Step 2: Run source safety checks**

Run strict UTF-8 decoding and mojibake scans over all changed text files, then `git diff --check`.

- [x] **Step 3: Verify real runtime**

Restart the API, run or observe an intraday cycle, inspect `/api/v1/decisions/current`, and verify ready cycles have no reasons while blocked cycles expose an exact reason instead of `block_reason_unrecorded`.

- [x] **Step 4: Verify the browser**

Open the A-share cockpit, confirm the ready layout is unchanged, then use a frozen blocked fixture/component test as the authoritative blocked visual check if current live data is ready. Confirm no console errors and no horizontal overflow.
