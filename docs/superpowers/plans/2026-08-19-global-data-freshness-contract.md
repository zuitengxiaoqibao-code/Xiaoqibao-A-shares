# 全站数据日期与新鲜度一致性修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让所有菜单明确区分查询日期、实际数据日期、零散最新记录、生成时间和刷新原因，禁止历史缓存冒充当前数据。

**Architecture:** 后端以 `MarketReviewSnapshot` 为历史复盘统一事实快照，新增向后兼容的刷新语义字段；独立资金流、新闻、通达信导入和研究缓存沿用各自真实时间字段，但统一由前端状态组件呈现。所有统计数字、明细和钻取都绑定同一个快照日期，数据不足只标记 partial/stale/unavailable，不补造股票或日期。

**Tech Stack:** Python/Pydantic/FastAPI、React/TypeScript、Pytest/Vitest、PowerShell portable build/smoke。

## Global Constraints

- Windows EXE 是唯一用户交付入口；不生成浏览器页面交付物。
- A 股数据只展示真实来源；零散日期不能冒充全市场日期。
- 中文项目文件保持 UTF-8；修改后执行乱码扫描、测试和 `git diff --check`。
- 不关闭、重启或控制用户的通达信，不控制鼠标或桌面。

### Task 1: 复盘日期契约与失败测试

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/market_review.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_review.py`
- Test: `apps/api/tests/a_shares/test_market_review.py`
- Test: `apps/api/tests/gongbu/test_local_market_review.py`

- [x] 写测试：主导日期落后 `as_of` 时必须是 `partial/stale` 语义并保留真实明细；零散最新日期不能成为 `latest_trade_date`。
- [x] 运行聚焦测试，确认在实现前失败。
- [x] 增加 `expected_trade_date`、`refresh_required`、`refresh_reason` 三个可选字段并保持旧 JSON 可反序列化。
- [x] 让 `build_market_review` 在覆盖不足、主导日期落后时设置中文原因及刷新标志；非交易日按实际交易日规则不误报。
- [x] 运行聚焦测试确认通过。

### Task 2: 本地历史缓存与后端总览裁决

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/local_market_review.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Modify: `apps/api/src/qibao_api/contracts/market_overview.py`（仅必要时）
- Test: `apps/api/tests/a_shares/test_market_overview.py`

- [x] 写测试：旧缓存可以返回但必须标记刷新；数据库最新零散日期不应阻断真实主导日快照；刷新失败必须保留旧缓存并返回原因。
- [x] 运行测试确认失败。
- [x] 修正本地缓存读取与仓库日期裁决，避免把全局最大日期误当完整覆盖日期。
- [x] 在总览构建中统一传播 review 的刷新状态、实际日期和警告，不以 `as_of` 覆盖历史日期。
- [x] 运行 API 聚焦测试确认通过。

### Task 3: 前端历史菜单统一状态条与日期绑定

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceInsightDashboard.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceInsights.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceSelectors.ts`
- Test: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`
- Test: `apps/web/src/features/market-overview/workspaces/workspaceInsights.test.ts`

- [x] 写测试：首板、连板、昨涨停、百日新高、突破、低位放量、龙虎榜等菜单在 stale/partial 时显示查询日期、实际日期、零散日期、覆盖率、更新时间和原因。
- [x] 运行测试确认失败。
- [x] 抽取统一 `ReviewFreshnessBanner` 或等价展示组件，所有依赖 review 的菜单复用。
- [x] 所有统计卡片和明细表显示同一快照日期；无成员明细时明确“只有聚合值”。
- [x] 股票名称、代码、数据日期和来源同时展示，点击钻取不跨日期。
- [x] 运行 Web 聚焦测试确认通过。

### Task 4: 独立数据源日期审计与前端提示

**Files:**
- Modify: relevant API contracts/services for fund flow, TDX import, candidate sentiment, company research, sector fund flow, news.
- Modify: corresponding overview/workspace components.
- Test: relevant API/Web tests.

- [x] 为资金流、通达信导入、候选情绪、公司研究、板块资金、新闻分别建立“数据截至/生成时间/质量/原因”断言。
- [x] 对过期但真实的数据保留内容并显示 stale/partial，不显示“今日”或“当前”误导文案。
- [x] 新闻同时显示事件发生时间与抓取/核验时间。
- [x] 运行相关聚焦测试确认通过。

### Task 5: 全量验证与 EXE 交付

**Files:**
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`
- Create: `docs/verification/2026-08-19-global-data-freshness.md`

- [x] 运行 API/Web/Ruff/乱码扫描/`git diff --check`。
- [x] 执行 `scripts/build-portable.ps1 -SkipTests`，保留八个持久目录。
- [x] 执行隔离数据 smoke 和正式数据 smoke；记录真实 partial/stale/unavailable 边界，不放宽超时伪造通过。
- [x] 记录 EXE 路径、SHA-256、测试结果、仍缺失的真实数据源。
- [x] 更新项目记忆并完成计划复核。
