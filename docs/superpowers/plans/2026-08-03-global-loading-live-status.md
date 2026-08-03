# 全站加载与实时监控状态 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让最新数据完成后进入实时监控态，并保证全站所有加载状态有持续动态反馈、失败状态有具体环节和原因。

**Architecture:** 扩展共享 `DailyRefreshStatus` 表达完成监控与结构化失败；在主题样式中为所有 `aria-busy` 容器提供统一的不确定进度动画；仅为未声明 busy 的现有加载容器补齐语义属性。

**Tech Stack:** React、TypeScript、Vitest、Testing Library、CSS animations、桌面 pywebview。

## Global Constraints

- 不生成虚假行情、研究结果或虚假百分比。
- 已有缓存时刷新失败必须保留完整缓存。
- 中文文件保持 UTF-8，手工修改使用 `apply_patch`。
- 最终只交付便携 EXE。

---

### Task 1: 实时监控与失败明细

**Files:**
- Create: `apps/web/src/shared/DailyRefreshStatus.test.tsx`
- Modify: `apps/web/src/shared/DailyRefreshStatus.tsx`
- Modify: `apps/web/src/shared/dailyRefreshStatus.css`

**Interfaces:**
- Consumes: `LoadProgress` 的真实 `stage`、`detail` 和 `percent`。
- Produces: 完成后的实时监控状态，以及“失败环节 / 失败对象 / 原因”结构。

- [ ] 写失败测试，断言完成态显示“已加载实时最新数据”“当前状态：实时监控中”和最新时间。
- [ ] 写失败测试，断言失败态显示失败环节、失败对象和原始原因。
- [ ] 运行测试确认因现有文案和结构缺失而失败。
- [ ] 实现完成监控态、完成轨道、实时脉冲和失败明细。
- [ ] 运行共享组件及两个缓存页面测试。

### Task 2: 全局加载动画保障

**Files:**
- Modify: `apps/web/src/app/layout-safety.test.ts`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: 页面已有的 `aria-busy="true"` 和 `.lucide-loader-circle`。
- Produces: 不确定进度扫描轨道、加载区域脉冲和统一图标旋转。

- [ ] 写失败测试，断言主题样式包含 `[aria-busy="true"]::after` 和 `.lucide-loader-circle` 动画规则。
- [ ] 运行测试确认规则缺失。
- [ ] 实现只使用 transform/opacity 的低开销动画，并支持 `prefers-reduced-motion`。
- [ ] 运行布局和字体安全测试。

### Task 3: 补齐静态加载容器语义

**Files:**
- Modify: `apps/web/src/features/a-shares/AShareResearchView.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`
- Modify: `apps/web/src/features/market-sentiment/MarketSentimentDashboard.tsx`
- Modify: `apps/web/src/features/market-sentiment/WatchlistMarketSentiment.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/features/governance/GovernanceViews.tsx`

**Interfaces:**
- Consumes: Task 2 的全局 busy 动画。
- Produces: 所有主要静态加载容器的 `aria-busy="true"` 与 `role="status"`。

- [ ] 在现有页面测试中增加 busy 语义断言并确认失败。
- [ ] 为各加载容器补齐语义属性，不改变业务请求或数据。
- [ ] 运行涉及页面的定向测试。

### Task 4: 验证与桌面交付

**Files:**
- Create: `docs/verification/2026-08-03-global-loading-live-status.md`

**Interfaces:**
- Consumes: Tasks 1–3 的用户界面与测试结果。
- Produces: 重建后的便携 EXE、哈希和验证记录。

- [ ] 运行前端全量测试与生产构建。
- [ ] 运行后端全量测试。
- [ ] 运行严格 UTF-8、乱码扫描和 `git diff --check`。
- [ ] 运行 `scripts/build-portable.ps1 -SkipTests`。
- [ ] 运行 `scripts/run-portable-smoke.ps1`，确认实际 EXE 在 3 秒内显示窗口。
- [ ] 核对八个持久目录、SHA-256 和残留进程。
