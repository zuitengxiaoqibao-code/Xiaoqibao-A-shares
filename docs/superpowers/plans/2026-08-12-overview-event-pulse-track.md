# Overview Event Pulse Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace vertical anomaly labels on the Shanghai index minute chart with a numbered, grouped, selected-state event pulse track linked to the anomaly list.

**Architecture:** Keep event-to-minute matching as a pure transformation in `OverviewMinuteChart.tsx`. Produce stable display groups for the ECharts marker layer and the React event rail/list so numbering stays consistent. Extend `QuantChart` only with an optional chart event callback if direct chart clicking is required; otherwise selection remains driven by accessible React controls.

**Tech Stack:** React 19, TypeScript, ECharts 5, Vitest, Testing Library, CSS.

## Global Constraints

- Use only existing real `minute_series` and `anomalies` data.
- Never synthesize event times, prices, directions, themes, or headlines.
- Preserve A-share red-up and green-down semantics.
- Deliver and verify through the portable Windows EXE.
- Do not close, restart, or control TongdaXin.

---

### Task 1: Pure event pulse model

**Files:**
- Modify: `apps/web/src/features/market-overview/OverviewMinuteChart.tsx`
- Test: `apps/web/src/features/market-overview/OverviewMinuteChart.test.tsx`

**Interfaces:**
- Produces: `buildAnomalyPulseGroups(points, anomalies, selectedAnomalyId)` with stable number, group count, minute, price, lane, color and selected state.

- [x] Write failing tests proving labels are short numbers, negative events are green, same-minute events aggregate to `+N`, and selected groups remain visible.
- [x] Run the focused Vitest file and confirm expected failures.
- [x] Implement the minimal pure grouping and ECharts marker configuration.
- [x] Run the focused Vitest file and confirm it passes.

### Task 2: Event rail and synchronized anomaly list

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Test: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`

**Interfaces:**
- Consumes: stable chronological anomaly numbering from Task 1.
- Produces: accessible event pulse rail, selected event summary and numbered right-side list.

- [x] Write failing UI tests for the rail, selected summary, numbered list and synchronized selection.
- [x] Run focused UI tests and confirm expected failures.
- [x] Implement the React controls and terminal-specific styling with reduced-motion support.
- [x] Run focused UI tests and confirm they pass.

### Task 3: Verification and EXE delivery

**Files:**
- Create: `docs/verification/2026-08-12-overview-event-pulse-track.md`

- [x] Run all Web tests and production build.
- [x] Run API tests to protect the desktop release baseline.
- [x] Run UTF-8/mojibake scan and `git diff --check`.
- [x] Record TongdaXin process and port baseline.
- [x] Run `scripts/build-portable.ps1`.
- [x] Run `scripts/run-portable-smoke.ps1 -UseReleaseData` against the rebuilt release or staged release.
- [x] Verify the eight persistent directories, no new application process residue, and unchanged TongdaXin PID/port.
