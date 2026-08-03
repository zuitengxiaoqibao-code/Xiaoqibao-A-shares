# 信息总览全功能工作台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让信息总览功能栏中的全部菜单拥有独立、真实、可解释的数据工作台。

**Architecture:** 后端扩充本地通达信市场快照的代表股票集合，前端以功能目录和统一渲染器生成不同工作台。统一框架负责刷新、错误、图表、榜单和证据，功能定义只描述数据视图与解读，避免重复组件。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、React 19、TypeScript、ECharts、Vitest、pytest。

## Global Constraints

- 本地通达信优先。
- 不生成随机数据或无法验证的投资结论。
- 中文文件只用 `apply_patch` 修改并在完成前扫描乱码。
- 不改变 `/market-overview` 路由。

---

### Task 1: 扩充本地市场代表股票

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/market_overview.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Test: `apps/api/tests/contracts/test_market_overview.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_overview.py`

**Interfaces:**
- Produces: `OverviewFeatureStock` and `OverviewMarketSnapshot.market_stocks`.

- [ ] 写入失败测试，要求快照保留现价、昨收、开高低、成交量和成交额。
- [ ] 运行目标测试，确认因字段缺失失败。
- [ ] 实现涨停、跌停、炸板、涨幅、跌幅和成交额并集去重选择器。
- [ ] 运行目标测试并确认通过。

### Task 2: 将代表股票暴露给总览接口

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Modify: `apps/api/src/qibao_api/contracts/market_overview.py`
- Test: `apps/api/tests/a_shares/test_market_overview.py`
- Test: `apps/api/tests/routes/test_market_overview.py`

**Interfaces:**
- Consumes: `OverviewMarketSnapshot.market_stocks`.
- Produces: `MarketOverviewResponse.market_stocks`.

- [ ] 写入失败测试，要求本地市场股票进入响应且失败时为空数组。
- [ ] 运行测试确认失败原因正确。
- [ ] 实现响应映射和向后兼容默认值。
- [ ] 运行路由与服务测试。

### Task 3: 建立完整功能目录

**Files:**
- Create: `apps/web/src/features/market-overview/featureCatalog.ts`
- Create: `apps/web/src/features/market-overview/featureCatalog.test.ts`
- Modify: `apps/web/src/features/market-overview/OverviewFeatureRail.tsx`

**Interfaces:**
- Produces: `MARKET_FEATURES`, `MarketFeatureDefinition`, `featureRows`.

- [ ] 写入失败测试，断言全部标签唯一、都有分组、视图、解释和风险边界。
- [ ] 运行测试确认目录尚不存在。
- [ ] 实现完整功能矩阵并让功能栏使用同一数据源。
- [ ] 运行目录测试。

### Task 4: 实现功能数据选择与图表

**Files:**
- Create: `apps/web/src/features/market-overview/featureSelectors.ts`
- Create: `apps/web/src/features/market-overview/featureSelectors.test.ts`
- Create: `apps/web/src/features/market-overview/MarketFeatureChart.tsx`

**Interfaces:**
- Consumes: `MarketOverviewResponse`, `MarketFeatureDefinition`.
- Produces: `buildFeatureWorkspace()` and ECharts option.

- [ ] 写入涨停、跌停、炸板、题材、板块、资讯和成交活跃选择器失败测试。
- [ ] 运行测试确认缺少实现。
- [ ] 实现确定性选择器、指标和来源边界。
- [ ] 运行选择器测试。

### Task 5: 实现独立工作台并接入菜单

**Files:**
- Create: `apps/web/src/features/market-overview/MarketFeatureWorkspace.tsx`
- Create: `apps/web/src/features/market-overview/MarketFeatureWorkspace.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Modify: `apps/web/src/features/market-overview/types.ts`

**Interfaces:**
- Consumes: `buildFeatureWorkspace()`.
- Produces: 功能标题、指标、图表、榜单、证据和新手解读。

- [ ] 写入失败测试，点击不同菜单后工作台标题和内容发生变化。
- [ ] 运行测试确认仍是旧的区域高亮行为。
- [ ] 实现工作台并替换旧的筛选映射。
- [ ] 运行市场总览组件测试。

### Task 6: 验证

**Files:**
- Verify only.

- [ ] 运行后端相关测试与 Ruff。
- [ ] 运行全部前端测试和生产构建。
- [ ] 扫描中文乱码并运行 `git diff --check`。
- [ ] 实机遍历全部菜单，确认每个入口都有独立内容。
- [ ] 在 1440px 和 390px 截图检查布局。
