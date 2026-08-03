# A 股关键状态仪表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在单股分析页顶部增加由真实数据驱动的关键状态仪表，并突出行动、证据、情绪与风险之间的关系。

**Architecture:** 新建独立的 `KeySignalDashboard` 展示组件，接收当前确定性评估、证据覆盖和可选个股情绪快照。`StockDecisionCockpit` 继续负责数据装配，并用新仪表替换现有重复的结论头部和置信度区域；其余 AI、阶段、清单和详细证据保持不变。

**Tech Stack:** React 19、TypeScript 5.8、CSS custom properties、Vitest、Testing Library

## Global Constraints

- 只使用已有可验证数据，不生成风险分、收益概率或默认情绪分。
- 圆环仅用于真实的 0-100 数值。
- 行动与风险使用分类状态，不转换成数值。
- 保留现有路由、API、候选列表字段和详细分析数据流。
- 桌面四栏、中等屏幕两栏、手机单栏且无横向滚动。
- 使用 `apply_patch` 修改中文文件，并在完成后执行 UTF-8 与乱码扫描。

---

### Task 1: 关键状态仪表组件

**Files:**
- Create: `apps/web/src/features/stock-cockpit/KeySignalDashboard.tsx`
- Create: `apps/web/src/features/stock-cockpit/KeySignalDashboard.test.tsx`

**Interfaces:**
- Consumes: `StockAssessment`, `StockCockpitSnapshot["overall_quality"]`, `CandidateSentimentSnapshot | null`, `readySources: number`, `totalSources: number`
- Produces: `KeySignalDashboard(props)` React component with accessible meter elements

- [ ] **Step 1: Write failing component tests**

Test a ready `observe` assessment with 85% confidence, 6/6 evidence and a 71-point positive sentiment. Assert four dashboard cells, `meter` values, action tone, primary risk, and no conflict notice. Add cases for `avoid` plus positive sentiment, partial coverage, and unavailable sentiment.

- [ ] **Step 2: Run the component test and verify failure**

Run: `npm test -- src/features/stock-cockpit/KeySignalDashboard.test.tsx`

Expected: FAIL because `KeySignalDashboard.tsx` does not exist.

- [ ] **Step 3: Implement the minimal dashboard component**

Implement bounded percentage parsing, candidate sentiment labels, a CSS-driven `SignalGauge`, categorical action presentation, evidence quality tone, unavailable sentiment fallback, primary risk summary, and the positive-sentiment/non-observe conflict notice.

- [ ] **Step 4: Run the component test and verify pass**

Run: `npm test -- src/features/stock-cockpit/KeySignalDashboard.test.tsx`

Expected: all dashboard component tests PASS.

### Task 2: 驾驶舱集成与去重

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

**Interfaces:**
- Consumes: `KeySignalDashboard` from Task 1
- Produces: the existing `EvidenceDecisionSummary` with the new dashboard at its top

- [ ] **Step 1: Update integration tests first**

Assert that the evidence summary contains “关键状态仪表”, preserves the current action and evidence coverage, surfaces matching candidate sentiment, and no longer renders the old separate verdict layout.

- [ ] **Step 2: Run targeted cockpit tests and verify failure**

Run: `npm test -- src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: FAIL until the dashboard receives the current candidate sentiment and replaces the old header/verdict markup.

- [ ] **Step 3: Integrate the dashboard**

Pass the matching candidate sentiment into `EvidenceDecisionSummary`, render `KeySignalDashboard` with assessment and prepared-source counts, remove the old duplicated confidence/verdict markup, and keep the detailed evidence, AI explanation, phase status, checklist and footer unchanged.

- [ ] **Step 4: Run targeted cockpit tests and verify pass**

Run: `npm test -- src/features/stock-cockpit/StockDecisionCockpit.test.tsx src/features/stock-cockpit/KeySignalDashboard.test.tsx`

Expected: all targeted tests PASS.

### Task 3: 专业仪表视觉与响应式布局

**Files:**
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: dashboard classes and `--gauge-value` from Task 1
- Produces: stable four/two/one-column layout and semantic gauge colors

- [ ] **Step 1: Add dashboard styles**

Add a four-column grid with a wider action cell, CSS conic-ring meters, restrained separators, fixed gauge dimensions, semantic action/evidence/sentiment tones, and a full-width risk alert. Reuse the existing `--focus-*` tokens.

- [ ] **Step 2: Add responsive rules**

At 900px switch the dashboard to two columns; at 520px switch to one column. Keep ring size fixed and ensure long Chinese risk text wraps.

- [ ] **Step 3: Run production checks**

Run: `npm test`

Expected: 31 test files and at least 212 tests PASS.

Run: `npm run build`

Expected: TypeScript and Vite production build PASS.

- [ ] **Step 4: Run source safety checks**

Run `git diff --check`, strict UTF-8 decoding, and a replacement-character/repeated-question-mark scan for all touched Chinese UI files.

Expected: no malformed diff, invalid UTF-8 or mojibake matches.

- [ ] **Step 5: Inspect the actual page**

Check `http://localhost:5173/a-shares?symbol=603629` at the normal desktop viewport and 390px mobile width. Confirm real values render, action and conflict warnings use the correct tones, and `scrollWidth === clientWidth` on mobile.
