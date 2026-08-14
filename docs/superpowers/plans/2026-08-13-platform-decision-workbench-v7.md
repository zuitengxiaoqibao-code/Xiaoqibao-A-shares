# A 股观测台真实决策工作台 v7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有信息展示能力统一为可核验、可筛选、可增量更新、可复盘的本地 A 股决策工作台。

**Architecture:** 复用现有 `FieldEvidence`、`EvidenceLedger`、`AShareInstrumentDirectory`、快照缓存、统一事件和决策日志。新增共享指标契约、统一股票主数据读模型、增量资源合并器、筛选会话、提醒收件箱和决策快照关联；各页面只消费共享契约，不再自行解释相同数据。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、SQLite/DuckDB、React 19、TypeScript、ECharts、Vitest、PyInstaller。

## Global Constraints

- 只交付 Windows 便携 EXE，不生成浏览器或 HTML 交付物。
- 数据缺失必须显示不可用或仅聚合统计，不得生成模拟成员、名称、行情、新闻或结论。
- 所有股票默认显示名称和六位代码；名称缺失显示“名称待补齐”。
- A 股颜色遵守红涨绿跌；结构性分类颜色不得冒充涨跌方向。
- 页面先显示同日真实缓存，后台增量更新不得把完整数据刷新为空。
- 不关闭、重启或控制通达信；不控制鼠标和桌面。
- 每阶段完成后运行聚焦测试、全量相关测试、生产构建、UTF-8/乱码扫描和 `git diff --check`。
- 用户可见变更完成后重建便携 EXE并执行正式烟测，保留 `config/data/news/cache/logs/models/exports/backups`。

---

### Task 1: 全站指标契约与信息总览迁移

**Files:**
- Create: `apps/api/src/qibao_api/contracts/metric_contract.py`
- Create: `apps/api/tests/contracts/test_metric_contract.py`
- Create: `apps/web/src/shared/evidence/metricContract.ts`
- Create: `apps/web/src/shared/evidence/metricContract.test.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceInsights.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/MetricDrilldown.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceInsightDashboard.tsx`
- Test: `apps/web/src/features/market-overview/workspaces/workspaceInsights.test.ts`
- Test: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`

**Produces:** `MetricContract`，统一包含指标标识、标签、值、单位、口径、交易日、观测时间、来源、公式版本、样本量、状态、总数、已加载成员数、成员列表和不可钻取原因。

- [x] 先写后端与前端契约失败测试，覆盖成员数量一致性、聚合统计说明、缺失状态、数值精度和来源字段。
- [x] 运行聚焦测试，确认因契约不存在而失败。
- [x] 实现最小共享契约与验证函数。
- [x] 将信息总览 50 个专题的顶部指标适配到共享契约。
- [x] 钻取面板展示口径、交易日、来源、公式版本、总数与已加载数量。
- [x] 运行信息总览聚焦测试、全量 Web 测试和生产构建。

### Task 2: 统一股票主数据索引

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/instrument_directory.py`
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Create: `apps/api/tests/a_shares/test_instrument_directory_search.py`
- Create: `apps/web/src/shared/instruments/instrumentDirectory.ts`
- Create: `apps/web/src/shared/instruments/instrumentDirectory.test.ts`
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantInstrumentSelector.tsx`

**Produces:** 名称、代码、简称、历史名称、交易所、行业、板块、状态和搜索别名的本地统一读模型。

- [x] 写失败测试覆盖代码、中文名称、前缀和拼音首字母查询，以及 ST/停牌状态。
- [x] 扩展本地目录表和兼容迁移，不删除旧观测。
- [x] 提供一次加载、内存搜索、后台更新的前端目录。
- [x] 替换个股观察、公司研究、量化和钻取名单的分散名称解析。
- [x] 验证搜索首屏即时响应，名称缺失仍诚实标记。

### Task 3: 增量刷新引擎

**Files:**
- Modify: `apps/web/src/shared/coalescedFetch.ts`
- Create: `apps/web/src/shared/incrementalResource.ts`
- Create: `apps/web/src/shared/incrementalResource.test.ts`
- Modify: `apps/web/src/features/market-overview/api.ts`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/news-alerts/useBreakingNewsAlerts.ts`
- Modify: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.ts`

**Produces:** 按资源键合并、按实体 ID 追加、按交易日切换、失败保留旧快照的统一增量资源状态机。

- [x] 写失败测试覆盖乱序响应、重复事件、跨日清空、空响应保护和局部价格更新。
- [x] 实现纯函数合并器和资源状态机。
- [x] 市场行情只替换变化股票和最新分钟点，事件与新闻只追加新 ID。
- [x] 页面切换保留筛选、滚动和已渲染图表实例。
- [x] 加入刷新耗时和变化条数诊断，不显示整页加载遮罩。

### Task 4: 统一筛选工作台

**Files:**
- Create: `apps/web/src/shared/screener/types.ts`
- Create: `apps/web/src/shared/screener/filterEngine.ts`
- Create: `apps/web/src/shared/screener/filterEngine.test.ts`
- Create: `apps/web/src/shared/screener/ScreenerWorkbench.tsx`
- Create: `apps/web/src/shared/screener/ScreenerWorkbench.test.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/MetricDrilldown.tsx`
- Modify: `apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`

**Produces:** 可排序、搜索、排除 ST/停牌、保存条件、加入观察池、横向比较和导出的同口径筛选会话。

- [x] 写筛选语义和保存恢复失败测试。
- [x] 实现纯函数筛选与本地持久化。
- [x] 将所有统计钻取名单接入筛选工作台。
- [x] 输出文件包含统计口径、交易日、来源和成员数量，不只导出代码。
- [x] 验证筛选后仍可进入三个研究入口。

### Task 5: 量化真实性审计

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/backtest.py`
- Modify: `apps/api/src/qibao_api/zhongshu/backtest.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/web/src/features/backtest/BacktestPanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Test: `apps/api/tests/contracts/test_backtest.py`
- Test: `apps/api/tests/zhongshu/test_backtest.py`
- Test: `apps/web/src/features/backtest/BacktestPanel.test.tsx`

**Produces:** 手续费、滑点、成交限制、停牌/退市处理、前视检查、样本内外、滚动验证、候选入选与排除原因的审计快照。

- [x] 先写不可成交涨跌停、手续费滑点和前视边界失败测试。
- [x] 扩展回测请求快照和结果契约。
- [x] 将候选入选、排除和数据不足原因持久化到策略快照。
- [x] 未满足样本门槛时不输出胜率、Sharpe 或稳定性结论。
- [x] 前端用门槛标签和证据明细展示，不用单一高分替代审计。

### Task 6: 统一提醒中心

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/unified_events.py`
- Create: `apps/api/src/qibao_api/a_shares/alert_inbox.py`
- Create: `apps/api/src/qibao_api/contracts/alert_inbox.py`
- Create: `apps/api/tests/a_shares/test_alert_inbox.py`
- Create: `apps/web/src/features/alerts/AlertCenter.tsx`
- Create: `apps/web/src/features/alerts/AlertCenter.test.tsx`
- Modify: `apps/web/src/features/speech/AnomalyVoiceAnnouncer.tsx`

**Produces:** 按事件指纹去重、证据合并、优先级、冷却期、静默时间和语音资格统一处理的提醒收件箱。

- [x] 写同事件多来源合并、冷却、静默和升级失败测试。
- [x] 实现不可变事件指纹与提醒状态机。
- [x] 语音只消费高优先级、未播报且证据达标事件。
- [x] 点击提醒定位股票、板块和 K 线真实时间节点。
- [x] 设置页只保存音色、语速、静默和优先级，不保存来源授权冗余项。

### Task 7: 今日决策记录闭环

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/decision_journal.py`
- Modify: `apps/api/src/qibao_api/a_shares/decision_journal.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Create: `apps/web/src/features/decision-journal/TodayDecisionJournal.tsx`
- Create: `apps/web/src/features/decision-journal/TodayDecisionJournal.test.tsx`
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`

**Produces:** 关联股票、筛选会话、市场风格、数据快照哈希、观察理由、风险、失效条件、后续表现和复盘结论的追加式记录。

- [x] 写旧日志迁移、追加不可修改、同日查询和快照关联失败测试。
- [x] 扩展 SQLite 表并以兼容迁移保留现有记录。
- [x] 在个股观察、公司研究、量化和筛选工作台提供“记录本次判断”。
- [x] 今日研判展示按时间排列的判断、证据和后续结果。
- [x] 盘后任务只补写真实表现，不改写原始判断。

### Task 8: 全站验收与便携 EXE 交付

**Files:**
- Modify: `docs/verification/2026-08-13-platform-decision-workbench-v7.md`
- Verify: `scripts/build-portable.ps1`
- Verify: `scripts/run-portable-smoke.ps1`

- [x] 运行 API 全量测试、Web 全量测试和生产构建。
- [x] 运行 UTF-8 严格解码、乱码扫描和 `git diff --check`。
- [x] 重建便携 EXE，确认八个持久目录保留。
- [x] 烟测首页、信息总览、筛选、量化、提醒和今日研判。
- [x] 核验测试端口释放、本程序无测试残留、通达信未被关闭或控制。
- [x] 记录 EXE SHA-256、启动耗时、接口状态和真实数据边界。
