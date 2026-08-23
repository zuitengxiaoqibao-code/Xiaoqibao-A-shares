# 全站速度、数据与信息架构统一实施计划

> **执行要求：** 使用 `executing-plans` 按任务逐项实现。每项先写失败测试，再实现，再运行聚焦验证；所有任务完成后统一构建和验证 Windows 便携 EXE。

**目标：** 十四个一级菜单都在打开后快速展示缓存或真实结果，任何未缓存查询在十秒内给出可用内容或明确降级；共享采集、快照、请求、刷新、任务进度和性能门禁，清除重复请求、重复计算、重复版面和无意义提示。

**架构：** `共享数据运行时 -> 不可变领域快照 -> 页面最小快照 -> 单一增量流 -> 后台重任务`。现有 EXE 与内嵌 React 保持不变。

**技术栈：** Python、FastAPI、SQLite/DuckDB、React、TypeScript、SSE、pytest、Vitest、PyInstaller。

## 全局约束

- EXE 是唯一交付和用户验收入口，不生成浏览器交付物。
- 不启动、关闭、重启或控制通达信，不控制鼠标和桌面。
- 不伪造行情、新闻、AI、候选、概率、进度或 `ready` 状态。
- 已有内容在刷新时不可被全页遮罩或空数据替换。
- 所有错误提示中文化，并保留失败来源、阶段和缓存时间。
- 中文文件只用 `apply_patch` 等 UTF-8 安全方式编辑。
- 每个阶段通过聚焦测试、乱码扫描和 `git diff --check` 后再提交。

## Task 1：性能基线、规范化路由与十秒门禁

**Files:**
- Modify: `apps/api/src/qibao_api/operations/performance_store.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/tests/operations/test_performance_store.py`
- Modify: `apps/api/tests/routes/test_operations.py`
- Create: `scripts/verify-menu-performance.ps1`
- Create: `scripts/verify-menu-performance.tests.ps1`
- Create: `docs/architecture/menu-runtime-ledger.md`

- [x] 写失败测试：股票代码、日期、任务 ID 和查询串不同的同类 API 聚合到同一规范路由；记录 HTTP 状态、缓存/降级来源和当前发布代次。
- [x] 实现路由模板规范化和性能数据库向后兼容迁移，旧样本可见但不参与当前门禁。
- [x] 建立 14 菜单、首屏 API、依赖快照、刷新频率、缓存策略和 10 秒结果契约总账。
- [x] 新增可自动运行的 14 菜单性能门禁，验证缓存首屏、真实降级和最长等待。
- [x] 运行聚焦 pytest、PowerShell 自测、乱码扫描与 `git diff --check`。

## Task 2：统一前端 API 客户端

**Files:**
- Create: `apps/web/src/shared/apiClient.ts`
- Create: `apps/web/src/shared/apiClient.test.ts`
- Modify: `apps/web/src/shared/coalescedFetch.ts`
- Modify: `apps/web/src/shared/fetchJsonWithProgress.ts`
- Modify: `apps/web/src/shared/performance/requestLedger.ts`
- Modify: `apps/web/src/features/*/api.ts`

- [x] 写失败测试：查询参数顺序规范化、相同 GET 合并、调用者独立取消、超时中文化、缓存元数据、last-good 保留和副作用请求不自动重试。
- [x] 实现统一 `apiClient.get/getCached/post` 契约和领域并发上限。
- [x] 机械迁移全部直接 `fetch()` 与零散 JSON/错误处理；保留文件下载和 SSE 的流式例外。
- [x] 删除已被统一客户端完全替代的重复包装器，更新请求账本统计。
- [x] 运行全量 Web 测试、TypeScript/Vite 构建、乱码扫描与 `git diff --check`。

## Task 3：应用级实时总线与可见性调度

**Files:**
- Create: `apps/web/src/shared/realtime/RealtimeProvider.tsx`
- Create: `apps/web/src/shared/realtime/realtimeStore.ts`
- Create: `apps/web/src/shared/realtime/RealtimeProvider.test.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Modify: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.ts`
- Modify: `apps/web/src/features/news-alerts/useBreakingNewsAlerts.ts`
- Modify: `apps/web/src/features/monitor-center/MonitorTtsAnnouncer.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`

- [x] 写失败测试：全应用只有一个 SSE，按主题订阅；隐藏页面不刷新；断线只启动一个指数退避轮询；恢复 SSE 后停止轮询。
- [x] 实现应用级实时 Provider、主题版本和可见性订阅。
- [x] 迁移行情、事件、量化、新闻、告警和运维的重复轮询；只保留时钟显示、任务状态等必要定时器。
- [x] 验证切换菜单不会重复建连接、刷新不会重置页面、通达信进程不受影响。
- [x] 运行聚焦与全量 Web 测试、生产构建和静态定时器审计。

## Task 4：共享领域快照与页面首屏契约

**Files:**
- Modify: `apps/api/src/qibao_api/operations/shared_snapshots.py`
- Modify: `apps/api/src/qibao_api/operations/precompute_snapshots.py`
- Create: `apps/api/src/qibao_api/operations/page_snapshots.py`
- Create: `apps/api/src/qibao_api/contracts/page_snapshots.py`
- Modify: relevant files under `apps/api/src/qibao_api/routes/`
- Test: `apps/api/tests/operations/test_page_snapshots.py`
- Test: relevant route tests

- [x] 写失败测试：同一市场横截面只计算一次并被多个页面投影；快照含交易日、时间、来源、覆盖率、哈希、新鲜度和缺失原因。
- [x] 为十四个菜单实现最小首屏快照，不把历史表、回测明细和 AI 长文本放入首屏。
- [x] 将页面打开时的外部抓取移出请求同步路径；缓存缺失时启动有界后台任务并返回真实阶段。
- [x] 为行情/指数/K 线、市场生态、新闻、量化、公司研究和运维分别落实刷新频率。
- [x] 运行共享快照并发/复用测试、路由测试和 API 全量测试。

## Task 5：十四菜单职责和信息总览收敛

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`
- Modify: menu view components under `apps/web/src/features/`
- Modify: `apps/web/src/app/theme.css`
- Test: navigation, workspace registry, layout and menu contract tests

- [x] 写失败测试：14 个菜单保持同一级；每个菜单只有唯一首屏职责；信息总览标记 8 个核心工作区并只按当前选择挂载其余工作区。
- [x] 把重复能力移动到正确菜单或钻取区，不删除已存在的有效业务能力。
- [x] 统计数字提供明细钻取；股票代码和名称成对展示；证据时间与来源可见。
- [x] 去除全页加载工作台和无业务意义的空卡片；保留各菜单必要且不同口径的数据审计。
- [x] 统一字号、密度、卡片/表格/图表规格和红涨绿跌，验证窗口化与最大化布局。
- [x] 运行 Web 全量、布局安全测试和生产构建；EXE smoke 验证窗口可见与首屏可用。

## Task 6：渐进加载与 AI 变更触发

**Files:**
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisView.tsx`
- Modify: news, stock, first-limit, late-session, risk and operations views
- Modify: corresponding API services and task coordinators
- Test: focused API and Web suites for all heavy menus

- [x] 写失败测试：缓存立即显示，区块独立补齐，单区失败不清空其他区块，十秒内结束等待并指出来源。
- [x] 公司研究按事实摘要、财务/同业/估值、催化/反方、AI 解释分阶段加载。
- [x] 量化按市场策略、候选/TICK、事件 K 线、回测/风险、AI 解释分阶段加载，重扫在后台。
- [x] 新闻、个股、首板、尾盘、风险和运维使用缓存优先、独立失败的渐进加载契约。
- [x] AI 通过冻结快照 ID、内容哈希、阈值事件、用户请求或收盘冻结触发，并记录输入快照版本。
- [x] 运行重任务取消、超时、缓存恢复、错误中文化和真实性测试。

## Task 7：启动与路由资源优化

**Files:**
- Modify: `apps/web/src/features/dashboard/routePreload.ts`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/api/src/qibao_desktop/window.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: desktop/server startup tests and route preload tests

- [x] 写失败测试：启动后不一次预载所有路由；只预载相邻高概率菜单，空闲且系统负载允许时才继续。
- [x] 缩短同步 import/装配路径，把非首屏服务延迟初始化到首次使用或后台阶段。
- [x] 保留真实启动阶段和耗时，不用假进度；首窗与首页缓存不等待外部数据源。
- [x] 运行冷/热启动与真实 EXE smoke，首窗保持 1 秒内，API 和首页状态按真实门禁记录。

## Task 8：死代码、重复资源和超大模块治理

**Files:**
- Modify/Delete: only files proven unreachable by build graph, route registry, import graph and tests
- Refactor: `apps/api/src/qibao_api/main.py`
- Refactor: market overview and quant strategy modules
- Modify: package/build manifests and ownership tests

- [x] 生成前端构建分包、Python/PyInstaller 导入交叉引用和 EXE 包含清单，区分源码资产与运行时资产。
- [x] 完成四项证据审计；没有足够证据的文件不删除，测试、文档和恢复资产继续保留。
- [x] 装配、采集、计算、投影和页面契约已由独立模块承载；保持 `main` 公共装配入口兼容。
- [x] 运行全量测试、生产构建和启动/页面性能回归。

## Task 9：全量验证、EXE、恢复与发布证据

**Files:**
- Create: `docs/verification/2026-08-21-sitewide-speed-data-clarity.md`
- Modify: this plan checklist
- Update: durable project memory after all evidence is confirmed

- [x] 运行 API 全量 pytest、Web 全量 Vitest、Ruff、TypeScript/Vite 生产构建。
- [x] 运行中文 UTF-8/乱码扫描、`git diff --check`、14 菜单性能门禁和数据真实性门禁。
- [x] 运行 `scripts/build-portable.ps1`，确认八个持久目录完整保留。
- [x] 运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`，验证真实 EXE 能启动且关键菜单返回真实状态。
- [x] 运行恢复演练、迁移校验、发布质量门禁和包体清单检查。
- [x] 记录真实性能、失败/降级、EXE 路径、提交和 SHA-256。
- [x] 更新项目记忆并运行 Vault 校验、乱码扫描和 Git diff 检查。

## 2026-08-23 完成审计补强

- [x] 将十四菜单门禁从样本自测升级为真实便携 EXE 逐项采样。
- [x] 将十四项端到端耗时、缓存首帧、状态和降级原因写入签名发布清单。
- [x] 发布质量门禁重新计算十四菜单结果，缺失、超时或无原因空结果直接阻断。
