# Monitor Console Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompose the root A-share homepage into a deep-blue monitoring console inspired by the supplied screenshot while preserving existing behavior and real data.

**Architecture:** Add semantic monitoring-window wrappers to `TodayDecisionView` and scope all visual changes under a homepage-specific class. Reuse `MarketSentimentDashboard` and `DecisionWorkbench` without duplicating or fabricating data.

**Tech Stack:** React, TypeScript, CSS Grid, Vitest, Testing Library

## Global Constraints

- Do not copy screenshot text, subtitles, watermarks, video controls, or social overlays.
- Preserve routes, navigation labels, API contracts, accessibility roles, and real-data behavior.
- Do not add dependencies or fabricated market values.
- Preserve UTF-8 Chinese source text.

---

### Task 1: Homepage monitoring structure

**Files:**
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Test: `apps/web/src/features/dashboard/Dashboard.test.tsx`

**Interfaces:**
- Consumes: existing market sentiment and decision workbench components.
- Produces: `A 股监控首页`, `市场情绪监视窗`, and `三阶段决策监视窗` semantic regions.

- [ ] Write a failing dashboard test that asserts the monitoring structure.
- [ ] Run the focused dashboard test and confirm failure because the structure is absent.
- [ ] Add the minimum semantic wrappers and truthful control-band labels.
- [ ] Run the focused test and confirm it passes.

### Task 2: Monitoring-console visual system

**Files:**
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: the Task 1 homepage classes and existing child component classes.
- Produces: screenshot-inspired deep-blue, compact, square-pane layout with responsive collapse.

- [ ] Add homepage-scoped color tokens, title bars, pane borders, dense grid spacing, and state colors.
- [ ] Add 1280px, 900px, and 520px responsive rules without changing non-homepage routes.
- [ ] Run full tests and production build.
- [ ] Run UTF-8/mojibake and `git diff --check` verification.
- [ ] Inspect the live homepage at desktop, small laptop, and mobile widths and repair visual failures.
