# 监控规则模板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在监控中心提供默认停用的中文常用规则模板，并让默认规则使用真实快照字段，用户可一键启用且能看懂当前状态。

**Architecture:** 模板定义和中文解释放在监控中心前端，与现有规则编辑器共用 `RuleDraft` 和保存接口；稳定模板 ID 让重复启用变成更新，不增加新的后端持久化格式。规则列表通过现有摘要和告警数据计算“未启用/监控中/最近触发/暂无数据”等状态。

**Tech Stack:** React 19、TypeScript、Vitest、Testing Library、现有 `apiClient` 和 FastAPI 监控规则 DSL。

## Global Constraints

- 默认模板必须停用，不自动发送站内、语音或飞书告警。
- 只预置已有真实总线发布者的四个主题：市场总览、量化策略、新闻热点、尾盘选股。
- 模板真实字段必须使用 `regime.risk_score`、`verified_count`、`candidate_count` 等后端快照路径。
- 保留旧版单条件规则和现有高级规则编辑器兼容性。
- 中文界面不得展示英文字段路径作为主要说明。

### Task 1: Add template model and real default field mapping

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Test: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`

**Interfaces:**
- Add `MonitorRuleTemplate`, `RuleDraft.template_id?`, `RuleDraft.explanation?` types.
- Add exported-for-test-safe helpers `defaultRule()` and `templateDraft(template)` only if needed by component tests; otherwise test through rendered UI.

- [ ] **Step 1: Write failing tests**

Add tests asserting the initial editor uses `regime.risk_score`, four template cards are visible, and the template text contains Chinese source and trigger explanations.

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: FAIL because the current editor has no template cards and still posts `{risk_score: {gte: 65}}`.

- [ ] **Step 3: Implement the minimal definitions and default mapping**

Add stable template definitions:

```ts
const monitorRuleTemplates: MonitorRuleTemplate[] = [
  { id: "monitor-market-risk", name: "市场风险升高提醒", topic: "market_overview", field: "regime.risk_score", operator: "gte", threshold: 65, source: "市场总览实时快照", explanation: "市场风险分达到 65 以上时提醒，优先检查风险闸门和仓位。" },
  { id: "monitor-quant-risk", name: "量化策略风险升高提醒", topic: "quant_strategy", field: "regime.risk_score", operator: "gte", threshold: 65, source: "量化策略实时快照", explanation: "量化策略使用的市场风险分达到 65 以上时提醒。" },
  { id: "monitor-news-arrival", name: "新闻热点出现提醒", topic: "news_events", field: "verified_count", operator: "gt", threshold: 0, source: "已核验新闻快照", explanation: "出现已核验新闻事件时提醒，避免把未核验内容当成信号。" },
  { id: "monitor-late-candidate", name: "尾盘候选出现提醒", topic: "late_session_candidates", field: "candidate_count", operator: "gt", threshold: 0, source: "尾盘选股实时快照", explanation: "尾盘筛选产生候选股票时提醒，具体结果仍需查看筛选规则和数据状态。" },
];
```

Set the new editor default and recovery field to `regime.risk_score`; keep legacy root `risk_score` in the label map for old saved rules.

- [ ] **Step 4: Run focused tests and verify green**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: new template/default assertions pass; update the existing request expectation to the real nested path.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/monitor-center/MonitorCenterView.tsx apps/web/src/features/monitor-center/MonitorCenterView.test.tsx
git commit -m "feat: add monitor rule templates"
```

### Task 2: Add one-click enable and readable status explanations

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`

**Interfaces:**
- `templateDraft(template)` returns a complete `RuleDraft` with stable ID, one condition, safe channel defaults, and no required freshness gate.
- `saveRuleDraft(draft, notice)` posts through the existing `/api/v1/monitor-center/rules` endpoint and reloads state.

- [ ] **Step 1: Write failing interaction tests**

Add tests that click “启用此规则” on the market-risk template and assert the POST body contains `id: "monitor-market-risk"`, `topics: ["market_overview"]`, and `{ "regime.risk_score": { "gte": 65 } }`; assert the card changes to “监控中” and displays the saved explanation.

Add a test that supplies a matching saved rule and summary without alerts, then asserts the card shows “监控中” rather than “未启用”.

- [ ] **Step 2: Run focused tests and verify the expected failure**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: FAIL because the enable button and template state do not exist.

- [ ] **Step 3: Implement one-click enable and status derivation**

Implement `templateDraft`, `rulePayload(draft = rule)`, and `saveRuleDraft`. Use stable IDs so the existing backend replacement-by-ID behavior prevents duplicates. Derive status as:

```ts
const templateStatus = (template: MonitorRuleTemplate) => {
  const saved = rules.find((item) => item.id === template.id);
  if (!saved) return "未启用";
  const matchingTopic = current.topics.find((item) => item.topic === template.topic);
  if (matchingTopic?.status === "no_data") return "暂无数据";
  const recent = alerts.find((item) => item.rule_id === template.id);
  return recent ? "最近触发" : "监控中";
};
```

Render a compact template grid above the manual editor. Each card includes the Chinese condition, source, explanation, status chip, and a button labeled “启用此规则” or “已启用”. Keep the advanced editor available below it.

- [ ] **Step 4: Add focused styles and verify responsive layout**

Add `.monitor-template-grid`, `.monitor-template-card`, `.monitor-template-meta`, and `.monitor-template-explanation` to `apps/web/src/app/theme.css`; use an auto-fit grid, compact spacing, readable 14px body text, and a mobile single-column fallback.

- [ ] **Step 5: Run focused tests and verify green**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: all monitor-center tests pass, including one-click enable and status tests.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/features/monitor-center/MonitorCenterView.tsx apps/web/src/app/theme.css apps/web/src/features/monitor-center/MonitorCenterView.test.tsx
git commit -m "feat: explain monitor templates for beginners"
```

### Task 3: Full verification and portable EXE delivery

**Files:**
- Modify: none unless verification exposes a regression.
- Verify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`, `apps/web/src/app/theme.css`, `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`

- [ ] **Step 1: Run monitor-center and full Web tests**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center`

Then run: `pnpm.cmd --dir . --filter "@qibao/web" test -- --maxWorkers=2`

- [ ] **Step 2: Run TypeScript/Vite production build**

Run: `pnpm --dir apps/web build`

- [ ] **Step 3: Run UTF-8/Chinese mojibake and diff checks**

Run the repository's existing UTF-8 scan and `git diff --check`; fail on replacement characters or repeated question marks in touched UI files.

- [ ] **Step 4: Rebuild the portable EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`.

Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` as required by `AGENTS.md`.

- [ ] **Step 5: Run the actual EXE smoke verification**

Run the existing `scripts/run-portable-smoke.ps1` against the rebuilt release, then run the release quality gate. Do not close or control 通达信 or the user's desktop.

- [ ] **Step 6: Commit verification documentation**

Record the test counts, EXE path, hash, and rule-template behavior in `docs/verification/2026-08-24-monitor-rule-templates.md`, then commit the implementation and verification notes.
