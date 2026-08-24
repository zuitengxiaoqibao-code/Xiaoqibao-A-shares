# 监控中心升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将监控中心升级为覆盖全项目数据健康、风险告警、恢复状态和独立投递的实时控制台。

**Architecture:** 在现有 `MonitorCenterService` 和实时快照总线之上增加兼容旧规则的生命周期状态、摘要投影和健康投影；API 提供一次首屏摘要，前端用摘要首屏并以实时事件/轮询增量更新。所有状态来自真实快照、持久化审计和已存在的应用状态，不新增外部服务。

**Tech Stack:** FastAPI、Pydantic/JSON 持久化、Python threading、React、TypeScript、Vitest、现有 `apiClient` 和实时总线。

## Global Constraints

- 保持 Windows EXE 为唯一用户交付入口；不提供浏览器或 localhost 作为交付物。
- 规则和历史 JSON 格式向后兼容，旧规则无需迁移即可读取。
- 不生成模拟行情、模拟告警或虚假 AI 结论；缺失数据必须显示 `partial` 或 `unavailable`。
- 所有错误和状态文案使用中文；投递通道独立记录状态和失败原因。
- 修改中文文件后运行 UTF-8/乱码扫描、`git diff --check` 和对应测试。

---

### Task 1: Extend alert lifecycle and summary contracts

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/monitor_center.py`
- Create: `apps/api/tests/a_shares/test_monitor_center_upgrade.py`

**Interfaces:**
- `MonitorCenterService.evaluate()` continues returning an alert dictionary and accepts old rules.
- Add `MonitorCenterService.summary(*, now: datetime | None = None) -> dict[str, Any]`.
- Add `MonitorCenterService.confirm(alert_id: str, *, confirmed_by: str = "用户") -> dict[str, Any]`.
- Add `MonitorCenterService.evaluate_recovery(snapshot, observed_at, topic=None) -> dict[str, Any] | None`.

- [x] **Step 1: Write failing tests** for summary counts, confirmation, recovery events, severity defaults, and old rule compatibility.
- [x] **Step 2: Run** `..\\..\\.venv\\Scripts\\python.exe -m pytest -q tests/a_shares/test_monitor_center_upgrade.py`; verify the new methods fail before implementation.
- [x] **Step 3: Add lifecycle fields** to new alerts with defaults: `severity="warning"`, `state="active"`, `confirmed=false`, `trigger_count=1`, `recovered_at=null`, `recovery_alert_id=null`.
- [x] **Step 4: Persist active condition fingerprints** per rule/symbol/topic and emit a recovery record when a previously active fingerprint no longer matches.
- [x] **Step 5: Implement `summary()`** returning service heartbeat, rule counts, alert counts, delivery failures, pending deliveries, and per-topic health derived from recent alerts.
- [x] **Step 6: Implement `confirm()`** to mark one alert confirmed, persist timestamp/user, and return the updated alert.
- [x] **Step 7: Run the focused tests** and verify all pass; commit `feat: add monitor alert lifecycle summary`.

### Task 2: Add monitor summary and alert action routes

**Files:**
- Modify: `apps/api/src/qibao_api/routes/monitor_center.py`
- Modify: `apps/api/tests/routes/test_monitor_center.py`

**Interfaces:**
- `GET /api/v1/monitor-center/summary` returns the summary from Task 1.
- `POST /api/v1/monitor-center/alerts/{alert_id}/confirm` accepts optional `confirmed_by` and returns the alert.
- `POST /api/v1/monitor-center/alerts/{alert_id}/delivery/retry` accepts `channel` and returns the updated delivery state without re-evaluating the market snapshot.

- [x] **Step 1: Add route tests** for summary shape, 404 alert confirmation, invalid channel rejection, and retry state update.
- [x] **Step 2: Run** `..\\..\\.venv\\Scripts\\python.exe -m pytest -q tests/routes/test_monitor_center.py`; observe expected failures.
- [x] **Step 3: Implement routes** with existing dependency lookup and Chinese `HTTPException` details.
- [x] **Step 4: Add route path assertions** and run focused route tests.
- [x] **Step 5: Commit** `feat: expose monitor summary and alert actions`.

### Task 3: Build the monitor-center dashboard data layer

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Add TypeScript types for `MonitorSummary`, `MonitorTopicHealth`, and lifecycle-aware `Alert`.
- Add `jsonFetch<MonitorSummary>("/api/v1/monitor-center/summary")` as the first-load request.
- Preserve existing rule and notification endpoints for editing and configuration.

- [x] **Step 1: Add failing UI tests** for the summary KPI row, topic health cards, severity filter, confirm action, and loading failure fallback.
- [x] **Step 2: Run** `pnpm exec vitest run src/features/monitor-center/MonitorCenterView.test.tsx`; verify the new assertions fail.
- [x] **Step 3: Replace the separate alert-first layout** with a summary-first dashboard while keeping rule editor and notification configuration available below.
- [x] **Step 4: Add Chinese status labels** for live/cached/partial/unavailable, active/recovered/confirmed, and delivery states.
- [x] **Step 5: Add alert filters** for topic, severity, state, and symbol text; wire confirm buttons to the new route and refresh only the summary.
- [x] **Step 6: Add compact responsive CSS** for KPI cards, topic health cards, alert timeline, and narrow windows without large blank regions.
- [x] **Step 7: Run focused UI tests** and commit `feat: upgrade monitor center dashboard`.

### Task 4: Wire live summary refresh and cache-safe failure behavior

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`
- Inspect: `apps/web/src/shared/realtime/RealtimeProvider.tsx`

**Interfaces:**
- Subscribe to `monitor_alert` or existing realtime alert events when available; otherwise use the existing polling fallback.
- Keep the last valid `MonitorSummary` when a refresh fails and expose the Chinese reason beside the stale timestamp.

- [x] **Step 1: Add a failing test** where a refresh rejects after a valid summary and verify the previous summary remains visible.
- [x] **Step 2: Implement request generation/cleanup** so a hidden or unmounted view cannot overwrite newer summary state.
- [x] **Step 3: Add a 15-second visible-page refresh using the existing fallback tick**, paused when the page is hidden.
- [x] **Step 4: Run focused UI tests and the realtime provider tests**; commit `fix: keep monitor summary live and cache-safe`.

### Task 5: Full verification and portable EXE delivery

**Files:**
- No source changes unless a verification failure requires a focused fix.
- Update: `docs/verification/2026-08-24-monitor-center-upgrade.md`

- [ ] **Step 1: Run** `pnpm --filter @qibao/web test` and `..\\..\\.venv\\Scripts\\python.exe -m pytest -q apps/api`.
- [ ] **Step 2: Run** Ruff, TypeScript/Vite build, UTF-8/乱码 scan, and `git diff --check`.
- [ ] **Step 3: Commit source changes cleanly, then run** `scripts/build-portable.ps1 -SkipTests`.
- [ ] **Step 4: Run** `scripts/run-portable-smoke.ps1 -UseReleaseData -StartupKind hot` and verify the monitor-center endpoint is included in the 14-menu gate.
- [ ] **Step 5: Run** `scripts/verify-restore-drill.ps1 -ReleaseRoot dist\\XiaoQiBao-Portable -UpdateManifest` and `scripts/verify-release-quality.ps1 -ReleaseRoot dist\\XiaoQiBao-Portable`.
- [ ] **Step 6: Record test counts, EXE SHA-256, commit, and any truthful partial/unavailable data states in the verification document; commit `docs: verify monitor center upgrade`.
