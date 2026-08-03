# Content-Driven Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove meaningless blank areas across the desktop application while preserving stable chart and dashboard canvases.

**Architecture:** Make generic page grids and content cards size to their actual content. Keep explicit height only on visualizations that require a stable drawing surface, and cap long feeds with scrolling rather than forcing short feeds to fill a large panel.

**Tech Stack:** React 19, TypeScript, CSS Grid, Vitest, Testing Library, Vite, portable Windows EXE.

## Global Constraints

- Preserve all existing routes, data contracts, and real-data behavior.
- Do not introduce simulated data.
- Preserve necessary stable dimensions for ECharts, K-line charts, gauges, and fixed-format dashboards.
- Use `apply_patch` for encoding-sensitive source edits.
- Run a mojibake scan after touching Chinese UI files.

---

### Task 1: Lock the generic workspace layout contract

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`

**Interfaces:**
- Consumes: existing `.distinct-block-grid`, `.distinct-block`, `.distinct-block-body`, and `.distinct-empty` selectors.
- Produces: a content-driven generic workspace layout with compact empty states.

- [ ] **Step 1: Write a failing CSS contract test**

Read `overview.css` and assert that the generic grid uses `align-items: start`, generic cards and bodies have no large fixed minimum height, and empty states are compact.

- [ ] **Step 2: Verify the test fails**

Run: `pnpm --filter @qibao/web test -- MarketOverviewView.test.tsx`

Expected: FAIL because the current stylesheet uses `align-items: stretch` and generic `230px` to `520px` minimum heights.

- [ ] **Step 3: Implement the minimal CSS correction**

Change the grid to top alignment, remove generic large minimum heights, keep size classes for column span only, and give `.distinct-empty` a compact minimum height. Preserve chart-specific dimensions.

- [ ] **Step 4: Verify the focused test passes**

Run: `pnpm --filter @qibao/web test -- MarketOverviewView.test.tsx`

Expected: PASS.

### Task 2: Audit major pages for the same layout defect

**Files:**
- Modify only affected CSS files under `apps/web/src/features/` and `apps/web/src/app/`.
- Test the nearest existing `*.test.tsx` file for each changed page.

**Interfaces:**
- Consumes: existing page-specific layout classes.
- Produces: content-driven text/list/empty-state regions, with stable visualization canvases unchanged.

- [ ] **Step 1: Classify fixed heights**

Search `min-height`, fixed `height`, `100vh`, `align-items: stretch`, and fixed grid rows. Classify each occurrence as visualization, fixed-format control, or ordinary content.

- [ ] **Step 2: Add a failing regression assertion for every ordinary-content defect found**

Use source-level CSS assertions when jsdom cannot calculate layout. Keep each assertion tied to a named selector and expected layout contract.

- [ ] **Step 3: Verify each new assertion fails for the intended rule**

Run the nearest focused Vitest file and inspect the failure message.

- [ ] **Step 4: Remove only the invalid sizing rule**

Do not change visualization height, data flow, routes, copy, or component behavior.

- [ ] **Step 5: Verify focused tests pass**

Run each affected feature test.

### Task 3: Verify and rebuild the portable application

**Files:**
- Build output: `dist/XiaoQiBao-Portable/xiaoqibao.exe`

**Interfaces:**
- Consumes: production web bundle and existing persistent desktop data.
- Produces: updated portable EXE with user data preserved.

- [ ] **Step 1: Run frontend tests and production build**

Run: `pnpm test:web`

Run: `pnpm build`

- [ ] **Step 2: Scan modified Chinese files for mojibake**

Search for replacement characters, repeated question marks, and common mojibake sequences in modified source files.

- [ ] **Step 3: Perform desktop and narrow-screen visual checks**

Verify Hotspot Broadcast plus representative overview, A-share, first-limit-up, quant-analysis, convertible-bond, risk, history, and settings pages. Confirm ordinary content no longer creates large empty panels and no content overlaps.

- [ ] **Step 4: Preserve persistent files and rebuild the portable EXE**

Stop the running portable process, rebuild with `scripts/build-portable.ps1 -SkipTests`, restore persistent files, and verify their SHA-256 hashes are unchanged.

- [ ] **Step 5: Run portable smoke verification and launch the updated EXE**

Run `scripts/run-portable-smoke.ps1`, confirm API and UI readiness, then launch `dist/XiaoQiBao-Portable/xiaoqibao.exe`.
