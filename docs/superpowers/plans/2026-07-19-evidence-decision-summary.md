# 证据决策摘要实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在右侧单股驾驶舱顶部加入由现有核验快照驱动的新手证据决策摘要。

**Architecture:** 在 `StockDecisionCockpit.tsx` 内增加纯展示 `EvidenceDecisionSummary` 和 `preparationForSummary` 回退计算，复用现有 `StockAssessment`、`StockPreparation` 与 `StockCockpitSnapshot`。通过现有 CSS 令牌增加桌面四列、移动单列布局，不修改 API 或服务端计算。

**Tech Stack:** React 19、TypeScript 5、Vitest、Testing Library、现有 CSS 设计令牌。

## Global Constraints

- 摘要不生成新行情、价格、概率或买卖指令。
- 数据不足时必须降低证据等级，不得显示为高可信结论。
- 保留现有行动卡、个股情绪、市场情绪、阶段时间线和数据详情。
- 中文文件使用 UTF-8 和 `apply_patch` 编辑。

---

### Task 1: 证据决策摘要

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: `StockCockpitSnapshot`.
- Produces: `<section role="region" aria-label="证据决策摘要">`，位于 `PreparationStatus` 之后、`AssessmentConclusion` 之前。

- [x] **Step 1: 写完整和部分证据的失败测试**
- [x] **Step 2: 运行测试确认摘要尚不存在时失败**
- [x] **Step 3: 实现回退计数、证据等级和新手摘要**
- [x] **Step 4: 添加桌面四列与窄屏单列样式**
- [x] **Step 5: 运行单测确认通过**

Run: `npm test -- src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: `23 passed`。

### Task 2: 完整验证

- [ ] **Step 1: 运行前端全套测试**

Run: `npm test`

- [ ] **Step 2: 运行生产构建**

Run: `npm run build`

- [ ] **Step 3: 扫描编码和差异**

Run: UTF-8/mojibake scan and `git diff --check`。
