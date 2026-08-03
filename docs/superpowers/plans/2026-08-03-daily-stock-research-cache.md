# 个股观察与公司研究当日缓存 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当天缓存先展示、最新真实数据后台刷新，并在个股观察提供醒目的公司研究入口。

**Architecture:** 新增共享缓存、流式 JSON 进度和缓存状态组件；两个业务页面只负责各自的刷新状态与展示。缓存按页面、日期、股票隔离，不修改后端业务数据。

**Tech Stack:** React、TypeScript、Vitest、Testing Library、浏览器 Fetch Streams、localStorage、桌面 pywebview。

## Global Constraints

- 用户只通过便携 EXE 验收。
- 不生成模拟行情、研究结论或虚假加载数据。
- 中文文件保持 UTF-8，手工修改使用 `apply_patch`。
- 刷新失败时必须保留已有缓存。

---

### Task 1: 共享当日缓存

**Files:**
- Create: `apps/web/src/shared/dailySnapshotCache.ts`
- Create: `apps/web/src/shared/dailySnapshotCache.test.ts`

- [ ] 写失败测试：当天快照可读、跨日和损坏快照不可读、同命名空间只保留最近 12 项。
- [ ] 运行测试确认因模块缺失而失败。
- [ ] 实现 `readDailySnapshot`、`writeDailySnapshot` 和清理逻辑。
- [ ] 运行测试确认通过。

### Task 2: 流式 JSON 加载进度

**Files:**
- Create: `apps/web/src/shared/fetchJsonWithProgress.ts`
- Create: `apps/web/src/shared/fetchJsonWithProgress.test.ts`
- Modify: `apps/web/src/features/stock-cockpit/api.ts`
- Modify: `apps/web/src/features/company-research/api.ts`

- [ ] 写失败测试：按响应字节报告进度并在解析后到 100%。
- [ ] 运行测试确认失败。
- [ ] 实现共享读取器并为两个加载函数增加可选进度回调。
- [ ] 运行共享及 API 测试。

### Task 3: 个股观察缓存与跳转

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/theme.css`

- [ ] 写失败测试：缓存立即展示、后台刷新替换、失败保留缓存、公司研究按钮保留股票代码。
- [ ] 运行定向测试确认失败。
- [ ] 接入共享缓存和进度状态，增加高亮跳转按钮。
- [ ] 运行定向测试确认通过。

### Task 4: 公司研究缓存与刷新状态

**Files:**
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.test.tsx`
- Modify: `apps/web/src/features/company-research/companyResearch.css`

- [ ] 写失败测试：缓存研究结果先展示、刷新进度可见、刷新成功替换、失败继续展示缓存。
- [ ] 运行定向测试确认失败。
- [ ] 为每个研究条目接入独立缓存时间和刷新状态。
- [ ] 运行定向测试确认通过。

### Task 5: 验证与桌面交付

**Files:**
- Create: `docs/verification/2026-08-03-daily-stock-research-cache.md`

- [ ] 运行前端定向与全量测试。
- [ ] 运行后端全量测试。
- [ ] 运行严格 UTF-8、乱码扫描和 `git diff --check`。
- [ ] 运行 `scripts/build-portable.ps1 -SkipTests`。
- [ ] 运行 `scripts/run-portable-smoke.ps1` 并确认实际 EXE 启动。
- [ ] 验证发布目录持久文件夹保留、计算 SHA-256、结束测试进程。
