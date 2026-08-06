# 一树 A 股观测台全站可视化与证据可信度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 用统一的真实数据可视化内核和证据状态契约，逐批升级全站页面，并通过便携 EXE 交付。

**Architecture:** 先建立共享视觉原语、ECharts 主题和证据状态渲染器，再迁移信息总览、今日研判、个股观察、公司研究和量化分析；市场专题页按菜单语义逐页绑定专属图表组合。后端继续复用既有 API 与本地通达信/腾讯/缓存来源，第三阶段才扩展已实测的 TdxQuant 只读能力。

**Tech Stack:** React 19, TypeScript 5.8, ECharts 5.6, CSS, Vitest, FastAPI, Pydantic, pytest, PyInstaller portable EXE。

## Current Progress (2026-08-06)

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 共享证据状态与图表原语 | 已完成 | `784400f`、`f5ef932`、`b72d456` |
| 信息总览缓存优先与启动状态 | 已完成 | `1bdcb50`、`docs/verification/2026-08-06-cache-startup-performance.md` |
| 全局可读性基线 | 已完成 | `ea2995a`；正文 14px、辅助文字 13px |
| 专题工作区语义拆分 | 已完成基础版本，持续审查 | 50 个独立定义，`workspaceRegistry.test.ts` |
| 不可用/陈旧证据诚实展示 | 持续推进 | `f5dcd65`；专题页不再冒充实时连接 |
| TdxQuant 只读深度接入 | 基础能力探测完成，个股估值/行业与可转债条款已接入，其他能力持续推进 | 设置页已显示 8 类只读能力状态；`get_more_info`/`get_stock_info`/`get_kzz_info` 已进入业务契约，专业数据包与高阶字段仍需补齐 |
| 全站最终验收与 EXE 交付 | 本轮通过，仍需持续回归 | 前端 430 项、API 1070 项、EXE 烟测通过 |

## Remaining Goals

以下目标在全部验收通过前保持为持续计划，不以单个阶段完成代替项目完成：

- [ ] 完成 50 个专题页的真实字段覆盖审查，清理残留重复、空白和无关代理指标。
- [x] 将通达信本地只读能力扩展为可探测的行情、财务、板块、事件和公式能力，并在设置页显示能力状态。
- [x] 将已探测为 ready 的通达信能力接入对应业务字段；`get_more_info`/`get_stock_info` 已进入个股基本面与估值，`get_kzz_info` 已进入可转债条款诊断，`get_ipo_info` 已提供严格的新股/新债日历只读接口，`formula_process_mul_*` 已提供严格的公式批量只读接口并在量化分析仪表盘展示；专业数据包或接口不支持时继续保持不可用，不使用代理字段。
- [ ] 继续优化个股观察、公司研究和量化分析的动态刷新、缓存恢复和图表密度。
- [ ] 对所有页面执行字号、颜色、响应式和红涨绿跌回归检查。
- [ ] 每次源代码改动后重建便携 EXE，保留持久目录并运行真实烟测。

## 2026-08-06 增量记录

- 已完成设置页只读能力探测：证券目录、实时行情、板块目录、扩展行情与估值、基础财务与行业、新股与新债日历、可转债条款、通达信公式计算。
- 探测只调用 JSON-RPC 只读方法，不连接券商、不调用交易接口；接口异常只保留错误类型，不回显异常原文或凭据。
- 首页实时更新失败且存在当日缓存时，启动层增加“继续使用缓存”操作，避免错误遮罩持续阻塞已有完整数据。
- 个股诊断已增加可选本地 TdxQuant 明细源：仅在设置启用且桥接返回明确字段时使用 `get_more_info`/`get_stock_info`；本地桥不可用、空响应或字段不足时自动回到既有 mootdx 财务源，估值区仍保留来源和不可用边界。
- 可转债条款诊断已增加只读 `get_kzz_info` 优先源；只有正股代码、转股价、到期日、转股起始日和剩余规模全部明确返回时才接受，否则自动回退公开条款源。
- 新增 `/api/v1/tdx/local/ipo-calendar`：仅接受明确的代码、名称、类型和申购日期，上市日/中签日缺失保持为空；错误包、空包和不完整行返回 `unavailable`。
- 新增 `/api/v1/tdx/local/formula`：仅允许 `formula_process_mul_*` 只读公式方法，量化分析仪表盘按当前标的读取明确返回的公式字段；缺失字段不转成 0，结果不可用时显示原因。

## Global Constraints

- 所有用户交付通过 `dist/XiaoQiBao-Portable/xiaoqibao.exe`，不交付 HTML 或 localhost。
- A 股上涨/改善使用 `--market-up: #f04f5f`，下跌/恶化使用 `--market-down: #2fcf91`。
- 缺失、陈旧、冲突和未验证数据必须有状态，不用随机、截图静态数字或无关字段填空。
- AI 只能解释已有证据，不创建证券代码、价格、新闻事实或评分。
- 用户可见正文不低于 12px；桌面、窄屏和 390px 视口不能出现遮挡或横向溢出。
- 构建前保留 `config/data/news/cache/logs/models/exports/backups`。

### Task 1: 可视化状态与图表原语

**Files:**
- Create: `apps/web/src/shared/visualization/types.ts`
- Create: `apps/web/src/shared/visualization/chartTheme.ts`
- Create: `apps/web/src/shared/visualization/VisualPrimitives.tsx`
- Create: `apps/web/src/shared/visualization/visualization.css`
- Test: `apps/web/src/shared/visualization/VisualPrimitives.test.tsx`

**Deliverable:** 统一的 `EvidenceState`、`DataStateNotice`、`ChartPanel`、`MetricBand`、`GaugeRow`、`RankBarList` 和 `EvidenceBadge`，提供 ready/partial/stale/unavailable/error 五种状态。

### Task 2: ECharts 主题与图形工厂

**Files:**
- Modify: `apps/web/src/features/quant-analysis/QuantChart.tsx`
- Create: `apps/web/src/shared/visualization/chartOptions.ts`
- Test: `apps/web/src/shared/visualization/chartOptions.test.ts`

**Deliverable:** 统一字体、坐标轴、tooltip、零轴、涨跌色和缺失点断线配置；提供 bar-line、dual-axis、radar、heatmap、treemap、gauge、candlestick 等工厂函数。

### Task 3: 全局 CSS 基线迁移

**Files:**
- Modify: `apps/web/src/app/tokens.css`
- Modify: `apps/web/src/app/theme.css`
- Modify: `apps/web/src/app/terminal.css`
- Test: `apps/web/src/app/typography.test.ts`, `apps/web/src/app/layout-safety.test.ts`

**Deliverable:** 统一深色终端背景、边框、间距、字号、状态色和 reduced-motion；清理局部浅色和冲突的粉色上涨语义。

### Task 4: 信息总览基准页

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/OverviewTables.tsx`
- Modify: `apps/web/src/features/market-overview/OverviewMinuteChart.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Test: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`, `apps/web/src/features/market-overview/OverviewMinuteChart.test.tsx`

**Deliverable:** 顶部指标带、指数分时、异动时间线、板块热力、热门板块/股票表统一为截图所示的高密度图形结构，保持真实数据和自动刷新。

### Task 5: 今日研判与个股观察

**Files:**
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/KeySignalDashboard.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Test: corresponding existing tests plus new visual state assertions

**Deliverable:** 三阶段状态带、资金流向混合图、K 线事件索引、亮点/风险标签和来源账本统一展示。

### Task 6: 公司研究与量化分析

**Files:**
- Modify: `apps/web/src/features/company-research/ResearchVisualSummary.tsx`
- Modify: `apps/web/src/features/company-research/companyResearch.css`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Test: existing company research and quant tests plus chart option assertions

**Deliverable:** 财务五维组合图、估值双轴历史、资产负债 treemap、研究仪表和策略投票仪表统一为真实数据状态驱动的面板。

### Task 7: 市场专题页语义迁移

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`
- Test: `DistinctMarketWorkspace.test.tsx`, `workspaceRegistry.test.ts`

**Deliverable:** 每个菜单绑定独立图形组合：涨停/连板/炸板、竞价、龙虎榜、突破、低位放量、热点/复盘等不再重复同一模板。

### Task 8: TdxQuant 只读增强

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/web/src/features/data-settings/LocalSourceSettingsSection.tsx`
- Test: `apps/api/tests` relevant TDX tests and data settings tests

**Deliverable:** 能力探测、`get_more_info`/`get_stock_info`/`get_ipo_info`/`get_kzz_info`/`formula_process_mul_*` 只读接入；专业数据包缺失时返回明确降级，不碰交易接口。

### Task 9: EXE 交付与全站验收

**Files:**
- Modify: `docs/verification/2026-08-06-sitewide-visual-evidence-redesign.md`

**Commands:**
- `pnpm --dir . --filter "@qibao/web" test`
- `.venv/Scripts/python.exe -m pytest apps/api/tests -q`
- `pnpm --dir . --filter "@qibao/web" build`
- `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -SkipTests`
- `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`

**Deliverable:** 便携 EXE、测试证据、SHA-256 和持久目录保留记录。
