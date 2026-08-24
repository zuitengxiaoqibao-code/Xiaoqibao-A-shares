# 信息总览密度与分区恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让信息总览的 14 张截图对应工作区在桌面和窄窗口都紧凑可读，并在区块刷新失败时保留真实 last-good 数据。

**Architecture:** 先在工作区渲染层建立紧凑栅格和空态契约，再在页面状态层增加区块失败可视化。优先复用现有 `apiClient.getCached`、`useQuantLiveResource` 和真实快照，不引入新的数据源或模拟数据。

**Tech Stack:** React 18、TypeScript、CSS Grid、Vitest/Testing Library、Vite、PowerShell portable build。

## Global Constraints

- EXE 是唯一用户交付入口，不交付 HTML 或 localhost。
- 中文文件按 UTF-8 安全编辑，保持红涨绿跌。
- 不伪造行情、新闻、AI、候选、概率、进度或 ready 状态。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。

---

### Task 1: 工作区布局回归测试

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`

**Interfaces:**
- Consumes: existing `overview` fixtures and rendered class names.
- Produces: regression coverage for compact empty states and stale-content preservation.

- [ ] **Step 1: Write failing tests**

Add tests that render a no-evidence workspace and assert `distinct-empty` is present while `.evidence-map` does not expose a large-canvas class; add a refresh failure test that asserts the prior snapshot and Chinese retry copy remain visible.

- [ ] **Step 2: Run the focused tests**

Run `pnpm --filter @qibao/web test -- --run apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx apps/web/src/features/market-overview/MarketOverviewView.test.tsx`.

Expected: the new assertions fail before implementation.

- [ ] **Step 3: Keep the test fixtures real**

Use the existing partial/unavailable fixtures; do not add synthetic stock prices or fake news.

- [ ] **Step 4: Commit the tests**

Run `git add apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx apps/web/src/features/market-overview/MarketOverviewView.test.tsx && git commit -m "test: cover compact overview empty and stale states"`.

### Task 2: Compact overview layout and empty evidence map

**Files:**
- Modify: `apps/web/src/features/market-overview/overview.css`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`

**Interfaces:**
- Consumes: existing `Frame`, `Empty`, `EvidenceMap` renderers.
- Produces: content-sized blocks, compact chart/list shells, and truthful evidence-map empty state.

- [ ] **Step 1: Implement the minimum CSS changes**

Set `.distinct-block-grid` to `align-items: start` and `grid-auto-rows: min-content`; remove forced block height; change fixed list/chart heights to bounded `min-height`/`max-height`; set metric decks to content-sized rows; add explicit narrow-window grid rules.

- [ ] **Step 2: Implement the evidence-map guard**

When there are no valid evidence nodes/edges, return the existing `Empty` component with a concise Chinese reason and source context instead of the relationship canvas.

- [ ] **Step 3: Run the focused web tests**

Run `pnpm --filter @qibao/web test -- --run apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`.

Expected: all compact layout and empty-state tests pass.

- [ ] **Step 4: Commit the implementation**

Run `git add apps/web/src/features/market-overview/overview.css apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx && git commit -m "fix: compact overview workspaces and evidence empty state"`.

### Task 3: Section-level stale/error status

**Files:**
- Create: `apps/web/src/shared/SectionRefreshState.tsx`
- Create: `apps/web/src/shared/SectionRefreshState.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`

**Interfaces:**
- Consumes: `error`, `loading`, `data`, and section retry callbacks.
- Produces: `<SectionRefreshState state="stale" phase="..." error="..." onRetry={...} />` with Chinese accessible status.

- [ ] **Step 1: Write the failing component test**

Assert that `state="stale"` renders the last-good message, phase, and exactly one retry button; assert `state="error"` renders a compact error without hiding the caller's content.

- [ ] **Step 2: Run the component test to verify RED**

Run `pnpm --filter @qibao/web test -- --run apps/web/src/shared/SectionRefreshState.test.tsx`.

Expected: module not found or missing state copy.

- [ ] **Step 3: Implement the component**

Use existing `AlertTriangle`, `RefreshCw`, and shared font/color variables. Never render English raw exception text; keep the caller's children outside this component so the old snapshot remains mounted.

- [ ] **Step 4: Integrate with overview refresh status**

Replace the full-width error-only banner path with the section state component when `data` exists; pass the existing `refresh` callback as the one retry action.

- [ ] **Step 5: Run focused tests**

Run `pnpm --filter @qibao/web test -- --run apps/web/src/shared/SectionRefreshState.test.tsx apps/web/src/features/market-overview/MarketOverviewView.test.tsx`.

Expected: PASS.

- [ ] **Step 6: Commit**

Run `git add apps/web/src/shared/SectionRefreshState.tsx apps/web/src/shared/SectionRefreshState.test.tsx apps/web/src/features/market-overview/MarketOverviewView.tsx apps/web/src/features/market-overview/overview.css && git commit -m "fix: preserve overview snapshot on refresh failure"`.

### Task 4: Full verification and portable EXE

**Files:**
- Modify: `docs/verification/2026-08-24-overview-density-timeout-recovery.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

**Interfaces:**
- Consumes: source changes and existing build/smoke scripts.
- Produces: clean portable EXE, smoke evidence, restore evidence, and memory update.

- [ ] **Step 1: Run web and API checks**

Run `pnpm --filter @qibao/web test -- --run`, `pnpm --filter @qibao/web build`, API tests, Ruff, UTF-8/mojibake scan, and `git diff --check`.

- [ ] **Step 2: Build portable EXE**

Run `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1` and preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, `backups`.

- [ ] **Step 3: Run real smoke and restore gates**

Run cold/hot `scripts/run-portable-smoke.ps1 -UseReleaseData`, `scripts/verify-restore-drill.ps1 -ReleaseRoot dist\\XiaoQiBao-Portable -UpdateManifest`, and `scripts/verify-release-quality.ps1 -ReleaseRoot dist\\XiaoQiBao-Portable`.

- [ ] **Step 4: Record evidence**

Record actual commit, EXE path/hash, test counts, startup timings, restore status, and any truthful `partial/unavailable` data states. Do not claim ready for missing sources.

- [ ] **Step 5: Commit evidence**

Run `git add docs/verification/2026-08-24-overview-density-timeout-recovery.md && git commit -m "docs: record overview density recovery evidence"`.
