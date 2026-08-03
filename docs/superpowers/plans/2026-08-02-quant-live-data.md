# 量化分析真实动态数据 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让量化分析使用真实分层刷新，并在断链时保留最后有效证据和显示数据新鲜度。

**Architecture:** 新建一个页面可见性驱动的轮询 Hook，分别调度 TICK、策略和候选池。后端量化策略契约补充生成时间、市场观测时间、数据年龄和刷新模式，前端状态条统一呈现这些信息。

**Tech Stack:** React 18、TypeScript、Vitest、FastAPI、Pydantic、pytest、便携 Windows EXE。

## Global Constraints

- 最终用户只通过 `dist/XiaoQiBao-Portable/xiaoqibao.exe` 查看。
- 禁止模拟行情、随机分数和缓存冒充实时数据。
- 中文文件使用 UTF-8 和 `apply_patch` 修改。
- 构建后保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。

---

### Task 1: 后端新鲜度契约

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Test: `apps/api/tests/a_shares/test_quant_strategy.py`
- Test: `apps/api/tests/routes/test_quant_strategy.py`

**Interfaces:**
- Produces: `generated_at`, `market_observed_at`, `data_age_seconds`, `refresh_mode`, `next_refresh_at`。

- [ ] 先写刷新模式和数据年龄失败测试。
- [ ] 运行定向 pytest，确认因字段缺失失败。
- [ ] 实现最小契约和刷新模式计算。
- [ ] 运行定向 pytest，确认通过。

### Task 2: 页面可见性轮询 Hook

**Files:**
- Create: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.ts`
- Test: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.test.tsx`

**Interfaces:**
- Produces: `useQuantLiveResource<T>({ loader, intervalMs, enabled, errorMessage })`。
- Returns: 最后有效数据、初次加载状态、错误、最近成功时间、当前刷新状态和手动刷新函数。

- [ ] 先写立即加载、定时刷新、隐藏暂停、恢复刷新、失败保留和卸载清理测试。
- [ ] 运行 Vitest，确认 Hook 尚不存在而失败。
- [ ] 实现单飞请求和可见性调度。
- [ ] 运行 Vitest，确认通过。

### Task 3: 量化页面接入真实分层刷新

**Files:**
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Create: `apps/web/src/features/quant-analysis/QuantLiveStatusBar.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`

**Interfaces:**
- Consumes: Task 1 的新鲜度字段和 Task 2 的轮询 Hook。
- Produces: TICK 1 秒、策略 5 秒、候选池 30 秒刷新和状态条。

- [ ] 先写页面轮询频率、当前交易日 TICK、失败保留和状态条测试。
- [ ] 运行定向 Vitest，确认旧页面一次性加载导致失败。
- [ ] 用 Hook 替换一次性 board、tick、strategy 请求。
- [ ] 保持回测和 Kronos 仅随股票或输入日期变化。
- [ ] 增加状态条与可读样式。
- [ ] 运行定向 Vitest，确认通过。

### Task 4: 全量验证与 EXE 发布

**Files:**
- Verify: `apps/web/src/features/quant-analysis/*`
- Verify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Build: `scripts/build-portable.ps1`
- Smoke: `scripts/run-portable-smoke.ps1`

- [ ] 运行前端完整测试和构建。
- [ ] 运行后端完整测试。
- [ ] 扫描中文乱码和重复问号。
- [ ] 重建便携 EXE，并确认持久目录被保留。
- [ ] 对真实 EXE 运行启动和接口烟测。
- [ ] 记录最终 EXE SHA-256 和启动耗时。
