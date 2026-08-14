# Overview Stable Anomaly Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep market minute data refreshing while stabilizing same-day anomaly events and removing the top event-card rail.

**Architecture:** Merge each new overview response with the currently displayed same-day anomaly snapshot by `anomaly_id`. Keep existing events in place, append only unseen IDs, and reset the snapshot when `as_of` changes.

**Tech Stack:** React 19, TypeScript, Vitest, CSS.

## Global Constraints

- Keep the five-second market refresh.
- Remove the full top anomaly card rail.
- Never synthesize anomaly data.
- Preserve red-up and green-down semantics.
- Rebuild and verify the portable EXE without controlling TongdaXin.

---

### Task 1: Stable anomaly refresh contract

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`

- [x] Add failing tests for no top rail, same-day stable events, append-only new IDs and cross-day reset.
- [x] Run the focused test and confirm the old whole-response replacement fails.
- [x] Implement a pure same-day overview merge and use the merged response for state and cache.
- [x] Run the focused test and confirm it passes.

### Task 2: Remove retired rail styling

**Files:**
- Modify: `apps/web/src/features/market-overview/overview.css`

- [x] Remove event-rail styles and keep only the selected-summary light treatment.
- [x] Run layout safety and focused market overview tests.

### Task 3: EXE verification

**Files:**
- Create: `docs/verification/2026-08-12-overview-stable-anomaly-snapshot.md`

- [x] Run Web full tests and production build.
- [x] Run UTF-8/mojibake scan and `git diff --check`.
- [x] Rebuild the portable EXE and run release-data smoke.
- [x] Verify persistent directories, no application residue and unchanged TongdaXin PID/port.
