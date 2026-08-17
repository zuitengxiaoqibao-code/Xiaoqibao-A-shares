# 尾盘选股 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增“尾盘选股”菜单，基于真实 A 股本地行情与历史日线，在 14:30 前预筛并在 14:30–15:00 增量监控七项规则。

**Architecture:** 新增独立的后端领域服务、契约和路由；服务读取现有 LocalTdxOverviewSource、BarRepository 与 AShareInstrumentDirectory，不生成代理或模拟字段。前端新增独立页面与 API 类型，按状态带、规则仪表盘、候选标签、六类尾盘行为和实时变更日志展示。

**Tech Stack:** FastAPI、Pydantic、DuckDB BarRepository、React、TypeScript、Vitest、Vite、便携 EXE 构建脚本。

## Global Constraints

- 所有行情、历史、名称和时间戳必须来自真实本地数据；缺失字段标记为“不可用/部分可用”。
- 14:30 前只返回 `pre_screen`；14:30–15:00 返回 `live_monitor`；15:00 后冻结为 `post_close`。
- 不承诺不可验证的毫秒级数据；返回真实 `refresh_interval_ms` 和数据源能力。
- A 股红色表示上涨/改善，绿色表示下跌/恶化；不关闭、重启或控制通达信。
- 用户交付只通过 Windows EXE，源码修改后必须运行 `scripts/build-portable.ps1` 和 `scripts/run-portable-smoke.ps1`。

---

### Task 1: 后端契约与纯规则计算

**Files:**
- Create: `apps/api/src/qibao_api/contracts/late_session_selection.py`
- Create: `apps/api/src/qibao_api/a_shares/late_session_selection.py`
- Test: `apps/api/tests/test_late_session_selection.py`

- [ ] **Step 1: Write failing tests** for phase boundaries, all seven gates, unavailable yellow-line/index evidence, six behavior tags, and code/name pairing.
- [ ] **Step 2: Run `pytest apps/api/tests/test_late_session_selection.py -q` and verify RED.**
- [ ] **Step 3: Implement immutable Pydantic contracts and deterministic helpers.** The seven gates are: 14:30–15:00, change 3–6%, volume ratio 2–5, turnover 6–15%, market cap 60–300 亿, 20-session limit-up count >=1, price above real intraday average line. A missing field never passes.
- [ ] **Step 4: Run the focused tests and verify GREEN.**

### Task 2: Real-data service and API route

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Create: `apps/api/src/qibao_api/routes/late_session_selection.py`
- Modify: `apps/api/src/qibao_api/contracts/__init__.py` when required by package exports
- Test: `apps/api/tests/routes/test_late_session_selection_route.py`

- [ ] **Step 1: Write failing route tests** for `pre_screen`, `live_monitor`, `post_close`, stale snapshot retention, and no proxy for missing intraday average/index data.
- [ ] **Step 2: Run route tests and verify RED.**
- [ ] **Step 3: Implement service wiring.** Use `local_tdx_overview_source.current()` for live quotes; use `bar_repository.latest_many()` for 20-session history; resolve names from `AShareInstrumentDirectory`; compute turnover and market cap only when real fields exist; compute intraday average only from explicit minute/average fields. Include source evidence, coverage and limitations.
- [ ] **Step 4: Register router and dependency without adding a second polling loop.** The route reads the latest local snapshot and returns `next_refresh_ms` based on observed source timestamp/refresh policy.
- [ ] **Step 5: Run focused API tests and full API tests.**

### Task 3: Frontend menu, API client and page

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Create: `apps/web/src/features/late-session-selection/api.ts`
- Create: `apps/web/src/features/late-session-selection/types.ts`
- Create: `apps/web/src/features/late-session-selection/LateSessionSelectionView.tsx`
- Create: `apps/web/src/features/late-session-selection/lateSessionSelection.css`
- Tests: `apps/web/src/features/late-session-selection/LateSessionSelectionView.test.tsx`

- [ ] **Step 1: Write failing component tests** for menu routing, seven rule cards, code/name labels, phase-specific refresh, behavior tags, unavailable states and no fabricated recommendations.
- [ ] **Step 2: Run the focused Vitest test and verify RED.**
- [ ] **Step 3: Implement route `late_session_selection` and lazy page loading.**
- [ ] **Step 4: Implement page layout:** status strip, seven clickable rule cards, candidate tags with timestamps/source, six behavior cards using “观察/风险提示/待核验”, live change log, and post-close freeze banner.
- [ ] **Step 5: Add responsive CSS and red-up/green-down visual semantics.**
- [ ] **Step 6: Run focused and full Web tests, TypeScript and Vite build.**

### Task 4: Release verification and memory update

**Files:**
- Modify: `D:\Users\90090\Documents\知识库\02-项目记忆\金融财经.md`
- Create: `docs/verification/2026-08-17-late-session-selection.md`

- [ ] **Step 1: Run UTF-8/mojibake scan and `git diff --check`.**
- [ ] **Step 2: Run `scripts/build-portable.ps1` and preserve the eight persistent directories.**
- [ ] **Step 3: Run `scripts/run-portable-smoke.ps1` against the rebuilt EXE; record actual status, timing and any real-data partial boundary.**
- [ ] **Step 4: Record confirmed facts and limitations in the project memory without credentials.**

## Self-review

- The screenshot gates, time phases, real-data-only rule, six explanatory behaviors, menu routing, responsive presentation and EXE delivery are all covered above.
- No rule uses a price/volume proxy for the missing yellow line, turnover, market cap or index comparison.
- API and UI names are consistent: `LateSessionSelectionResponse`, `late_session_selection`, `/api/v1/a-shares/late-session-selection`.
