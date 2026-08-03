# A 股自选股市场情绪实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让自选股列表与候选列表保持代码/名称/候选分一致，并把全市场情绪移动到点击自选股后的右侧详情。

**Architecture:** 保留独立 `WatchlistMarketSentiment` 表示组件，复用已有情绪响应类型和加载函数。`StockSelector` 只负责自选列表行，`StockDecisionCockpit` 在选择来源为 `watchlist` 时挂载情绪组件，`Dashboard` 将加载函数传给右侧驾驶舱。

**Tech Stack:** React 19、TypeScript 5、Vitest、Testing Library、现有 CSS 设计令牌。

## Global Constraints

- 情绪始终是 A 股全市场环境，不得冒充个股评分。
- 不重新计分，不修改 `MarketSentimentResponse`，不新增 API。
- 失败和不可用状态不得阻断自选列表。
- 只在点击自选股并进入右侧驾驶舱后挂载和请求。
- 自选列表只显示代码、名称和候选分；没有候选快照时显示 `--`。
- 辅助文字不小于 12px，移动端操作目标不小于 44px。
- 保留 dirty worktree；不 stage、commit 或 push。

---

### Task 1: 紧凑自选情绪组件

**Files:**
- Create: `apps/web/src/features/market-sentiment/WatchlistMarketSentiment.tsx`
- Create: `apps/web/src/features/market-sentiment/WatchlistMarketSentiment.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `load: () => Promise<MarketSentimentResponse>`
- Produces: `<WatchlistMarketSentiment load={load} />`

- [x] **Step 1: 写失败测试**

覆盖部分可用且陈旧的真实分数、无分数不可用、请求失败与重试。明确断言“A 股全市场环境”和“不是个股评分”。

- [x] **Step 2: 运行测试并确认 RED**

Run: `pnpm --filter @qibao/web test -- WatchlistMarketSentiment.test.tsx`

Expected: 因组件模块不存在而失败。

- [x] **Step 3: 实现最小组件和样式**

使用 `current ?? previous_close`；根据 `band`、`quality`、`freshness` 生成冻结展示；错误状态提供 44px 重试按钮；不生成新数字。

- [x] **Step 4: 运行测试并确认 GREEN**

Run: `pnpm --filter @qibao/web test -- WatchlistMarketSentiment.test.tsx`

Expected: all tests pass.

---

### Task 2: 自选列表与右侧详情接线

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`

**Interfaces:**
- Extends: `StockDecisionCockpit` with optional `loadMarketSentiment?: () => Promise<MarketSentimentResponse>`
- Reuses: existing `Dashboard.loadMarketSentiment`

- [x] **Step 1: 写列表精简与右侧懒加载失败测试**

断言自选行只显示代码/名称/候选分，左侧不请求或显示情绪；点击自选股后右侧请求一次并显示紧凑区域。

- [x] **Step 2: 运行测试并确认 RED**

Run: `pnpm --filter @qibao/web test -- StockSelector.test.tsx`

Expected: `StockSelector` 未渲染自选情绪。

- [x] **Step 3: 实现最小接线**

让 `WatchlistRow` 复用候选分，移除左侧情绪挂载；向 `StockDecisionCockpit` 传入现有 `loadMarketSentiment`，仅在选择来源为 `watchlist` 时渲染 `WatchlistMarketSentiment`。

- [x] **Step 4: 运行相关测试并确认 GREEN**

Run: `pnpm --filter @qibao/web test -- StockSelector.test.tsx Dashboard.test.tsx`

Expected: all tests pass.

- [x] **Step 5: 完整验证**

Run: `pnpm test:web`

Run: `pnpm build`

严格 UTF-8 解码所有代码与文档，扫描替换字符、常见乱码和连续问号，运行 `git diff --check`。

Expected: 零测试失败、构建成功、零编码错误、零乱码、无空白错误。
