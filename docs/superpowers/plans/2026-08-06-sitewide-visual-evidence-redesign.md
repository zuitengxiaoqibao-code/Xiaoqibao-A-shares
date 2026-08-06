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
| 全站最终验收与 EXE 交付 | 本轮通过，仍需持续回归 | 前端 449 项、API 1099 项、EXE 烟测通过 |

## Remaining Goals

以下目标在全部验收通过前保持为持续计划，不以单个阶段完成代替项目完成：

- [x] 完成第一轮 50 个专题页的真实字段覆盖审查：缺失行情、成交额、板块字段不再转成 0；不满足必要字段的筛选、排行和强度指标不入选，页面显示 `--` / 未接入。
- [x] 将通达信本地只读能力扩展为可探测的行情、财务、板块、事件和公式能力，并在设置页显示能力状态。
- [x] 将已探测为 ready 的通达信能力接入对应业务字段；`get_more_info`/`get_stock_info` 已进入个股基本面与估值，`get_kzz_info` 已进入可转债条款诊断，`get_ipo_info` 已提供严格的新股/新债日历只读接口，`formula_process_mul_*` 已提供严格的公式批量只读接口并在量化分析仪表盘展示；专业数据包或接口不支持时继续保持不可用，不使用代理字段。
- [x] 完成个股观察 30 秒、公司研究 5 分钟的可见页面后台刷新，并在恢复可见时立即刷新；保留当日缓存、避免请求重叠，量化分析继续使用页面可见轮询。
- [x] 提升量化 TICK 图表的信息密度：增加 inside/slider 双层缩放导航，成交量按已验证涨跌方向使用红涨绿跌，缺失数据仍不绘制伪曲线。
- [x] 完成跨交易日缓存回归：缓存日期统一按 `Asia/Shanghai` 计算，交易日午夜边界不会误读上一日快照；通达信实时行情仅在明确返回 `MarketCapYi` 时把市值传入板块成分字段，单位不明的 `MarketValue` 保持不可用。
- [ ] 在本机通达信专业数据包实际可用后，继续扩展更多真实字段并逐菜单做数据源切换回归。
- [x] 将可延后的远程转债全量同步移到可取消后台任务，健康检查不再等待网络同步；业务 `lifespan-ready` 约 656ms，窗口首帧 118ms，修正烟测健康轮询后 API 就绪 4112ms、完整验证 4460ms。
- [x] 将 `exchange_calendars` 从 API 模块导入阶段移到首次交易日查询时构造；功能保持不变，新增懒加载回归。连续三次 EXE 烟测窗口 100-111ms、API 3423-3480ms、完整验证 3982-4126ms。
- [x] 将 Edge TTS 从 API 语音服务顶层导入移到首次请求语音时懒加载，并新增子进程回归测试；本轮 API 1093 项通过、1 项按环境跳过，便携 EXE 连续三次烟测通过。
- [x] 优化便携桌面启动就绪路径：`LocalApiServer` 只等待 Uvicorn 完成 lifespan，不再重复发起自探测 HTTP 请求；通达信 fallback 全市场扫描在便携运行时延后 2 秒启动，先展示当日缓存再刷新最新数据。API 1095 项通过、1 项按环境跳过，连续三次 EXE 烟测通过。
- [x] 将便携桌面 API 线程提前到窗口创建前启动，让 Python 导入、lifespan 初始化与 WebView 建窗并行；热启动 API 就绪降至 2.69-2.74 秒，窗口首帧保持 114-119ms。
- [x] 延后 DuckDB、mootdx、pandas 和 numpy 的顶层导入；BarRepository 首次真实日线操作时才初始化 DuckDB，备份和通达信客户端保持兼容的懒加载入口。便携 smoke 改为先等待 `lifespan-ready` 日志再发起 HTTP，避免 Windows 预绑定 socket 的早期取消连接触发 `WinError 64`。
- [ ] 继续压缩冷启动等待：窗口首帧已满足 3 秒目标，首次冷盘 API 仍约 9.36 秒，主要受 Windows 首次加载/安全扫描影响；后续继续审计 PyInstaller 冷磁盘读取和剩余重型模块导入，同时保留缓存优先和健康检查先可用。
- [x] 完成工作区、个股观察、公司研究、量化分析和全站测试的字号、颜色、红涨绿跌回归；窄屏/布局测试通过。
- [x] 本轮源代码改动后已重建便携 EXE，保留持久目录并运行真实烟测；后续每次源代码改动仍重复此验收。
- [x] 通达信桥已启用但暂不可用时，数据设置页在可见期间每 60 秒自动重探测，页面隐藏暂停、恢复可见立即探测，且不会打断手动检测或保存。
- 远程可转债全量同步不再阻塞 API lifespan：启动后后台执行，退出时显式取消并等待任务；烟测健康探测改为 1 秒轮询，避免把连接建立等待误计为 API 业务就绪时间。

## 2026-08-06 增量记录：专题指标证据边界

- [x] 收紧信息总览专题指标的“已就绪”边界：情绪分、市场风格、风险分、热度分、复盘质量/日期、上涨/下跌家数、两市成交额、题材叠加股票和龙虎榜均在必要字段缺失或样本为空时显示 `未接入/不可用`，不再显示 `--`、`待准备` 或 `0` 作为已验证结果。
- [x] 龙虎榜证据要求至少存在一条真实上榜记录；空列表即使没有后端警告，也不会被当作可验证席位数据。
- [x] 新增 5 个边界回归场景；前端全量 71 个测试文件、453 项通过；API 1099 项通过、1 项按环境跳过；Vite 生产构建通过；乱码扫描和 `git diff --check` 通过。
- [ ] 下一轮继续审计专题派生分数的可解释性和命名，明确哪些是原始字段、哪些是确定性派生指标，并在页面标签中给出计算口径。
- [x] 通达信本地 overview 后台刷新失败改为限频日志：首次失败、错误类型变化和每 20 次失败记录一次，恢复时记录一次；避免桥接不可达时重复写完整堆栈导致日志膨胀，同时保留诊断线索。

## 2026-08-06 后续增量：启动并行化与打包实验

- `packaging/xiaoqibao.spec` 的 `noarchive=True` 实验已完成并回退。独立 `.pyc` 文件使便携目录从 1,845 个文件增加到 4,558 个，热启动仅有轻微变化，首次冷盘启动约 10.76 秒，未证明有稳定收益；最终保留 `noarchive=False`，优先控制文件数量和冷盘扫描成本。
- 桌面 GUI 路径现在先准备便携运行目录、迁移旧数据并启动 API 线程，再创建 WebView；窗口显示与 API 导入/lifespan 初始化可以重叠。服务器仍在窗口失败或退出时统一释放。
- 本轮专项桌面与冷导入测试通过；前端 71 个测试文件、449 项通过；API 1,099 项通过、1 项按环境跳过；Vite 构建和便携 EXE 构建通过。
- 本轮 EXE 烟测（串行、无端口冲突）：窗口 102/118/111ms；API `/health` 2,664/2,387/2,414ms；完整验证 3,371/3,201/3,212ms；信息总览均为 `ready`，量化策略均为 `unavailable`（真实样本不足，不虚构）。
- 当前便携 EXE SHA-256：`C6BCBED43368E286AEE03A6CA2481E967ECC66D1813DC47B2F325E13D6B38487`；持久目录 `config/data/news/cache/logs/models/exports/backups` 均保留。

## 2026-08-06 增量记录

- 继续收紧专题与量化视觉真实性边界：龙虎榜/席位缺金额、连板缺高度、复盘缺量能时不再显示 0 值；市场风格、策略、公司研究和回测空值增加明确 unavailable 状态与中性空条样式。前端 444 项、API 1089 项通过；便携 EXE 烟测窗口 125ms、API 4645ms、完整验证 5041ms，SHA-256 为 `6C510317E60A482FEE6EF905B034CE0B5D731AA96F574473839AACD909764522`。

- 已完成设置页只读能力探测：证券目录、实时行情、板块目录、扩展行情与估值、基础财务与行业、新股与新债日历、可转债条款、通达信公式计算。
- 探测只调用 JSON-RPC 只读方法，不连接券商、不调用交易接口；接口异常只保留错误类型，不回显异常原文或凭据。
- 首页实时更新失败且存在当日缓存时，启动层增加“继续使用缓存”操作，避免错误遮罩持续阻塞已有完整数据。
- 个股诊断已增加可选本地 TdxQuant 明细源：仅在设置启用且桥接返回明确字段时使用 `get_more_info`/`get_stock_info`；本地桥不可用、空响应或字段不足时自动回到既有 mootdx 财务源，估值区仍保留来源和不可用边界。
- 可转债条款诊断已增加只读 `get_kzz_info` 优先源；只有正股代码、转股价、到期日、转股起始日和剩余规模全部明确返回时才接受，否则自动回退公开条款源。
- 新增 `/api/v1/tdx/local/ipo-calendar`：仅接受明确的代码、名称、类型和申购日期，上市日/中签日缺失保持为空；错误包、空包和不完整行返回 `unavailable`。
- 新增 `/api/v1/tdx/local/formula`：仅允许 `formula_process_mul_*` 只读公式方法，量化分析仪表盘按当前标的读取明确返回的公式字段；缺失字段不转成 0，结果不可用时显示原因。
- 量化公式面板按当前分析标的每 15 秒刷新一次，切换标的或卸载页面时释放旧定时器，避免旧股票响应覆盖新股票。

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
