# A股短线风格与策略工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在量化分析中增加基于真实全市场数据的短线风格识别、策略选择和候选股票仪表盘。

**Architecture:** 复用现有 `MarketOverviewService` 和盘后候选服务，在新的纯计算服务中完成模型匹配与策略评分。React 通过独立 API 加载该工作台，失败不影响原有量化四象限。

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, React 18, TypeScript, ECharts, Vitest, PyInstaller portable EXE.

## Global Constraints

- 仅交付 Windows 便携 EXE，不提供 HTML 或 localhost 入口。
- 不生成模拟行情、资金流、候选、胜率或买卖点。
- 缺失盘中触发时必须阻止 `alert` 状态。
- 使用 `apply_patch` 修改中文文件，完成后执行 UTF-8 与乱码扫描。
- 重建时保留 `config/data/news/cache/logs/models/exports/backups`。

---

### Task 1: 短线策略契约与纯计算

**Files:**
- Create: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Test: `apps/api/tests/a_shares/test_quant_strategy.py`

**Interfaces:**
- Consumes: `MarketOverviewResponse`, `CandidateBoard`, 股票名称解析器。
- Produces: `QuantStrategyDashboard`, `build_quant_strategy_dashboard(...)`。

- [ ] 写失败测试，覆盖六类风格、六个模型、`40/30/20/10` 公式、风险扣分和缺失触发阻断。
- [ ] 运行测试确认新模块不存在。
- [ ] 实现冻结 Pydantic 契约和纯 Decimal 计算。
- [ ] 运行模块测试并确认无 `NaN/Infinity`。

### Task 2: 服务、依赖与 API

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Create: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/routes/test_quant_strategy.py`

**Interfaces:**
- Produces: `GET /api/v1/a-shares/quant-strategy?limit=12`。

- [ ] 写失败路由测试，覆盖正常、部分数据和服务异常。
- [ ] 组合市场总览、候选池和股票目录，保留来源与观测时间。
- [ ] 注册依赖、应用状态和路由。
- [ ] 运行路由与生命周期测试。

### Task 3: React API 与策略工作台

**Files:**
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Create: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Create: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Produces: `QuantStrategyLoader`, `ShortTermStrategyWorkbench`。

- [ ] 写失败组件测试，覆盖仪表、11项指标、候选标签、触发与失效条件。
- [ ] 实现类型和 API，拒绝非 2xx。
- [ ] 实现 ECharts 仪表、指标矩阵、策略带和响应式候选标签墙。
- [ ] 接入现有量化页面并保持各数据源独立降级。
- [ ] 运行量化分析前端测试。

### Task 4: 应用接线与验证

**Files:**
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`

- [ ] 接入 `loadQuantStrategy` 并保留现有路由与书签。
- [ ] 运行完整前后端测试、Ruff、TypeScript 和生产构建。
- [ ] 执行 UTF-8、乱码与 `git diff --check`。
- [ ] 运行 `scripts/build-portable.ps1` 重建便携版。
- [ ] 运行 `scripts/run-portable-smoke.ps1`，记录真实 EXE 启动和接口状态。
- [ ] 计算最终 EXE SHA-256。
