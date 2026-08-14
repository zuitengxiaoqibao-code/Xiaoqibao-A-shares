# 一树 A 股观测台平台完善计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task with verification checkpoints.

**Goal:** 在不牺牲数据真实性的前提下，将一树-A股观测台完善为快速、可追溯、可解释、可恢复的 Windows EXE 决策工作台。

**Architecture:** 以现有 API 契约、证据账本、缓存优先和便携发布体系为基础，补齐“数据水位—请求性能—研究结论—交互展示—发布治理”五层闭环。所有新增能力优先复用现有 `MetricContract`、`EvidenceLedger`、`DataWatermarkStrip`、每日快照和发布清单，不另起一套状态系统。

**Tech Stack:** FastAPI + Pydantic + DuckDB + React 19 + TypeScript + ECharts + Vitest + Pytest + PyInstaller + PowerShell portable build/smoke scripts。

## Global Constraints

- Windows EXE 是唯一用户交付入口；不交付 HTML 或 localhost 页面。
- 所有行情、财务、新闻和量化结果必须来自真实可核验数据；缺失时显示 `partial/stale/unavailable/error`，不得用零值、随机值或无关字段填充。
- A 股红色表示上涨/改善，绿色表示下跌/恶化；结构构成图使用中性色。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。
- 中文源文件使用 UTF-8 和 `apply_patch` 修改；修改后执行乱码扫描、API/Web 测试、生产构建和 EXE smoke。
- 任何生产代码必须先有失败测试，再实现最小修复。

## 当前基线

- 信息总览已有约 98.52% 的真实行情覆盖率和缓存优先启动。
- 量化分析已有真实候选、因子覆盖率、市场风格和候选生命周期基础，但在覆盖不足、触发解释和刷新稳定性上继续增强。
- 公司研究已有 F10、行业、公告、风险、正反方证据和前向 PE 字段证据，但需要统一证据摘要与研究结论结构。
- 已有 `MetricContract`、`EvidenceLedger`、`DataWatermarkStrip`、历史质量检查、通达信导入、运维诊断和 portable release manifest。
- 已知工程治理遗留：部分测试工具链生命周期警告、真实通达信专业包缺失时的 `unavailable` 边界、量化和公司研究的 `partial` 状态。

## 分阶段目标

### 阶段 1：数据真实性闭环

- [x] 全站可见指标都能关联来源、观测时间、交易日、样本量、覆盖率和限制原因。
- [x] 事实、推导、判断、不可用四类内容在页面中可区分。
- [x] 历史日线自动检查缺失、重复、未来日期和异常覆盖率，并提供可追溯修复建议。
- [x] 专业接口诊断码和普通行情降级边界在所有相关页面一致。

### 阶段 2：性能闭环

- [x] 启动采用界面骨架、当日缓存、后台实时更新三段式流程。
- [x] 同一股票/交易日/数据域请求合并，避免重复请求和整页重排。
- [x] 数据域并行加载，页面切换不阻塞，不反复出现“加载工作台”。
- [x] 进度条基于实际任务权重，失败显示具体阶段和原因。
- [x] 记录窗口、缓存、API、页面可交互、完整更新的 P50/P95 和缓存命中率。

### 阶段 3：量化与公司研究闭环

- [x] 量化候选统一显示风格、策略、分项评分、触发条件、失效条件、仓位和证据覆盖率。
- [x] 回测显示样本数、闭合交易、胜率、盈亏比、回撤、Sharpe、手续费、滑点和数据区间。
- [x] 公司研究统一输出业务、行业、财务、现金流、竞争、估值、催化、风险和逻辑失效条件。
- [x] 新闻、板块、股票、K 线事件可相互跳转，重复新闻合并并显示原始来源。

### 阶段 4：全站交互与视觉统一

- [x] 所有统计数字支持钻取；股票统一展示名称 + 六位代码。
- [x] 统一状态颜色、字号、卡片密度、表格密度、图表高度和响应式断点。
- [x] 最大化、高 DPI、小屏和窗口缩放不出现大面积留白或错列。
- [x] 移除整页跳动、连续滚动等干扰动效，保留低频呼吸/流光状态反馈。

### 阶段 5：发布与恢复治理

- [x] 质量门禁覆盖 API、Web、类型、Ruff、编码、构建、smoke、数据水位和进程释放。
- [x] 发布清单包含 commit、工作树状态、依赖哈希、迁移版本、数据快照和 EXE SHA-256。
- [x] 数据库迁移、备份、恢复和回滚流程可验证，八个持久目录不丢失。

## 任务拆分

### Task 1: 建立全局数据证据摘要契约

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/evidence_ledger.py`
- Modify: `apps/api/tests/contracts/test_evidence_ledger.py`
- Modify: `apps/web/src/shared/evidence/EvidenceLedger.tsx`
- Modify: `apps/web/src/shared/evidence/EvidenceLedger.test.tsx`
- Modify: `apps/web/src/shared/evidence/DataWatermarkStrip.tsx`

**Interfaces:**
- `EvidenceLedgerEntry` 增加 `total_count` 和 `coverage_percent`，覆盖率由 API/仓储层传入而非前端推导。
- API 合约必须拒绝 `ready` 状态缺少观测时间、覆盖率超出 0–100、有效样本超过总样本或不可用状态缺少原因。
- 证据账本展示覆盖率与“有效样本/总样本”，DataWatermarkStrip 在总览条展示同一口径。

- [x] Step 1: 在 `test_evidence_ledger.py` 增加失败测试，覆盖覆盖率越界和有效样本超总样本。
- [x] Step 2: 运行 `pytest apps/api/tests/contracts/test_evidence_ledger.py -q`，确认新断言因字段/校验缺失而失败。
- [x] Step 3: 扩展冻结的 Pydantic 证据条目，增加 `total_count`、`coverage_percent` 和校验。
- [x] Step 4: 重新运行 API 定向测试并确认全部通过。
- [x] Step 5: 在现有 `EvidenceLedger.test.tsx` 先增加失败断言，再实现覆盖率展示和 DataWatermarkStrip 的有效样本/总样本展示。

### Task 2: 统一请求去重与性能账本

**Files:**
- Inspect/Modify: `apps/web/src/shared/api/*`（沿用现有请求封装位置）
- Create: `apps/web/src/shared/performance/requestLedger.ts`
- Create: `apps/web/src/shared/performance/requestLedger.test.ts`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`

**Interfaces:**
- `requestLedger.run<T>(key, operation, metadata)`：同 key 的并发调用共享同一个 Promise。
- `requestLedger.record()`：记录开始、结束、状态、缓存命中和错误原因。
- 账本只保留有限窗口的本地内存数据，不写入行情数据库。

- [x] Step 1: 写失败测试，验证相同 key 并发只执行一次，失败请求可被下一次调用重新执行。
- [x] Step 2: 运行定向 Vitest，确认失败原因是函数不存在。
- [x] Step 3: 实现最小内存去重和 P50/P95 聚合函数。
- [x] Step 4: 将信息总览刷新、量化刷新、公司研究刷新接入去重层，保持现有 API 契约不变。
- [x] Step 5: 增加回归测试，验证请求合并、失败重试和延迟统计不会清空已显示缓存，也不会触发整页卸载。

### Task 3: 量化策略证据和触发解释面板

**Files:**
- Inspect/Modify: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Inspect/Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Create/Modify: `apps/web/src/features/quant-analysis/StrategyEvidencePanel.tsx`
- Create: `apps/web/src/features/quant-analysis/StrategyEvidencePanel.test.tsx`

**Interfaces:**
- 每个候选输出 `regime_match`, `stock_score`, `trigger_score`, `rr_score`, `risk_penalty`, `final_score`, `evidence_coverage`, `trigger_state`, `invalidations`。
- 缺少关键因子时，分数保持不可用或部分状态，不补 0。

- [x] Step 1: 添加失败测试，验证缺少资金流或历史覆盖时不会生成 ready 触发结论。
- [x] Step 2: 运行 API 定向测试确认失败。
- [x] Step 3: 实现严格门槛和结构化解释；候选证据覆盖改用真实市场/因子/触发水位加权，不再使用固定基线。
- [x] Step 4: 前端用仪表、分项条和触发/失效标签展示，不新增随机数据。
- [x] Step 5: 验证刷新、切股和旧快照恢复时证据不会串标的。

### Task 4: 公司研究事实—推导—判断摘要

**Files:**
- Inspect/Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Inspect/Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Inspect/Modify: `apps/web/src/features/company-research/CompanyResearchSections.tsx`
- Create: `apps/web/src/features/company-research/ResearchConclusionBlock.test.tsx`

**Interfaces:**
- 每条结论包含 `kind`（fact/inference/judgement/unavailable）、`claim`、`evidence_ids`、`source_count`、`observed_at` 和 `limitations`。
- 默认展示一条重点结论和最多三条证据，完整原文折叠。

- [x] Step 1: 写失败测试，验证没有证据时只能显示 unavailable，不显示推测性结论。
- [x] Step 2: 运行测试确认失败。
- [x] Step 3: 实现 API 结构化摘要。
- [x] Step 4: 统一公司研究页面的重点结论、正方、反方、催化和风险布局。
- [x] Step 5: 运行公司研究聚焦回归和全量 Web 测试。

### Task 5: 全站可钻取和响应式密度回归

**Files:**
- Inspect/Modify: `apps/web/src/features/market-overview/workspaces/MetricDrilldown.tsx`
- Inspect/Modify: `apps/web/src/features/market-overview/overview.css`
- Inspect/Modify: `apps/web/src/app/theme.css`
- Create: `apps/web/src/app/density-regression.test.tsx`

**Interfaces:**
- 所有统计卡必须提供 `aria-label`、可点击状态和对应成员/聚合说明。
- 桌面 12 列、双列中屏、单列小屏布局必须保持卡片顺序和名称+代码可读性。

- [x] Step 1: 写失败测试，覆盖宽屏四列、中屏双列、小屏单列和聚合指标不可钻取说明。
- [x] Step 2: 运行测试确认当前布局缺口。
- [x] Step 3: 调整 CSS Grid、最小字号、行距和高度约束。
- [x] Step 4: 增加统计卡键盘访问和整行点击行为。
- [x] Step 5: 使用生产构建和静态布局测试验证无横向溢出和大面积留白。

### Task 6: 真实进度与刷新状态统一

**Files:**
- Inspect/Modify: `apps/api/src/qibao_api/contracts/task_progress.py`
- Inspect/Modify: `apps/api/src/qibao_api/operations/*`
- Inspect/Modify: `apps/web/src/features/market-overview/HomepageStartupOverlay.tsx`
- Inspect/Modify: `apps/web/src/shared/evidence/DataWatermarkStrip.tsx`
- Create: `apps/web/src/shared/progress/progressModel.test.ts`

**Interfaces:**
- 进度阶段必须有权重、已完成数量、总数量、当前状态和失败原因。
- 进度不得从 1% 直接跳 100%，终态必须与数据状态一致。

- [x] Step 1: 写失败测试，验证阶段权重能产生单调递增且不虚假的进度。
- [x] Step 2: 运行测试确认当前实现失败。
- [x] Step 3: 实现共享进度模型和“实时监控中/缓存展示/刷新失败”状态。
- [x] Step 4: 接入首页、量化、公司研究和数据设置，不再使用独立的假进度逻辑。
- [x] Step 5: 验证刷新过程中页面不闪烁、不整页切换，失败时保留可用缓存。

### Task 7: 发布质量门禁和回滚演练

**Files:**
- Inspect/Modify: `scripts/build-portable.ps1`
- Inspect/Modify: `scripts/run-portable-smoke.ps1`
- Create: `scripts/verify-release-quality.ps1`
- Create: `docs/verification/2026-08-14-platform-perfection.md`

- [x] Step 1: 写脚本验收清单测试/fixture，覆盖 commit、工作树、八个持久目录、EXE hash、窗口/API smoke。
- [x] Step 2: 运行脚本验证当前缺少质量门禁时失败。
- [x] Step 3: 实现发布质量脚本，任何关键门禁失败都返回非零退出码。
- [x] Step 4: 重建便携 EXE，保留 config/data/news/cache/logs/models/exports/backups。
- [x] Step 5: 运行 API、Web、Ruff、构建、乱码扫描和真实 EXE smoke，记录结果后再宣称阶段完成。

### Final verification record

- API: 1369 passed, 1 skipped, 5 warnings.
- Web: 111 test files, 651 passed; production build passed.
- Release smoke: window 59ms, API 2502ms, complete verification 16530ms; overview ready at 98.81% coverage; quant partial, company research partial, professional probes honest ready/partial/unavailable mix.
- Release quality: commit `769834603f19459a51817d0dd95af00f9e12852b`, EXE SHA-256 `3333C4C977B2DDA9959AAC5562E8D51DD3B460CEAB4407C5E6BFAAAE66ECC04D`; all eight persistent directories preserved.

### Task 8: 旧快照完整性兼容

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/company_research_versions.py`
- Modify: `apps/api/tests/a_shares/test_company_research_versions.py`

**Interfaces:**
- 新增的证据水位字段属于展示元数据，不改变旧公司研究快照的语义哈希。
- 旧发布包中的追加式版本仍必须通过 canonical hash、身份和语义校验。

- [x] Step 1: 用旧证据条目和新增覆盖率字段编写失败兼容性测试。
- [x] Step 2: 运行定向测试，确认新增字段会造成旧语义哈希不一致。
- [x] Step 3: 在语义哈希归一化时仅排除证据水位元数据，不放宽 canonical hash 校验。
- [x] Step 4: 运行公司研究版本、全量 API、Web、构建和 EXE smoke。

## 每阶段验收标准

- 所有新增生产代码都有先失败后通过的测试记录。
- API/Web 全量测试、Ruff、TypeScript/Vite 构建和 UTF-8/乱码扫描通过。
- EXE 窗口可见、API 就绪、首页可交互、关键页面可打开。
- 数据不足时仍显示真实 `partial/unavailable`，不生成模拟指标。
- smoke 结束无本程序、Node、测试 Python 残留进程，通达信进程和监听状态不被改变。
