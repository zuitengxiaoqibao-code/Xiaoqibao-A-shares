# 数据源健康与故障转移可观测性实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 持久化通达信节点和百度历史源的调用质量，并在新手数据设置中展示可读的来源健康信息。

**Architecture:** 在现有 `operations.sqlite3` 中新增 append-only 来源事件表。通达信 failover client 与百度历史源通过可选回调写事件；仓储按最近 20 条事件聚合；只读 API 和 DataSettingsView 负责展示。来源健康不会进入研判计算链路。

**Tech Stack:** Python 3.12、SQLite、FastAPI/Pydantic、React/TypeScript、Vitest、pytest、Ruff。

## Global Constraints

- A 股为主，转债域不与 A 股状态混合。
- 不恢复模拟资金、账户、委托、成交或自动交易。
- 中文文件使用 `apply_patch` 修改，并执行严格 UTF-8 与乱码扫描。
- AI 只能解释已冻结证据，来源健康不改变动作、数字、置信度或风险门禁。

### Task 1: 来源事件契约与持久化聚合

**Files:**
- Create: `apps/api/src/qibao_api/contracts/source_health.py`
- Modify: `apps/api/src/qibao_api/shangshu/operations_repository.py`
- Test: `apps/api/tests/shangshu/test_operations_repository.py`

**Interfaces:** `SourceAttemptEvent` 表示单次来源尝试；`OperationsRepository.append_source_attempt(event)` 追加事件；`OperationsRepository.source_health(limit=20)` 返回聚合字典。

- [x] Write a failing test for append-only source events and the recent-window aggregation.
- [x] Run the focused test and confirm it fails because the event table/API is absent.
- [x] Add the frozen event model, SQLite table/triggers, append method, and aggregation with `ready/degraded/unavailable` status and success rate.
- [x] Run the focused repository tests and confirm they pass.

### Task 2: Instrument TDX and Baidu history calls

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_client.py`
- Modify: `apps/api/src/qibao_api/gongbu/baidu_history.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/gongbu/test_tdx_client.py`
- Test: `apps/api/tests/gongbu/test_baidu_history.py`

**Interfaces:** `create_tdx_client(..., observer=None)` and `BaiduHistorySource(..., observer=None)` accept a callback compatible with `OperationsRepository.append_source_attempt`.

- [x] Write failing tests for per-node TDX events, observer isolation, and Baidu quality metadata.
- [x] Run focused tests and confirm the missing observer behavior.
- [x] Add monotonic timing, structured error codes, and callback-safe event emission; wire a shared repository callback in lifespan without changing default test constructors.
- [x] Run focused tests and confirm failover behavior remains green.

### Task 3: Read-only source-health API

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Test: `apps/api/tests/routes/test_operations.py`

**Interfaces:** `GET /api/v1/operations/source-health` returns `{sources: [...], window_size, generated_at}` with no raw exception text or secrets.

- [x] Write a failing route test with a fake repository.
- [x] Run the route test and confirm the endpoint is missing.
- [x] Add the dependency and response model/serialization, then run focused route tests.

### Task 4: Beginner data-settings display

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`

**Interfaces:** `SourceHealthLoader` loads the API response; the view shows source name, status, success rate, latency, last success/failure and Baidu freshness metadata.

- [x] Write failing component tests for no events, degraded, and unavailable source states.
- [x] Run focused Vitest and confirm the health section is absent.
- [x] Add API wiring and a compact responsive source-health section using existing visual tokens and no trading language.
- [x] Run focused Vitest and confirm all states render.

### Task 5: Verification and roadmap

**Files:**
- Modify: `docs/roadmap.md`

- [x] Run API tests, Ruff, Web tests and production build.
- [x] Run strict UTF-8, scoped mojibake scan and `git diff --check`.
- [x] Restart the formal `8000/5173` services and verify source-health, search, cockpit and three-phase endpoints.
- [ ] Verify desktop/mobile browser views have no console errors or page overflow.
- [x] Record the delivered observability rule and keep remaining roadmap items explicit.

### Regression follow-up

- [x] `BarRepository.latest_many` now deduplicates append-only same-day revisions before ranking the historical window; regression coverage verifies a full 60-bar window and the latest revision.
