# Sitewide Visual Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify every top-level page under one dark professional market-terminal visual system while preserving each page's task-specific density and behavior.

**Architecture:** Introduce semantic design tokens and a small set of presentational terminal primitives, then migrate page families in controlled batches. Keep business components and loaders unchanged; the migration is a CSS and composition change with focused rendering tests and cross-viewport visual verification.

**Tech Stack:** React 19, TypeScript 5.8, CSS, Vitest, Testing Library, Vite, Lucide React, ECharts.

## Global Constraints

- Use `JetBrains Mono` for data/body copy and `Orbitron` only for short English display labels.
- Keep primary body text at least 12px and secondary table labels at least 10px.
- Use red for A-share up/positive, green for down/negative, gold for warning/watch, cyan for live/interactive, gray for unavailable/unverified.
- Use 0-3px panel radii and no nested decorative cards.
- Do not change routes, data contracts, loaders, financial calculations, or existing feature behavior.
- Do not add sample, random, or fabricated data.
- Preserve the existing event K-line numbered anchors, event index, selected detail strip, and red-up/green-down semantics.
- After touching Chinese UI files, run the mojibake scan, related tests, full web tests, and production build.

---

### Task 1: Semantic Tokens And Terminal Primitives

**Files:**
- Create: `apps/web/src/app/tokens.css`
- Create: `apps/web/src/app/terminal.css`
- Create: `apps/web/src/shared/terminal/TerminalPrimitives.tsx`
- Create: `apps/web/src/shared/terminal/TerminalPrimitives.test.tsx`
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/app/typography.test.ts`

**Interfaces:**
- Produces: `TerminalPageHeader`, `TerminalStatusStrip`, `TerminalMetricBand`, `TerminalPanel`, and `TerminalStateNotice` presentational components.
- Produces: semantic CSS variables `--surface-*`, `--border-*`, `--text-*`, `--market-*`, and `--status-*`.

- [ ] **Step 1: Write failing token and primitive tests**

```tsx
it("renders a shared page header and explicit partial state", () => {
  render(<><TerminalPageHeader eyebrow="MARKET / OVERVIEW" title="信息总览" />
    <TerminalStateNotice state="partial" title="部分数据可用" detail="保留最近快照" /></>);
  expect(screen.getByRole("heading", { name: "信息总览" })).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveAttribute("data-state", "partial");
});
```

Update `typography.test.ts` to read `src/app/tokens.css` and assert the exact semantic variables and both font roles.

- [ ] **Step 2: Run tests and verify failure**

Run: `pnpm --dir apps/web test -- src/shared/terminal/TerminalPrimitives.test.tsx src/app/typography.test.ts`

Expected: FAIL because the primitive module and `tokens.css` do not exist.

- [ ] **Step 3: Implement minimal tokens and primitives**

```css
:root {
  --surface-canvas: #070b10; --surface-base: #0b1118;
  --surface-raised: #101923; --surface-emphasis: #15222d;
  --border-subtle: #22313d; --border-strong: #344a5a;
  --text-primary: #dce7ee; --text-secondary: #9fb0bd; --text-muted: #667987;
  --market-up: #f04f5f; --market-down: #2fcf91;
  --status-warning: #e5b84b; --status-live: #39c8dd;
  --status-unavailable: #7d8993;
  --font-display: "Orbitron", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  --font-body: "JetBrains Mono", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
}
```

Implement primitives as semantic wrappers accepting `className`, children, and state props without business logic. Import CSS in this order from `main.tsx`: `tokens.css`, existing `theme.css`, then `terminal.css`.

- [ ] **Step 4: Run focused tests**

Run: `pnpm --dir apps/web test -- src/shared/terminal/TerminalPrimitives.test.tsx src/app/typography.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/tokens.css apps/web/src/app/terminal.css apps/web/src/shared/terminal apps/web/src/main.tsx apps/web/src/app/typography.test.ts
git commit -m "feat(web): add shared terminal visual system"
```

### Task 2: Dark Market Overview Baseline

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketFeatureWorkspace.test.tsx`

**Interfaces:**
- Consumes: terminal primitives and semantic tokens from Task 1.
- Produces: the reference high-density layout for market-wide pages.

- [ ] **Step 1: Add failing structural and CSS tests**

```tsx
it("uses the shared dark terminal shell without losing overview regions", async () => {
  render(<MarketOverviewView load={() => Promise.resolve(overview)} />);
  expect(await screen.findByRole("heading", { name: "信息总览" })).toBeInTheDocument();
  expect(screen.getByRole("main")).toHaveClass("terminal-page", "market-overview-page");
  expect(screen.getByRole("region", { name: "市场情绪与指数" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "市场实时资讯" })).toBeInTheDocument();
});
```

Add a CSS source assertion that `overview.css` no longer defines `--overview-bg: #f` or white panel literals such as `background: #fff`.

- [ ] **Step 2: Run the overview tests and verify failure**

Run: `pnpm --dir apps/web test -- src/features/market-overview/MarketOverviewView.test.tsx src/features/market-overview/MarketFeatureWorkspace.test.tsx`

Expected: FAIL on the missing terminal class and remaining light palette.

- [ ] **Step 3: Migrate the overview shell and palette**

Wrap the page title in `TerminalPageHeader`, keep the current market strip, feature rail, chart, anomaly list, live feed, sector tables, and feature workspaces. Remap overview variables to shared tokens:

```css
.market-overview-page {
  --overview-bg: var(--surface-canvas);
  --overview-panel: var(--surface-base);
  --overview-line: var(--border-subtle);
  --overview-line-strong: var(--border-strong);
  --overview-text: var(--text-primary);
  --overview-muted: var(--text-muted);
  --overview-up: var(--market-up);
  --overview-down: var(--market-down);
  --overview-gold: var(--status-warning);
  --overview-blue: var(--status-live);
}
```

Replace light row stripes, headers, selected rows, chart empty states, and regime panels with `--surface-*` values. Do not alter grid tracks or loader calls.

- [ ] **Step 4: Run overview tests**

Run: `pnpm --dir apps/web test -- src/features/market-overview`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/market-overview
git commit -m "feat(web): unify information overview terminal"
```

### Task 3: Today Decision Reference Layout

**Files:**
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Create: `apps/web/src/features/decision-workbench/TodayDecisionView.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `TerminalPageHeader`, `TerminalStatusStrip`, and `TerminalPanel`.
- Produces: the reference conclusion-first layout for decision pages.

- [ ] **Step 1: Write a failing layout test**

```tsx
it("orders market state, breaking focus, and three-phase decisions", async () => {
  render(<TodayDecisionView loadCurrent={() => Promise.resolve(response())}
    loadSentiment={() => Promise.resolve(sentiment)} />);
  const regions = await screen.findAllByRole("region");
  expect(screen.getByRole("heading", { name: "A 股决策监控" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "市场情绪监视窗" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "三阶段决策监视窗" })).toBeInTheDocument();
  expect(regions.length).toBeGreaterThan(1);
});
```

- [ ] **Step 2: Run and verify the test fails on the shared shell assertions**

Run: `pnpm --dir apps/web test -- src/features/decision-workbench/TodayDecisionView.test.tsx`

Expected: FAIL until the shared page and panel classes are present.

- [ ] **Step 3: Apply the shared decision layout**

Use `TerminalPageHeader` for the current title and readouts, a compact status strip for scope/data mode, then terminal panels for market sentiment and decision flow. Keep the current scope switch, sentiment loader, and `DecisionWorkbench` props unchanged.

Replace `.console-*` one-off colors in `theme.css` with semantic tokens and remove letter spacing from Chinese copy.

- [ ] **Step 4: Run decision tests**

Run: `pnpm --dir apps/web test -- src/features/decision-workbench`

Expected: PASS with existing phase, freshness, error, and evidence behavior unchanged.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/decision-workbench apps/web/src/app/theme.css
git commit -m "feat(web): unify today decision workspace"
```

### Task 4: A-Share Cockpit And Event K-Line Migration

**Files:**
- Modify: `apps/web/src/features/a-shares/AShareResearchView.tsx`
- Modify: `apps/web/src/features/a-shares/AShareResearchView.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: semantic tokens and terminal panels.
- Preserves: list ordering and compact candidate fields, cockpit data flow, event selection, and ECharts options.

- [ ] **Step 1: Add regression tests for the unified shell and preserved event behavior**

```tsx
expect(screen.getByRole("region", { name: "个股新闻与热点事件 K 线" }))
  .toHaveClass("terminal-panel", "stock-event-kline");
fireEvent.click(screen.getByRole("button", { name: /02 .* 正向/ }));
expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent(events[1].headline);
```

Keep existing assertions that watchlist/candidate lists do not expose sentiment details in the left list.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pnpm --dir apps/web test -- src/features/a-shares/AShareResearchView.test.tsx src/features/stock-cockpit/StockDecisionCockpit.test.tsx src/features/stock-timeline/StockEventKline.test.tsx`

Expected: FAIL on new shared class assertions only.

- [ ] **Step 3: Migrate composition and CSS**

Use terminal panels for selector, key-signal dashboard, evidence sections, and event K-line. Replace local risk/info colors with semantic tokens. Keep ECharts `UP_COLOR` and `DOWN_COLOR` synchronized to `#f04f5f` and `#2fcf91`; do not change marker ranking, `MAX_CHART_EVENTS`, `MIN_EVENT_BAR_GAP`, or selection logic.

- [ ] **Step 4: Run focused tests**

Run: `pnpm --dir apps/web test -- src/features/a-shares src/features/stock-cockpit src/features/stock-timeline`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/a-shares apps/web/src/features/stock-cockpit apps/web/src/features/stock-timeline apps/web/src/app/theme.css
git commit -m "feat(web): unify a-share decision cockpit"
```

### Task 5: Research Tool Pages

**Files:**
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: common header, status strip, metric band, panel, table, and notice styles.
- Preserves: first-limit-up screening, Kronos/ECharts behavior, news sync and correction actions.

- [ ] **Step 1: Add failing shared-shell tests to each page**

```tsx
expect(screen.getByRole("main")).toHaveClass("terminal-page");
expect(screen.getByRole("heading", { name: expectedTitle })).toBeInTheDocument();
expect(screen.getByRole("status")).toHaveAttribute("data-state");
```

- [ ] **Step 2: Run tool-page tests and verify failure**

Run: `pnpm --dir apps/web test -- src/features/first-limit-up src/features/quant-analysis src/features/news-intelligence`

Expected: FAIL on the new visual contract assertions.

- [ ] **Step 3: Apply primitives without changing business components**

Replace page-specific header, summary, tabs, table, loading, error, and stale styles with semantic tokens. Preserve the quant four-quadrant proportions and ECharts container dimensions.

- [ ] **Step 4: Run tool-page tests**

Run: `pnpm --dir apps/web test -- src/features/first-limit-up src/features/quant-analysis src/features/news-intelligence`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/first-limit-up apps/web/src/features/quant-analysis apps/web/src/features/news-intelligence apps/web/src/app/theme.css
git commit -m "feat(web): unify research tool pages"
```

### Task 6: Convertible Bonds, Settings, Operations, And Navigation

**Files:**
- Modify: `apps/web/src/features/convertible-bonds/ConvertibleBondView.tsx`
- Modify: `apps/web/src/features/convertible-bonds/ConvertibleBondView.test.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.test.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: the shared terminal visual contract.
- Preserves: convertible-bond domain separation and all existing top-level route labels/order.

- [ ] **Step 1: Add failing visual-contract and navigation tests**

Assert each page has `terminal-page`, uses an accessible heading, and retains the current primary navigation names. Assert convertible-bond content does not render A-share candidate labels.

- [ ] **Step 2: Run tests and verify failure**

Run: `pnpm --dir apps/web test -- src/features/convertible-bonds src/features/data-settings src/features/operations src/features/beginner-shell`

Expected: FAIL on missing shared shell classes.

- [ ] **Step 3: Migrate remaining page families**

Apply semantic tokens and primitives. Keep the convertible-bond gold domain accent only as a restrained secondary accent, not a separate palette. Preserve existing navigation size, indentation, route highlighting, and top-level status.

- [ ] **Step 4: Run focused tests**

Run: `pnpm --dir apps/web test -- src/features/convertible-bonds src/features/data-settings src/features/operations src/features/beginner-shell`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/convertible-bonds apps/web/src/features/data-settings apps/web/src/features/operations apps/web/src/features/beginner-shell apps/web/src/app/theme.css
git commit -m "feat(web): complete terminal page migration"
```

### Task 7: Responsive And Full-Site Verification

**Files:**
- Modify: `apps/web/src/app/terminal.css`
- Modify: `apps/web/src/app/theme.css`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Create: `docs/verification/2026-07-29-sitewide-visual-check.md`

**Interfaces:**
- Produces: verified desktop/tablet/mobile layout behavior and a recorded acceptance result.

- [ ] **Step 1: Add source-level guard tests**

Extend `typography.test.ts` to scan CSS for negative letter spacing, body text below 10px in migrated shared primitives, and forbidden light overview backgrounds.

- [ ] **Step 2: Run the full web suite and production build**

Run: `pnpm --dir apps/web test`

Expected: all tests PASS.

Run: `pnpm --dir apps/web build`

Expected: TypeScript and Vite build complete with exit code 0.

- [ ] **Step 3: Run encoding and palette scans**

```powershell
$bad = rg -n "\?{3,}|锟斤拷|ï¿½|Ã.|Â." apps/web/src docs/verification
if ($LASTEXITCODE -eq 1) { Write-Output "mojibake scan clean"; exit 0 }
$bad; exit 1
```

Run: `rg -n "background:\s*#fff|background:\s*white|--overview-.*#f[0-9a-f]{5}" apps/web/src`

Expected: no migrated page-level light surfaces; legitimate chart tooltip text is reviewed individually.

- [ ] **Step 4: Perform browser visual checks**

At 1440x900, 1280x800, and 390x844 capture and inspect `/market-overview`, `/`, `/a-shares?symbol=600519`, `/first-limit-up`, `/first-limit-up/quant-analysis`, `/news`, `/convertible-bonds`, and `/settings`.

Record for each route: no overlap, no clipped Chinese text, stable chart dimensions, consistent semantic colors, visible focus states, and correct single/two-column responsive layout.

- [ ] **Step 5: Commit verification fixes and report**

```bash
git add apps/web/src/app apps/web/src/features/market-overview docs/verification/2026-07-29-sitewide-visual-check.md
git commit -m "test(web): verify unified terminal across viewports"
```
