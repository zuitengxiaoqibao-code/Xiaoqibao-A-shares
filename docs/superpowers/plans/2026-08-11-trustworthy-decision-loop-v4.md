# 可信决策闭环 v4.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有真实决策闭环上增加评分校准、组合风险、公司横向研究、严格提醒、个人复盘、统一水印和异常数据拦截。

**Architecture:** 量化校准与复盘日志扩展现有独立 SQLite 影子账本；组合风险使用独立 SQLite 持仓表和 `BarRepository.latest_many`；公司研究复用现有四股票缓存；共享水印只消费各页面已有时间和来源字段。所有新分析均为只读决策辅助，不控制交易软件或下单。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、SQLite、DuckDB、React、TypeScript、ECharts、Vitest、pytest、PyInstaller。

## Global Constraints

- 唯一用户交付入口为便携 Windows EXE。
- 禁止模拟、随机、缺失补零和代理数据冒充。
- A 股红涨绿跌。
- 不关闭、重启或控制通达信。
- 页面切换不触发全市场同步网络扫描。
- 用户可见源码修改后必须全量测试、生产构建、乱码扫描、便携构建和真实发布 smoke。

---

### Task 1: 日线序列质量契约

**Files:**
- Create: `apps/api/src/qibao_api/contracts/data_quality.py`
- Create: `apps/api/src/qibao_api/a_shares/data_quality.py`
- Test: `apps/api/tests/a_shares/test_data_quality.py`

**Interfaces:**
- Produces: `DataQualityIssue`, `DataQualityReport`, `assess_bar_series(bars: Sequence[DailyBar]) -> DataQualityReport`。

- [x] **Step 1: Write the failing tests** for duplicate dates, descending dates, volume/amount contradiction, 35% jump warning and clean series.
- [x] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest apps\api\tests\a_shares\test_data_quality.py -q` and confirm failures are caused by missing contracts/functions.
- [x] **Step 3: Implement** immutable Pydantic contracts and deterministic checks; structural issues set `blocked=True`, jump issues remain warnings.
- [x] **Step 4: Run the focused tests** and confirm all pass.

### Task 2: 影子账本校准与漂移分析

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_shadow.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_shadow_ledger.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/api/tests/a_shares/test_quant_shadow_ledger.py`
- Modify: `apps/api/tests/routes/test_quant_strategy.py`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Modify: `apps/web/src/features/quant-analysis/QuantShadowLedgerPanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantShadowLedgerPanel.test.tsx`

**Interfaces:**
- Produces: `QuantShadowAnalytics`, `CalibrationBucket`, `StrategyDriftAssessment` and `QuantShadowLedgerStore.analytics(horizon=5)`.
- API: `GET /api/v1/a-shares/quant-strategy/shadow/analytics?horizon=5`.

- [x] **Step 1: Write failing backend tests** covering insufficient samples, bucket hit rates, Brier score and drift threshold.
- [x] **Step 2: Run focused backend tests** and confirm RED.
- [x] **Step 3: Implement analytics** using only mature ready outcomes, Decimal arithmetic and explicit sample gates.
- [x] **Step 4: Add route tests and route implementation** with horizon validation.
- [x] **Step 5: Write failing Web tests** for calibration buckets, insufficient state and drift warning.
- [x] **Step 6: Implement API/type/UI changes** and keep empty states truthful.
- [x] **Step 7: Run focused backend and Web tests**.

### Task 3: 严格提醒门槛与个人复盘日志

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Create: `apps/api/src/qibao_api/contracts/decision_journal.py`
- Create: `apps/api/src/qibao_api/a_shares/decision_journal.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/tests/a_shares/test_quant_strategy.py`
- Create: `apps/api/tests/a_shares/test_decision_journal.py`
- Modify: `apps/api/tests/routes/test_quant_strategy.py`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantShadowLedgerPanel.tsx`

**Interfaces:**
- Produces: candidate `alert_gate` with ordered checks and blockers.
- Produces: `DecisionJournalStore.append()` and `recent()`.
- API: `GET/POST /api/v1/a-shares/quant-strategy/journal`.

- [x] **Step 1: Write failing candidate tests** proving high volatility, deep drawdown, low evidence coverage or risk penalty prevent `alert`.
- [x] **Step 2: Implement `AlertGate` contracts and candidate status downgrade**.
- [x] **Step 3: Write failing journal store tests** for append-only records, positive numeric validation and decision linkage.
- [x] **Step 4: Implement journal store and routes** under the portable `data` directory.
- [x] **Step 5: Write failing Web tests** for gate reasons and journal submission/history.
- [x] **Step 6: Implement Web types, API and panels** without automatic trade actions.
- [x] **Step 7: Run focused tests**.

### Task 4: 组合风险存储与分析服务

**Files:**
- Create: `apps/api/src/qibao_api/contracts/portfolio_risk.py`
- Create: `apps/api/src/qibao_api/a_shares/portfolio_risk.py`
- Create: `apps/api/src/qibao_api/routes/portfolio_risk.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/a_shares/test_portfolio_risk.py`
- Create: `apps/api/tests/routes/test_portfolio_risk.py`

**Interfaces:**
- Produces: `PortfolioRiskStore`, `PortfolioRiskService.current()`, `upsert_position()`, `delete_position()`.
- Consumes: `BarRepository.latest_many`, verified metadata provider and cached market regime provider.
- API: `GET /api/v1/a-shares/portfolio-risk`, `PUT/DELETE /positions/{symbol}`.

- [x] **Step 1: Write failing store tests** for empty state, upsert, delete and invalid position values.
- [x] **Step 2: Implement SQLite store** with one row per symbol and no default positions.
- [x] **Step 3: Write failing analysis tests** for weights, HHI, industry concentration, correlation sample gate, three stress scenarios and regime position cap.
- [x] **Step 4: Implement analysis** with one batched local bar query and data-quality filtering.
- [x] **Step 5: Write route tests and implement routes/dependencies**.
- [x] **Step 6: Run focused API tests**.

### Task 5: 风险页面组合仪表盘

**Files:**
- Create: `apps/web/src/features/portfolio-risk/types.ts`
- Create: `apps/web/src/features/portfolio-risk/api.ts`
- Create: `apps/web/src/features/portfolio-risk/PortfolioRiskPanel.tsx`
- Create: `apps/web/src/features/portfolio-risk/PortfolioRiskPanel.test.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerRiskView.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerRiskView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: portfolio GET/PUT/DELETE API.
- Produces: editable position list, concentration gauges, correlation matrix and clearly labelled mechanical stress cards.

- [x] **Step 1: Write failing component tests** for empty state, adding/removing positions, unavailable industry, correlation and scenario labelling.
- [x] **Step 2: Implement API/types and panel** using red/green only for gain/loss direction.
- [x] **Step 3: Integrate into the existing risk route** below the five-layer risk matrix; do not add another top-level menu.
- [x] **Step 4: Add responsive CSS** with readable minimum font sizes.
- [x] **Step 5: Run focused Web tests**.

### Task 6: 公司研究比较、趋势和估值情景

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/api/tests/a_shares/test_company_research.py`
- Create: `apps/web/src/features/company-research/FinancialTrendChart.tsx`
- Create: `apps/web/src/features/company-research/FinancialTrendChart.test.tsx`
- Create: `apps/web/src/features/company-research/ResearchComparisonMatrix.tsx`
- Create: `apps/web/src/features/company-research/ResearchComparisonMatrix.test.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/company-research/types.ts`
- Modify: `apps/web/src/features/company-research/companyResearch.css`

**Interfaces:**
- Produces: `ValuationScenarioRange` inside `ValuationObservation`.
- Consumes: existing four-company research cache, annual financial periods and counter-case evidence.

- [x] **Step 1: Write failing backend tests** for available and unavailable valuation scenarios, including 3-institution and 180-day gates.
- [x] **Step 2: Implement transparent 0.8/1.0/1.2 peer-PE scenarios** with “not target price” limitation.
- [x] **Step 3: Write failing component tests** for comparison cutoff dates, missing-value gaps, scenario formula and opposing thesis.
- [x] **Step 4: Implement matrix and ECharts financial trend** without zero-filling missing values.
- [x] **Step 5: Integrate components and evidence navigation** into the existing company research page.
- [x] **Step 6: Run focused backend and Web tests**.

### Task 7: 统一数据水印

**Files:**
- Create: `apps/web/src/shared/evidence/DataWatermarkStrip.tsx`
- Create: `apps/web/src/shared/evidence/DataWatermarkStrip.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerRiskView.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Produces: one shared component accepting status, trade date, observed/generated times, source count, sample count, refresh state and limitations.

- [x] **Step 1: Write failing component tests** for ready, partial, stale and unavailable states.
- [x] **Step 2: Implement the shared strip** with no full-page loading behavior.
- [x] **Step 3: Integrate into quant, research and risk pages** using existing response fields.
- [x] **Step 4: Run focused Web and layout-safety tests**.

### Task 8: 全量验收与便携交付

**Files:**
- Modify: `docs/superpowers/plans/2026-08-11-trustworthy-decision-loop-v4.md`
- Create: `docs/verification/2026-08-11-trustworthy-decision-loop-v4.md`
- Modify: durable project memory after verification.

- [x] **Step 1: Run API full suite**: `.\.venv\Scripts\python.exe -m pytest apps\api\tests -q`.
- [x] **Step 2: Run Web full suite and build**: `npm test -- --run` and `npm run build` in `apps/web`.
- [x] **Step 3: Run UTF-8/mojibake scan and `git diff --check`**.
- [x] **Step 4: Rebuild portable EXE** with `scripts/build-portable.ps1`, preserving `config/data/news/cache/logs/models/exports/backups`.
- [x] **Step 5: Run real release smoke** with `scripts/run-portable-smoke.ps1 -UseReleaseData` and add portfolio/research probes.
- [x] **Step 6: Record SHA-256, performance, truthful unavailable states and no-TDX-control evidence**.
- [x] **Step 7: Mark every plan item complete and update long-term memory**.
