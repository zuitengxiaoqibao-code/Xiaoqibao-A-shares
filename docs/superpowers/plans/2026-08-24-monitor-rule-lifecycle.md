# 监控规则生命周期与条件管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为监控中心补齐规则暂停、恢复、停止删除和条件删除能力，形成可控、可恢复、可审计的规则操作闭环。

**Architecture:** 后端新增按规则 ID 的状态更新与删除接口；暂停会停止后续评估并关闭该规则的活跃告警，删除会移除规则但保留告警审计记录。前端规则卡片显示生命周期状态和操作按钮，高级编辑器每行提供删除条件按钮，最后一个条件保留但置灰，保存前继续由后端校验。

**Tech Stack:** FastAPI、Python、React 19、TypeScript、Vitest、Testing Library、现有 `apiClient` 和监控规则 DSL。

## Global Constraints

- Windows EXE 是唯一用户交付入口，不交付 HTML 或 localhost。
- 规则默认不启用，不自动发送告警；暂停和删除操作必须可追溯。
- 中文界面不得把英文内部字段路径作为主要操作说明。
- 保留旧版单条件规则、已有模板和高级规则 DSL 兼容。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。

### Task 1: 后端规则生命周期 API

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/monitor_center.py`
- Modify: `apps/api/src/qibao_api/routes/monitor_center.py`
- Test: `apps/api/tests/a_shares/test_monitor_center.py`
- Test: `apps/api/tests/routes/test_monitor_center.py`

**Interfaces:**
- `MonitorCenterService.set_rule_enabled(rule_id: str, enabled: bool) -> dict[str, Any]`
- `MonitorCenterService.delete_rule(rule_id: str) -> dict[str, str]`
- `PATCH /api/v1/monitor-center/rules/{rule_id}/status` with `{ "enabled": boolean }`
- `DELETE /api/v1/monitor-center/rules/{rule_id}`

- [ ] **Step 1: Write failing tests**

增加测试：暂停规则后 `enabled=false`、再次恢复为 `true`；暂停会把该规则的活跃告警标记为 `recovered` 并记录“规则已暂停”；删除不存在规则返回 404，删除存在规则后规则列表不再包含它但告警历史仍可查询。

- [ ] **Step 2: Run focused tests and verify red**

Run: `& '.venv\\Scripts\\python.exe' -m pytest apps/api/tests/a_shares/test_monitor_center.py apps/api/tests/routes/test_monitor_center.py -q`

Expected: FAIL because lifecycle service methods and routes do not exist.

- [ ] **Step 3: Implement minimal service lifecycle methods**

在服务锁内按规则 ID 定位规则；状态更新只改 `enabled`，暂停时遍历该规则的活跃告警，设置 `state=recovered`、`recovered_at`、`recovery_reason=规则已暂停`，并移除对应 `active_conditions`。删除只移除规则，不删除告警历史，找不到规则抛出 `KeyError("监控规则不存在")`。

- [ ] **Step 4: Add routes and Chinese errors**

路由捕获 `KeyError` 返回 404，捕获 `ValueError` 返回 422；状态接口校验 `enabled` 必须为布尔值。

- [ ] **Step 5: Run focused tests and verify green**

Run the same pytest command. Expected: all lifecycle and existing monitor tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/qibao_api/a_shares/monitor_center.py apps/api/src/qibao_api/routes/monitor_center.py apps/api/tests/a_shares/test_monitor_center.py apps/api/tests/routes/test_monitor_center.py
git commit -m "feat: add monitor rule lifecycle controls"
```

### Task 2: 前端暂停、恢复、删除和条件操作

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`

**Interfaces:**
- `setRuleEnabled(rule: Rule, enabled: boolean) -> Promise<void>` calls the status endpoint and reloads state.
- `deleteRule(rule: Rule) -> Promise<void>` calls the delete endpoint and clears the editor if the deleted rule is selected.
- `removeCondition(index: number)` remains safe when one condition remains.

- [ ] **Step 1: Write failing interaction tests**

增加测试：已启用规则卡片显示“暂停监控”；点击后向 `/rules/{id}/status` 发送 `PATCH {enabled:false}` 并显示“已暂停”；已暂停规则显示“恢复监控”和“停止并删除”；删除二次确认后调用 DELETE；增加第二条条件后每行显示“删除条件”，删除后只剩一条时按钮置灰；最后一条条件不能被删空。

- [ ] **Step 2: Run focused Web tests and verify red**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: FAIL because lifecycle buttons and condition delete controls are not rendered.

- [ ] **Step 3: Implement lifecycle actions and rule list cards**

将已保存规则从单个包裹按钮改为可读卡片，显示“监控中/已暂停”状态；新增暂停、恢复、停止并删除按钮。删除前使用 `window.confirm("确定停止并删除这条监控规则吗？")`，失败显示中文错误；模板按钮按状态切换为启用、暂停或恢复。

- [ ] **Step 4: Implement condition deletion affordance**

每条条件行显示带 `Trash2` 图标的“删除条件”按钮；仅剩一条时按钮 `disabled` 并保留 `title="至少保留一个条件"`。增加/删除后同步首条条件的兼容字段，确保请求体仍可被旧后端识别。

- [ ] **Step 5: Add compact responsive styles**

增加规则操作区、生命周期状态和条件删除按钮样式；桌面端横向排列，窄屏自动折行，按钮文字不换行，禁用态明确但不隐藏。

- [ ] **Step 6: Run focused tests and verify green**

Run: `pnpm --dir apps/web exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`

Expected: all monitor-center tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/features/monitor-center/MonitorCenterView.tsx apps/web/src/app/theme.css apps/web/src/features/monitor-center/MonitorCenterView.test.tsx
git commit -m "feat: add monitor pause delete and condition controls"
```

### Task 3: 全量验证与便携 EXE

**Files:**
- Create: `docs/verification/2026-08-24-monitor-rule-lifecycle.md`

- [ ] **Step 1: Run full Web and API tests**

Run: `pnpm.cmd --dir . --filter "@qibao/web" test -- --maxWorkers=2` and `& '.venv\\Scripts\\python.exe' -m pytest apps/api/tests -q`.

- [ ] **Step 2: Run build and encoding checks**

Run: `pnpm --dir apps/web build`; run the touched-file UTF-8/乱码扫描 and `git diff --check`.

- [ ] **Step 3: Rebuild portable EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`; preserve `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。

- [ ] **Step 4: Run ordered smoke, restore drill and release quality gate**

Run `scripts/run-portable-smoke.ps1 -UseReleaseData -StartupKind hot`, then `scripts/verify-restore-drill.ps1 -UpdateManifest`, then `scripts/verify-release-quality.ps1`.

- [ ] **Step 5: Record evidence and commit**

将测试计数、EXE 路径、SHA-256、规则生命周期行为、真实数据边界和恢复结果写入验证文档并提交。

