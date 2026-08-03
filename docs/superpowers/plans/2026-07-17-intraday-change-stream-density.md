# Intraday Change Stream Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep current intraday advice ahead of audit history and prevent repeated live quotes from accumulating in each new advice version.

**Architecture:** Add a backward-compatible evidence classification to the shared decision contract, then replace prior live-quote evidence during deterministic intraday evaluation. Render the immutable change history through a newest-first, three-version progressive disclosure component and restore natural mobile document order.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI, React 19, TypeScript 5, Vitest, Testing Library, CSS.

## Global Constraints

- A 股 remains primary and convertible bonds remain isolated.
- Do not add accounts, funds, positions, orders, broker connectivity, or automatic trading.
- Missing data remains explicit and must never be fabricated or replaced with zero.
- AI may explain frozen deterministic evidence but cannot change actions, confidence, numbers, gates, attribution, or observations.
- Existing decision history remains immutable.
- Edit Chinese files with `apply_patch`, then run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree and do not commit, stage, push, reset, or revert unrelated changes.

---

### Task 1: Classify And Replace Live Quote Evidence

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/decision.py`
- Modify: `apps/api/src/qibao_api/shangshu/decision_runtime.py`
- Modify: `apps/api/src/qibao_api/zhongshu/premarket_decision.py`
- Test: `apps/api/tests/contracts/test_decision.py`
- Test: `apps/api/tests/shangshu/test_decision_runtime.py`

**Interfaces:**
- Consumes: existing `EvidenceReference` records, including records without classification.
- Produces: `EvidenceReference.evidence_kind` and `_stable_supporting_evidence(...)` used by `DeterministicIntradayEvaluator.evaluate`.

- [x] **Step 1: Write failing contract and evaluator tests**

```python
assert evidence().evidence_kind == "other"
assert [item.evidence_id for item in result.advice[0].supporting_evidence] == [
    "factor-current", "news-baseline", "quote-current",
]
assert result.advice[0].supporting_evidence[-1].evidence_kind == "live_quote"
```

- [x] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/contracts/test_decision.py apps/api/tests/shangshu/test_decision_runtime.py -q`

Expected: failures show that `evidence_kind` is absent and old quote evidence remains.

- [x] **Step 3: Implement classification and replacement**

```python
EvidenceKind = Literal["other", "candidate_factor", "live_quote", "verified_news"]

class EvidenceReference(BaseModel):
    evidence_kind: EvidenceKind = "other"
```

Create new intraday quote evidence with `evidence_kind="live_quote"`. Mark runtime factor and event evidence with `candidate_factor` and `verified_news`. Filter inherited support with a helper that removes explicit live quotes and conservatively recognizes legacy provider-prefixed quote identities before appending the current quote.

- [x] **Step 4: Run focused API tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/contracts/test_decision.py apps/api/tests/shangshu/test_decision_runtime.py -q`

Expected: all selected tests pass.

### Task 2: Add Change Stream Progressive Disclosure

**Files:**
- Modify: `apps/web/src/features/decision-workbench/types.ts`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.tsx`
- Modify: `apps/web/src/features/decision-workbench/DecisionWorkbench.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: existing `PhaseSlot.change_stream` and optional `Evidence.evidence_kind`.
- Produces: newest-first `ChangeStream` with three-version default visibility, plus an intraday current-advice evidence view that retains all baseline evidence and only the latest quote.

- [x] **Step 1: Write the failing component test**

```tsx
expect(screen.getByText(/变化版本 #5/)).toBeInTheDocument();
expect(screen.getByText(/变化版本 #3/)).toBeInTheDocument();
expect(screen.queryByText(/变化版本 #2/)).not.toBeInTheDocument();
expect(screen.getByRole("button", { name: "查看更早 2 个版本" })).toBeInTheDocument();
```

Verify that rendered `details` elements do not have the `open` attribute, then expand and collapse the older versions. Add a current-advice fixture with multiple legacy and typed live quotes; assert that only the latest quote and all non-quote evidence render in the intraday advice panel.

- [x] **Step 2: Run the component test and verify RED**

Run: `pnpm --filter @qibao/web test -- DecisionWorkbench.test.tsx`

Expected: all five versions are present, no disclosure button exists, and details are open.

- [x] **Step 3: Implement progressive disclosure and mobile ordering**

Use a constant `DEFAULT_VISIBLE_CHANGE_VERSIONS = 3`, sort a copied stream by descending `sequence`, render only the visible slice, and use state keyed by the stream identity for expand/collapse. Add `currentSupportingEvidence(advice, phase)` to retain every non-live item and the newest live quote for the current intraday panel. Remove the mobile `.decision-rail { grid-row: 1; }` override while preserving desktop sticky positioning.

- [x] **Step 4: Run focused Web tests and verify GREEN**

Run: `pnpm --filter @qibao/web test -- DecisionWorkbench.test.tsx`

Expected: the decision workbench tests pass.

### Task 3: Production Verification

**Files:**
- Verify: all changed source, tests, specs, and plans.

**Interfaces:**
- Consumes: completed backend and frontend behavior.
- Produces: fresh automated and rendered evidence for the slice.

- [x] **Step 1: Run the full API suite and Ruff**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests -q`

Run: `.venv\Scripts\python.exe -m ruff check apps/api/src apps/api/tests`

Expected: no failures or lint errors.

- [x] **Step 2: Run the full Web suite and production build**

Run: `pnpm --filter @qibao/web test`

Run: `pnpm --filter @qibao/web build`

Expected: no test or build failures.

- [x] **Step 3: Run encoding and diff gates**

Strictly decode every changed text file as UTF-8, scan `apps` and `README.md` for repeated question marks, replacement characters, and established mojibake markers, then run `git diff --check`.

Expected: all gates pass.

- [x] **Step 4: Restart API and verify real responses**

Confirm health at `http://127.0.0.1:8000/health`, then verify newly evaluated advice contains one `live_quote` and retained non-quote evidence.

- [x] **Step 5: Browser-check desktop and mobile**

At 1440x900 and 390x844, verify current advice precedes the stage rail on mobile, three newest change versions are listed collapsed, disclosure works, no horizontal overflow exists, and no console errors or dialogs occur.
