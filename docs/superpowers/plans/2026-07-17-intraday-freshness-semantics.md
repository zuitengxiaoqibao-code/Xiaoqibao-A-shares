# Intraday Freshness Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop treating an unchanged deterministic advice version as a failed market-data link while preserving real stale-data warnings.

**Architecture:** Derive live freshness in a pure frontend function from the API's existing persisted polling-success timestamps. Integrate that result into the decision workbench so only live intraday data can show a stale banner, with scope-specific timestamps and dynamic thresholds.

**Tech Stack:** React 19, TypeScript 5, Vitest, Testing Library, existing FastAPI polling contract.

## Global Constraints

- A 股 remains primary and convertible bonds remain isolated.
- Do not add accounts, funds, positions, orders, broker connectivity, or automatic trading.
- Missing data remains explicit and must never be fabricated or replaced with zero.
- AI may explain frozen deterministic evidence but cannot change deterministic results or manufacture freshness.
- Existing decision history remains immutable.
- Edit Chinese files with `apply_patch`, then run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree and do not commit, stage, push, reset, or revert unrelated changes.

---

### Task 1: Lock Scope-Specific Freshness Behavior

**Files:**
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.test.tsx`

**Interfaces:**
- Consumes: existing `DecisionResponse.polling`, `PhaseSlot.generated_at`, phase and scope props.
- Produces: regression coverage for fresh, stale, selected-stock and frozen-phase behavior.

- [x] **Step 1: Write failing component tests**

```tsx
expect(screen.queryByText("聚合数据已过期")).not.toBeInTheDocument();
expect(screen.queryByText("行情更新已超过有效时间")).not.toBeInTheDocument();
```

Use an old `generated_at` with a recent relevant success time for the fresh case. Use an old relevant success beyond twice its interval for the stale case and assert the new beginner copy. Switch to an old premarket phase and assert that no live-data warning appears.

- [x] **Step 2: Run the test and verify RED**

Run: `pnpm --filter @qibao/web test -- DecisionWorkbench.test.tsx`

Expected: the fresh case still renders “聚合数据已过期” and the stale case lacks the new copy.

### Task 2: Implement Pure Freshness Semantics

**Files:**
- Create: `apps/web/src/features/decision-workbench/freshness.ts`
- Create: `apps/web/src/features/decision-workbench/freshness.test.ts`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `DecisionResponse["polling"]`, `DecisionPhase`, market session, server time, generated time and selected symbol.
- Produces: `livePhaseFreshness(input): LivePhaseFreshness`.

- [x] **Step 1: Add pure-function tests for scope and threshold edges**

```ts
expect(livePhaseFreshness(freshSelectedInput).status).toBe("fresh");
expect(livePhaseFreshness(staleMarketInput).status).toBe("stale");
expect(livePhaseFreshness(premarketInput).status).toBe("not_applicable");
expect(livePhaseFreshness(invalidTimeInput).status).toBe("uninitialized");
```

- [x] **Step 2: Implement the pure function**

Return the relevant scope, reference timestamp and effective threshold. Use focus fields for a non-empty selected symbol and universe fields otherwise. Use `generated_at` only when the relevant success timestamp is absent.

- [x] **Step 3: Integrate the result and update banner copy**

Replace the direct `generated_at` comparison in `PhaseContent`. Render a structured stale banner only when status is `stale`, including the relevant scope label and formatted last-success time.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `pnpm --filter @qibao/web test -- DecisionWorkbench.test.tsx freshness.test.ts`

Expected: all selected tests pass.

### Task 3: Production Verification

**Files:**
- Modify: `docs/roadmap.md`
- Verify: all changed files.

**Interfaces:**
- Consumes: completed freshness behavior.
- Produces: automated and rendered evidence that the false warning is gone without hiding true staleness.

- [x] **Step 1: Run full API/Web suites, Ruff and build**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests -q`

Run: `.venv\Scripts\python.exe -m ruff check apps/api/src apps/api/tests`

Run: `pnpm --filter @qibao/web test`

Run: `pnpm --filter @qibao/web build`

Expected: no failures.

- [x] **Step 2: Run encoding and diff gates**

Strictly decode every changed text file as UTF-8, run the established mojibake scan over `apps` and `README.md`, then run `git diff --check`.

Expected: all gates pass.

- [x] **Step 3: Verify the real API state and browser**

Confirm the real aggregate age exceeds 180 seconds while the relevant poll age remains below its effective threshold. At desktop and 390x844, verify no stale banner appears, no horizontal overflow exists, and no application console error or dialog occurs.

- [x] **Step 4: Verify the true-stale fixture**

Use the automated stale fixture to confirm the new warning still appears with the correct relevant scope and last-success time.

## Verification Record

- Component RED: four expected failures reproduced the market-wide, selected-stock, true-stale and frozen-phase defects.
- Focused GREEN: `freshness.test.ts` 6 passed; `DecisionWorkbench.test.tsx` 15 passed.
- Full regression: API 729 passed and 1 skipped; Web 153 passed; Ruff and the production build passed.
- Encoding and diff gates: 103 changed text files decoded as strict UTF-8; 279 source files passed the mojibake scan; `git diff --check` passed.
- Real runtime: normal polling rendered no stale banner; a later real universe poll age of about 189 seconds against a 180-second effective threshold rendered the new full-market warning with the last-success time. Both states had zero browser console errors or dialogs.
- Responsive browser check: desktop 1280x720 and mobile 390x844 had no page-level horizontal overflow. The mobile primary navigation remains an intentional horizontal scroll region.
