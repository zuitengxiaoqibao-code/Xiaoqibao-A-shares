# Overview Event Breathing Light Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace continuously expanding and moving event motion with a static event rail and low-frequency selected-state breathing light.

**Architecture:** Keep the React structure and real event data unchanged. Implement the behavior entirely in the event-specific CSS layer so it adds no timers, state updates or rendering work.

**Tech Stack:** React 19, TypeScript, CSS, Vitest.

## Global Constraints

- Do not change event data, matching, numbering or red-up/green-down semantics.
- Do not animate position, scale or content scrolling.
- Only the selected event may use a low-frequency ambient animation.
- Rebuild and verify the portable Windows EXE.
- Do not close, restart or control TongdaXin.

---

### Task 1: Event motion contract

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`

**Interfaces:**
- Produces: CSS-only selected-state breathing animation with no geometry movement.

- [x] Add a failing CSS contract test for no transform-based event motion, no hover displacement, selected-only breathing and reduced-motion shutdown.
- [x] Run the focused test and confirm it fails against the current expanding pulse.
- [x] Replace the old event pulse with opacity, border, background and shadow breathing only.
- [x] Run the focused test and confirm it passes.

### Task 2: Verification and EXE delivery

**Files:**
- Create: `docs/verification/2026-08-12-overview-event-breathing-light.md`

- [x] Run all Web tests and production build.
- [x] Run UTF-8/mojibake scan and `git diff --check`.
- [x] Record TongdaXin PID and port baseline.
- [x] Rebuild the portable EXE.
- [x] Run the portable EXE smoke test with release data.
- [x] Verify persistent directories, no application residue and unchanged TongdaXin PID/port.
