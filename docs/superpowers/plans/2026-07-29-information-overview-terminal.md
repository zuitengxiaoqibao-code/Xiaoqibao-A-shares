# Information Overview Terminal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增与参考截图同构的“信息总览”一级页面，用轻量聚合 API 展示真实市场情绪、指数分时、异动、新闻和板块榜单。

**Architecture:** 后端以一个容错聚合服务统一当前截止时间，腾讯来源只负责指数分钟线与批量行情，本地仓库负责情绪、新闻、热点和首次涨停。前端以独立 `market-overview` feature 呈现浅色高密度终端，保持现有页面视觉和路由不变。

**Tech Stack:** Python 3.12、FastAPI、Pydantic 2、httpx、React 19、TypeScript 5.8、ECharts 5.6、Vitest、PyInstaller onedir。

## Global Constraints

- 新菜单名固定为“信息总览”，位于“今日研判”上方，路由固定 `/market-overview`。
- 不复制截图中的第三方品牌、联系方式、视频水印和社交悬浮层。
- 不使用截图静态数字、随机数或无法验证的主力净额。
- A 股涨红跌绿；缺失字段显示 `--` 并保留质量状态。
- 腾讯响应按 GBK 解码；新闻 API 不得返回完整历史库。
- 保留现有所有路由、侧栏行为和可转债独立数据域。
- 修改中文文件后必须执行乱码扫描、测试和构建。

---

### Task 1: Market overview contracts and Tencent parsers

**Files:**
- Create: `apps/api/src/qibao_api/contracts/market_overview.py`
- Create: `apps/api/src/qibao_api/gongbu/tencent_overview.py`
- Test: `apps/api/tests/contracts/test_market_overview.py`
- Test: `apps/api/tests/gongbu/test_tencent_overview.py`

**Interfaces:**
- Produces `MarketOverviewResponse`, `OverviewIndexQuote`, `OverviewMinutePoint`, `OverviewAnomaly`, `OverviewSector`, `OverviewSectorStock`.
- Produces `parse_index_quotes(raw: bytes)`, `parse_index_minutes(payload: bytes, instrument: str)`, and `TencentOverviewSource.fetch(indices, symbols)`.

- [ ] Write parser/contract tests using GBK index fixtures, valid JSON minute fixtures, malformed rows and partial batches.
- [ ] Run focused tests and confirm failure because modules do not exist.
- [ ] Implement immutable contracts and strict parsers; incomplete individual rows are skipped with warnings, not fabricated.
- [ ] Run `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/contracts/test_market_overview.py tests/gongbu/test_tencent_overview.py -q` and require PASS.

### Task 2: Local-first overview aggregation and API

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Create: `apps/api/src/qibao_api/routes/market_overview.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/a_shares/test_market_overview.py`
- Test: `apps/api/tests/routes/test_market_overview.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces `MarketOverviewService.current(now: datetime) -> MarketOverviewResponse`.
- Produces `GET /api/v1/a-shares/market-overview`.

- [ ] Write tests for complete data, Tencent failure with last-success fallback, no cache partial response, 30-item news limit, sector grouping and stable snapshot timestamps.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement aggregation from `MarketSentimentRepository`, `NewsRepository`, `FirstLimitUpRepository`, `FundFlowRepository` and `TencentOverviewSource`.
- [ ] Add a 5-second thread-safe last-success cache for Tencent results and isolate each source failure into `warnings`.
- [ ] Wire service and router without fetching network data during API startup.
- [ ] Run `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/test_market_overview.py tests/routes/test_market_overview.py tests/libu_compliance/test_main_lifespan.py -q` and require PASS.

### Task 3: Navigation, route and typed frontend API

**Files:**
- Create: `apps/web/src/features/market-overview/types.ts`
- Create: `apps/web/src/features/market-overview/api.ts`
- Test: `apps/web/src/features/market-overview/api.test.ts`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`
- Modify: `apps/web/src/app/App.tsx`

**Interfaces:**
- Adds `BeginnerView = "market_overview"`.
- Adds `MarketOverviewLoader = (signal?: AbortSignal) => Promise<MarketOverviewResponse>`.
- Adds stable path mapping `/market-overview`.

- [ ] Write failing navigation and route tests proving the new entry precedes “今日研判”.
- [ ] Write failing API tests for success, structured backend error and abort behavior.
- [ ] Add types, fetcher, App prop wiring and route rendering placeholder.
- [ ] Run `pnpm --dir apps/web test -- src/features/beginner-shell/BeginnerNavigation.test.tsx src/features/dashboard/Dashboard.test.tsx src/features/market-overview/api.test.ts` and require PASS.

### Task 4: High-density overview page and ECharts interaction

**Files:**
- Create: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Create: `apps/web/src/features/market-overview/MarketTemperatureGauge.tsx`
- Create: `apps/web/src/features/market-overview/OverviewMinuteChart.tsx`
- Create: `apps/web/src/features/market-overview/OverviewFeatureRail.tsx`
- Create: `apps/web/src/features/market-overview/OverviewTables.tsx`
- Create: `apps/web/src/features/market-overview/overview.css`
- Test: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Test: `apps/web/src/features/market-overview/OverviewMinuteChart.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`

**Interfaces:**
- `MarketOverviewView` consumes `load`, optional `onOpenAShare(symbol)`, and manages refresh/filter/selection state.
- `OverviewMinuteChart` consumes minute points, anomalies and selected anomaly ID.

- [ ] Write tests for five information layers, refresh toggle, 5-second polling, visibility pause, feature filtering, anomaly selection, sector selection and A-share navigation.
- [ ] Run focused tests and verify component-missing failures.
- [ ] Build the exact density map: top strip, three-row feature rail, refresh toolbar, three-column workspace, two bottom tables.
- [ ] Use ECharts line plus markLine; never render synthetic points when `minute_series` is empty.
- [ ] Implement loading, partial, stale, empty and error states without blanking healthy regions.
- [ ] Run `pnpm --dir apps/web test -- src/features/market-overview` and require PASS.

### Task 5: Responsive and visual integration

**Files:**
- Modify: `apps/web/src/features/market-overview/overview.css`
- Modify: `apps/web/src/app/theme.css` only for shared shell compatibility.

- [ ] Verify desktop at 1440x900: no horizontal page overflow; chart/list/table proportions match the reference.
- [ ] Verify 1280x720: top strip remains scannable and bottom tables reachable.
- [ ] Verify 768x1024 and 390x844: feature rail/table scroll horizontally, primary regions stack, text does not overlap.
- [ ] Repair contrast, focus-visible, hover, loading and reduced-motion states.
- [ ] Keep all overview-specific colors scoped under `.market-overview-page`.

### Task 6: Full verification and portable build

**Files:**
- Modify: `docs/roadmap.md` only for the completed information-overview milestone.

- [ ] Run Ruff on `apps/api/src` and `apps/api/tests`.
- [ ] Run backend suite with isolated `QIBAO_DATA_DIR`.
- [ ] Run complete frontend Vitest suite and `pnpm --dir apps/web build`.
- [ ] Scan touched Chinese files for Unicode replacement characters, mojibake and repeated question marks.
- [ ] Restart the local API, verify `/api/v1/a-shares/market-overview` and `/market-overview` return successfully.
- [ ] Run `scripts/build-portable.ps1` and `scripts/run-portable-smoke.ps1`.
- [ ] Inspect `git diff --check` and do not stage unrelated user changes.
