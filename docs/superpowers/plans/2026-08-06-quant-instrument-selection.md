# 量化分析标的选择 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让量化分析仪表盘恢复全局最近股票，并支持醒目的代码/名称搜索与任意已验证 A 股切换。

**Architecture:** 新建聚焦的 `QuantInstrumentSelector` 处理搜索和交互，`QuantAnalysisDashboard` 管理分析标的与数据资源，`Dashboard` 负责连接全局 URL 选择状态和现有股票目录接口。

**Tech Stack:** React、TypeScript、Vitest、Testing Library、现有本地 A 股搜索 API、PowerShell 便携构建脚本。

## Global Constraints

- 不修改后端量化公式和数据真实性规则。
- 任意股票的首次涨停专属因子只能来自其自身候选记录。
- 用户可见中文保持 UTF-8，字号不低于全站可读性规则。
- 最终交付入口为便携 EXE。

---

### Task 1: 标的选择器与全局恢复

**Files:**
- Create: `apps/web/src/features/quant-analysis/QuantInstrumentSelector.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`

**Interfaces:**
- Consumes: `InstrumentSearchResponse`、候选股票代码与名称、全局 `selectedSymbol`。
- Produces: `onSelect(symbol)` 选择事件和当前标的可见状态。

- [x] 先写测试：全局标的优先、名称搜索、自定义股票不冒充候选因子。
- [x] 运行聚焦测试并确认因缺少行为而失败。
- [x] 实现选择器和量化页状态优先级。
- [x] 重跑聚焦测试并确认通过。

### Task 2: Dashboard 接线与视觉强调

**Files:**
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `searchAShareInstruments`、`SelectedInstrument.select`。
- Produces: 量化页 URL 同步、醒目的右上角控制区和响应式布局。

- [x] 写 Dashboard 接线测试并确认失败。
- [x] 传入全局标的、搜索接口与选择回调，补充布局样式。
- [x] 运行量化、Dashboard 和布局安全测试。

### Task 3: 完整验证与 EXE 交付

**Files:**
- Create: `docs/verification/2026-08-06-quant-instrument-selection.md`

**Interfaces:**
- Consumes: 完成后的前端源码和便携构建脚本。
- Produces: 测试、构建、编码扫描和 EXE 烟测证据。

- [x] 运行前端全量测试和生产构建。
- [x] 扫描乱码、低于 12px 的新增可见文字和 diff 格式。
- [x] 运行 `scripts/build-portable.ps1`。
- [x] 运行 `scripts/run-portable-smoke.ps1`。
- [x] 记录 EXE 路径、SHA-256 和烟测结果并提交。
