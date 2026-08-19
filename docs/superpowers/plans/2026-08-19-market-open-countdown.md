# 信息总览开盘倒计时与跨日隔离实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 盘前用真实倒计时替代昨日分时与异动，并在开盘后只展示当前交易日的真实数据。

**Architecture:** 后端负责交易日边界的数据隔离，前端负责缓存防御、状态计算和倒计时展示。两层都以 Asia/Shanghai 日期为准，确保旧缓存、慢响应和实时推送均不能把昨日事件混入今天。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、React 19、TypeScript、Vitest、CSS。

## Global Constraints

- 不生成模拟 K 线、模拟异动或模拟新闻。
- 不操作、关闭或重启通达信。
- 用户只通过 Windows 便携 EXE 验收。
- 中文文件只使用 `apply_patch` 修改，完成后执行乱码扫描。

---

### Task 1: 后端跨日时序数据隔离

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Test: `apps/api/tests/a_shares/test_market_overview.py`

**Interfaces:**
- Consumes: `MarketOverviewResponse`、`OverviewMinutePoint`、`OverviewAnomaly`、`OverviewLiveFeedItem`。
- Produces: 只包含当前上海交易日时序数据的总览响应。

- [ ] 写入昨日缓存盘前读取的失败测试，断言分钟线、异动和资讯为空。
- [ ] 运行测试并确认旧实现因保留昨日内容而失败。
- [ ] 增加统一的上海交易日过滤，并用于缓存读取、核心刷新和完整刷新。
- [ ] 运行后端聚焦测试确认通过。

### Task 2: 前端交易状态和缓存防御

**Files:**
- Create: `apps/web/src/features/market-overview/marketSessionDisplay.ts`
- Create: `apps/web/src/features/market-overview/marketSessionDisplay.test.ts`
- Modify: `apps/web/src/features/market-overview/marketOverviewCache.ts`
- Modify: `apps/web/src/features/market-overview/marketOverviewCache.test.ts`

**Interfaces:**
- Consumes: `market_data.phase`、当前时间、分钟点时间戳。
- Produces: `waiting_open/call_auction/awaiting_first_tick/live/postclose/closed` 展示状态及倒计时秒数。

- [ ] 写入六种交易状态和跨日前端缓存清理的失败测试。
- [ ] 运行测试并确认失败原因是状态函数缺失及旧缓存未隔离。
- [ ] 实现状态函数、倒计时格式和前端快照日期过滤。
- [ ] 运行相关测试确认通过。

### Task 3: 信息总览倒计时界面

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/market-overview/OverviewMinuteChart.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`

**Interfaces:**
- Consumes: Task 2 的交易状态与当天过滤后的分钟线、异动和资讯。
- Produces: K 线原位倒计时、首笔行情等待状态及开盘瞬间刷新。

- [ ] 写入盘前页面不显示昨日条目且显示倒计时的失败测试。
- [ ] 运行测试确认旧页面仍展示昨日内容。
- [ ] 实现秒级时钟、倒计时面板、当天数据选择和开盘归零刷新。
- [ ] 运行信息总览测试确认通过。

### Task 4: 发布验证

**Files:**
- Modify: `docs/verification/2026-08-19-market-open-countdown.md`

**Interfaces:**
- Consumes: 前三项实现和测试输出。
- Produces: 可追溯验证记录与最新便携 EXE。

- [ ] 运行 API/Web 聚焦测试与 Web 全量测试。
- [ ] 运行生产构建、UTF-8/乱码扫描和 `git diff --check`。
- [ ] 提交源码并执行 `scripts/build-portable.ps1`。
- [ ] 执行 `scripts/run-portable-smoke.ps1`，确认窗口、API、退出和端口释放。
