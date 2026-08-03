# Watchlist Default Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open the A-share selector on the watchlist and place it before short-term and swing candidates.

**Architecture:** Keep the existing `CandidateTab` state and rendering branches. Change only the initial state and the shared tab-order constant so visual order and keyboard order cannot diverge.

**Tech Stack:** React, TypeScript, Vitest, Testing Library

## Global Constraints

- Do not change candidate loading or stock-selection fallback behavior.
- Do not add dependencies.
- Preserve UTF-8 Chinese UI text.

---

### Task 1: Default watchlist tab and ordering

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Test: `apps/web/src/features/stock-cockpit/StockSelector.test.tsx`

**Interfaces:**
- Consumes: existing `CandidateTab` union and selector tabs.
- Produces: watchlist-first tab order for rendering and keyboard navigation.

- [ ] **Step 1: Write the failing test**

Assert that `getAllByRole("tab")` returns watchlist, short-term, and swing labels in that order, and that watchlist is selected by default.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/features/stock-cockpit/StockSelector.test.tsx`

Expected: FAIL because short-term is currently first and selected.

- [ ] **Step 3: Write minimal implementation**

Initialize `tab` to `watchlist` and use one watchlist-first order for both tab rendering and arrow-key switching.

- [ ] **Step 4: Run focused and full tests**

Run the selector test, the full frontend suite, and the production build. Then run UTF-8 and mojibake checks for the two touched Chinese files.
