# 数据大屏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增“数据大屏 / 数字孪生可视化大屏”菜单，为投影仪和长期驻留场景提供真实 A 股市场的高信息密度、16:9、动态可视化总览。

**Revision 2:** 在首版基础上扩展为全屏投影监控台，增加市场情绪/风险、真实分时、板块资金流、个股雷达、官方事件、数据范围审计和带粒子脉冲的来源流场。

**Architecture:** 页面作为 `Dashboard` 的独立懒加载视图，使用现有 `MarketOverviewLoader` 首屏快照和 `RealtimeProvider` 单一实时总线；Presenter 只做确定性聚合与格式化，不生成或推断行情。CSS 负责 16:9 面板栅格、响应式降级和低负担动画，数据状态始终标明实时、缓存、部分或不可用。

**Tech Stack:** React 19, TypeScript, Vite, lucide-react, 现有 ECharts/实时总线与主题变量。

## Global Constraints

- 只能使用真实接口或已验证缓存，不得使用随机数字、模拟行情或旧日期冒充当前数据。
- 复用现有 `MarketOverviewLoader`、`RealtimeProvider`，不得为每个模块建立重复行情连接。
- 中文 UI 保持 UTF-8；所有用户可见数据状态必须简洁、明确、可追溯。
- 不修改或关闭通达信，不删除 `config/data/news/cache/logs/models/exports/backups`。
- 最终交付入口仍是 Windows EXE；修改后运行便携构建与 smoke 脚本。

### Task 1: 数据大屏 Presenter 与视图

**Files:**
- Create: `apps/web/src/features/data-screen/types.ts`
- Create: `apps/web/src/features/data-screen/presenter.ts`
- Create: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Create: `apps/web/src/features/data-screen/dataScreen.css`
- Test: `apps/web/src/features/data-screen/presenter.test.ts`
- Test: `apps/web/src/features/data-screen/DataScreenView.test.tsx`

**Interfaces:**
- `buildDataScreenModel(snapshot: MarketOverviewResponse | null): DataScreenModel`
- `DataScreenView({ load, onOpenAShare })` consumes `MarketOverviewLoader` and emits selected stock navigation.

- [x] **Step 1: Write failing presenter tests** covering breadth totals, red-up/green-down classes, index sorting, unavailable state, and same-day observed time.
- [x] **Step 2: Run `pnpm --filter @qibao/web test -- src/features/data-screen/presenter.test.ts` and confirm failure because files do not exist.**
- [x] **Step 3: Implement deterministic model types and presenter.** Preserve nulls as unavailable and cap list sizes for projection readability.
- [x] **Step 4: Implement view with header status, market breadth, index center, sector/flow cards, anomaly timeline, news strip and source footer.** Use `aria-busy` while loading and keep previous snapshot visible during refresh.
- [x] **Step 5: Add CSS with a fixed 16:9-inspired grid, no nested cards, clear red-up/green-down tokens, no continuous marquee, and reduced-motion handling.**
- [x] **Step 6: Run focused tests and refine until green.**

### Task 2: 导航、路由与共享实时订阅

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Test: `apps/web/src/features/dashboard/Dashboard.test.tsx`
- Test: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`

- [x] **Step 1: Add failing assertions for `data_screen` view, `/data-screen` path, menu label and active state.**
- [x] **Step 2: Run the two focused tests and verify failure.**
- [x] **Step 3: Add the new view type, path mapping, lazy import and `loadMarketOverview` prop wiring.**
- [x] **Step 4: Add the navigation entry without regrouping existing menus.**
- [x] **Step 5: Run focused dashboard/navigation tests.**

### Task 3: 动态层与刷新语义

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Modify: `apps/web/src/features/data-screen/dataScreen.css`
- Test: `apps/web/src/features/data-screen/DataScreenView.test.tsx`

- [x] **Step 1: Add failing tests for realtime topic updates, event de-duplication, fallback snapshot retention, and reduced-motion class.**
- [x] **Step 2: Run focused tests and verify failure.**
- [x] **Step 3: Subscribe to `market_overview` and `news_events` via `useRealtimeTopic`; merge only newer sequence events and retain the last verified snapshot on transient failure.**
- [x] **Step 4: Add lightweight pulse/glow transitions for changed values and source-health badges; avoid whole-page remounts or scrolling animations.**
- [x] **Step 5: Run focused tests and visual build check.**

### Task 4: 全量验证与 Windows EXE 交付

**Files:**
- Modify: `docs/superpowers/plans/2026-09-01-data-screen.md` (checklist status only)

- [x] **Step 1: Run `pnpm --filter @qibao/web test`.**
- [x] **Step 2: Run `pnpm --filter @qibao/web build`.**
- [x] **Step 3: Run UTF-8/乱码扫描 and `git diff --check`.**
- [x] **Step 4: Run `scripts/build-portable.ps1 -SkipTests` and preserve persistent release directories.**
- [x] **Step 5: Run a staged EXE startup/API/static-route smoke.** The staged EXE launched and reached the API checks. The full fourteen-menu smoke remains blocked by the existing quant strategy 3-second performance gate (`4326ms`), not by the data-screen route.

### Revision 2 validation

- [x] 扩展 Presenter 读取分时、板块资金流、个股样本、情绪/风险、官方事件和数据范围字段，所有缺失值保持为不可用。
- [x] 增加全屏/退出全屏控制、16:9 画布布局、五项核心指标带、真实分时折线、涨跌生态、资金流向、个股雷达和官方事件区。
- [x] 将数字孪生流场扩展为“数据源 → 指数 → 板块 → 个股 → 事件”，使用呼吸、渐变和有限粒子动画，不使用持续跑马。
- [x] 修复辅助字体低于 12px 的可读性回归；全量 Web 测试 `139 files / 812 passed`、生产构建、UTF-8 扫描和 `git diff --check` 通过。
- [x] 重新生成暂存便携 EXE：`dist/XiaoQiBao-Portable-staged-ab900a20181f4b818dfa35a00b365f54/XiaoQiBao-Portable/xiaoqibao.exe`；健康接口 `ready`、`/data-screen` 为 `200`、首页根节点存在。
- [x] 完整十四菜单烟测仍不作为本轮通过依据：既有量化策略接口曾以约 `4466ms` 超过 3 秒性能门槛；未放宽门槛，未关闭或控制通达信。

## Self-review checklist

- Data model never substitutes random or stale cross-day values.
- All loading/error states have a visible status region and retain verified prior data when possible.
- Desktop 1920x1080 and narrow windows have no horizontal overflow.
- New menu is flat and does not reclassify existing navigation.
- All tests and build commands are recorded before claiming completion.

## Revision 3: 视口回归修复（2026-09-01）

- [x] Remove the duplicate viewport declarations that allowed the old fullscreen `overflow:auto` rule to win at some sizes.
- [x] Constrain the data-screen shell to one viewport with `min-height: 0`, `max-height: 100vh`, and a bounded grid row.
- [x] Keep panel bodies and the data-screen grid shrinkable/clipped while preserving natural document scrolling below 1250px.
- [x] Add regression coverage for stale scroll restoration and rerun the web suite: 139 files / 813 tests passed.
- [x] Rebuild the staged portable EXE and preserve persistent directories. The staged EXE smoke started successfully; the run stopped at the pre-existing quant strategy refresh gate (`4326ms` over `3000ms`).

## Revision 4: 便携版更新切换修复（2026-09-01）

- [x] 修复延期清单不会在下次启动重试的问题：启动时自动将 `pending-update.deferred.json` 原子恢复为 `pending-update.json`。
- [x] 修复新版本应用成功后旧延期清单残留的问题，避免旧版本再次被排队覆盖。
- [x] 新增启动更新回归测试；桌面入口与更新模块测试 `21 passed`，前端全量测试 `139 files / 813 tests passed`。
- [x] 重新构建便携 EXE 到 `dist/XiaoQiBao-Portable-staged-b10356fcbd3c4eada7699b5217ff2d20/XiaoQiBao-Portable/xiaoqibao.exe`。
- [x] 旧正式目录仍因现有进程占用而未覆盖；正式目录已写入指向该暂存版的 `pending-update.json`，关闭旧程序后下一次启动会自动切换。
- [x] 暂存版实际启动并创建窗口；完整 smoke 在既有公司研究数据源超时处停止，不属于 EXE 启动失败。
