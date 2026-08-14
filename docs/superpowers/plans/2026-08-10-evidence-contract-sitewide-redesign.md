# 一树-A股观测台全站证据契约重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成全站菜单语义、真实数据、专属展示、深度研究和性能体系重构，并通过便携 EXE 验收。

**Architecture:** 以菜单证据契约为中心，把数据采集、确定性计算、状态判定和可视化解耦。信息总览只做全市场发现，一级页面承载深度任务；不同频率的数据独立刷新并复用缓存。

**Tech Stack:** React 19、TypeScript、ECharts 5、FastAPI、Pydantic、SQLite、本地通达信、腾讯、东方财富、同花顺、新浪、巨潮、Microsoft Edge TTS。

## Global Constraints

- 用户只通过便携 EXE 检查产品。
- 所有数据必须真实、可追溯，不允许模拟值和无关代理字段。
- 红涨绿跌，未知灰色。
- 正文至少 13px，辅助标签至少 12px。
- 修改中文文件后执行乱码扫描。
- 用户可见修改后必须重建便携 EXE并运行实际烟测。
- 不关闭或控制通达信进程。

---

### Task 1: P0 历史指标真实性

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceInsights.ts`
- Test: `apps/web/src/features/market-overview/workspaces/workspaceInsights.test.ts`

- [x] 编写失败测试，要求百日新高和昨涨停在逐股数据存在时显示真实数量。
- [x] 运行聚焦测试并确认因当前固定 `unavailable` 失败。
- [x] 使用 `review.new_high_100` 和 `review.previous_limit_up` 生成真实指标。
- [x] 增加无复盘、空结果和来源不可用边界测试。
- [x] 运行聚焦测试和信息总览测试。

### Task 2: P0 阶段自适应默认入口

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Test: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`

- [x] 编写失败测试：异动为空时不得默认进入空白盘中异动工作区。
- [x] 定义开盘前、盘中、盘后和休市阶段的默认工作区选择规则。
- [x] 保留用户显式选择，后台刷新不得重置当前菜单。
- [x] 运行聚焦测试。

### Task 3: P0 菜单显示名称与兼容键分离

**Files:**
- Modify: `apps/web/src/features/market-overview/featureCatalog.ts`
- Modify: `apps/web/src/features/market-overview/OverviewFeatureRail.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`
- Test: corresponding market overview tests

- [x] 编写失败测试，要求兼容键保持不变但显示名称使用严谨名称。
- [x] 增加 `key`、`label`、`family` 菜单模型，不修改现有路由和缓存键。
- [x] 应用开盘检查、涨停复盘、观察热度榜、七维活跃榜、条件选股、产业链资料库和个股快览名称。
- [x] 对缺少委托数据的隔夜和竞价封单增加能力边界副标题。
- [x] 运行菜单、工作区和全站导航测试。

### Task 4: P0 样本范围和历史新鲜度

**Files:**
- Modify: `apps/web/src/features/market-overview/types.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceInsightDashboard.tsx`
- Modify: `apps/api/src/qibao_api/contracts/market_overview.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Test: frontend and API market overview tests

- [x] 编写失败测试，区分全市场聚合、代表股票样本和强势板块样本。
- [x] 在响应中增加明确样本范围元数据。
- [x] 历史日期落后时把历史结论标记为 stale，同时保留真实数据。
- [x] 页面展示 `293 只代表样本`、`12 个强势板块样本`等准确口径。
- [x] 运行前后端聚焦测试。

### Task 5: P1 信息总览结构重构

**Files:**
- Split and modify files under `apps/web/src/features/market-overview/`
- Test: all market overview frontend tests

- [x] 建立市场首页、竞价异动、涨停生态、题材板块、资金席位、量价筛选六类工作区。
- [x] 每个工作区使用独立数据问题和专属可视化，不共享无意义的通用卡片组合。
- [x] 将信息总览中的个股详情限制为快速抽屉和深度页面跳转。
- [x] 完成响应式布局、字号和红涨绿跌检查。

### Task 6: P2 数据源补全

**Files:**
- Create focused source adapters under `apps/api/src/qibao_api/gongbu/`
- Modify matching contracts, services and route tests

- [x] 接入并缓存逐笔成交或真实大单方向。
- [x] 接入板块净流入时间序列。
- [x] 区分官方投资事项日期和新闻日期。
- [x] 接入问财语义搜索时明确接口身份和授权状态。
- [x] 补充行业研报、机构 EPS 预测样本中位、公告、解禁、融资融券和股东户数；明确该 EPS 口径不是同花顺官方一致预期，不生成价格目标。

### Task 7: P3 深度工作台

**Files:**
- Modify focused modules under company-research, quant-analysis, beginner-risk and history-review
- Test: matching frontend and API suites

- [x] 公司研究增加同行自动选择、行业空间证据、前向估值、催化时间线和逻辑失效条件。
- [x] 量化分析增加因子贡献、触发证据、仓位投票、滚动验证和回测稳定性。
- [x] 风险提醒增加市场、个股、事件、数据和策略五层风险矩阵。
- [x] 历史复盘增加策略管理、参数版本、样本外验证和收益归因。

### Task 8: P4 性能与交付

**Files:**
- Modify frontend resource hooks, API caches, desktop startup and build scripts
- Test: full frontend, API and portable smoke suites

- [x] 将行情、板块、新闻、历史和重计算任务分频刷新。
- [x] 使用缓存先显示和后台静默更新，禁止整页加载遮罩回归。
- [x] 空闲时预加载一级页面代码，保留页面状态。
- [x] 运行全量前端与 API 测试、生产构建、乱码扫描和 diff 检查。
- [x] 运行 `scripts/build-portable.ps1`，保留持久目录。
- [x] 运行 `scripts/run-portable-smoke.ps1`，记录冷启动、API、首页和关键页面耗时。
