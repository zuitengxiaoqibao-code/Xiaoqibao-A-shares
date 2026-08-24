# 监控规则 DSL 与分层实时引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为监控中心实现兼容旧配置的组合规则 DSL、连续确认/冷却/恢复/新鲜度门控和更高自由度的规则配置界面。

**Architecture:** 在 `MonitorCenterService` 内增加纯函数式规则标准化、条件评估和触发状态机；实时总线继续负责事件分发，规则引擎只处理相关快照并拒绝过期数据。前端保持现有摘要仪表盘和 API，规则配置扩展为动态条件表单，并展示结构化规则预览。

**Tech Stack:** FastAPI、Python JSON 持久化、RealtimeSnapshotBus、React、TypeScript、Vitest。

## Global Constraints

- 保持旧 `conditions` JSON 读取兼容，不迁移或破坏已有规则。
- 真实数据缺失、过期或来源不可信时禁止触发，不生成模拟行情或 AI 结论。
- 所有用户可见错误使用中文；规则保存必须通过后端校验。
- 不新增外部服务；EXE 是唯一交付入口。
- 修改中文文件后运行 UTF-8/乱码扫描、`git diff --check` 和对应测试。

---

### Task 1: 规则标准化与校验

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/monitor_center.py`
- Create: `apps/api/tests/a_shares/test_monitor_rule_dsl.py`

**Interfaces:**
- `MonitorCenterService.normalize_rule(rule) -> dict[str, Any]`
- `MonitorCenterService.validate_rule(rule) -> dict[str, Any]`
- `MonitorCenterService._matches(snapshot, conditions) -> bool` 保持旧调用兼容，并支持标准化条件列表。

- [ ] **Step 1: Write failing tests** for old-format conversion, all/any/n_of conditions, invalid operators, negative windows and missing fields.
- [ ] **Step 2: Run** `.venv\Scripts\python.exe -m pytest -q apps/api/tests/a_shares/test_monitor_rule_dsl.py`; verify failures are due to missing standardization/validation.
- [ ] **Step 3: Implement** supported operators, condition list normalization, logic evaluation and Chinese validation errors; keep old `{field: {op: value}}` behavior unchanged.
- [ ] **Step 4: Run focused tests and Ruff**; confirm old monitor-center tests remain green.
- [ ] **Step 5: Commit** `feat: add monitor rule dsl validation`.

### Task 2: 实时状态机与新鲜度门控

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/monitor_center.py`
- Modify: `apps/api/tests/a_shares/test_monitor_rule_dsl.py`

**Interfaces:**
- `MonitorCenterService.evaluate()` accepts normalized rules and returns `None` for stale/incomplete snapshots.
- Persist per-rule/symbol/topic confirmation state under `condition_states`.
- Existing `evaluate_recovery()` continues producing one recovery event.

- [ ] **Step 1: Write failing tests** for `confirm_count`, `confirm_window_seconds`, `cooldown_seconds`, `freshness_seconds`, stale snapshot rejection and custom recovery conditions.
- [ ] **Step 2: Run** the focused test file and observe expected failures.
- [ ] **Step 3: Implement** state transitions: pending -> active after consecutive confirmations, reset after window break, cooldown dedupe, freshness gate and recovery condition evaluation.
- [ ] **Step 4: Add runtime subscription coverage** for `stock_observation` and `data_sources` without blocking existing topics.
- [ ] **Step 5: Run monitor service and runtime tests; commit** `feat: add realtime monitor rule state machine`.

### Task 3: Rule configuration API contract

**Files:**
- Modify: `apps/api/src/qibao_api/routes/monitor_center.py`
- Modify: `apps/api/tests/routes/test_monitor_center.py`

**Interfaces:**
- `POST /api/v1/monitor-center/rules` validates and returns normalized rule.
- `GET /api/v1/monitor-center/rules` returns normalized rules with `condition_summary` and `validation_state`.

- [ ] **Step 1: Add route tests** for normalized response, invalid condition payload, unknown operator, stale parameter rejection and legacy payload acceptance.
- [ ] **Step 2: Run** route tests to confirm failures.
- [ ] **Step 3: Wire `save_rule()` through `validate_rule()` and return Chinese `HTTPException` details.
- [ ] **Step 4: Run route tests and API monitor regression; commit** `feat: expose validated monitor rules`.

### Task 4: Flexible rule builder UI

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Rule draft supports `logic`, `conditions[]`, `confirm_count`, `confirm_window_seconds`, `cooldown_seconds`, `freshness_seconds`, `severity` and `recovery`.
- Save request posts normalized DSL while preserving channels and topics.

- [ ] **Step 1: Write failing UI tests** for adding/removing condition rows, all/any selector, realtime parameters, severity selector, JSON preview and save payload.
- [ ] **Step 2: Run** focused Vitest and observe failures.
- [ ] **Step 3: Implement dynamic condition editor and numeric validation; preserve old single-condition rule editing.
- [ ] **Step 4: Add compact responsive CSS and Chinese validation states.
- [ ] **Step 5: Run focused UI, layout-safety and TypeScript tests; commit** `feat: add flexible monitor rule builder`.

### Task 5: Full verification and portable EXE

**Files:**
- Create: `docs/verification/2026-08-24-monitor-rule-dsl.md`

- [ ] **Step 1: Run** API full tests, Web full tests, Ruff, TypeScript/Vite build, UTF-8 scan and `git diff --check`.
- [ ] **Step 2: Run** `scripts/build-portable.ps1 -SkipTests` and preserve all persistent directories.
- [ ] **Step 3: Run** `scripts/run-portable-smoke.ps1 -UseReleaseData -StartupKind hot` and confirm the rule save/summary endpoints.
- [ ] **Step 4: Run** restore drill and release quality verification.
- [ ] **Step 5: Record test counts, EXE hash, truthful partial/unavailable states and commits in the verification document; commit** `docs: verify monitor rule dsl`.
