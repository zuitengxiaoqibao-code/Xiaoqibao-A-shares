# 数据真实性与快速研究闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一交易日、快照证据、刷新复用和钻取边界，提升一树-A股观测台的真实性、速度和研究可追溯性。

**Architecture:** 复用现有 `dailySnapshotCache`、`incrementalResource`、`coalescedFetch`、字段证据和共享快照；新增轻量交易日工具与快照水位适配器，逐步接入四个核心页面，避免大规模重写。后端继续以真实通达信/现有真实源为准，缺失只产生明确不可用状态。

**Tech Stack:** React 19、TypeScript、Vitest、FastAPI、pytest、ECharts、PyInstaller。

## Global Constraints

- 只交付 Windows 便携 EXE，不生成浏览器或 HTML 交付物。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。
- 不使用模拟行情、随机数据、零值或无关字段填充缺失数据。
- A 股红色表示上涨/改善，绿色表示下跌/恶化。
- 保留便携版 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。
- 修改后运行聚焦测试、相关回归、生产构建、乱码扫描、`git diff --check`、便携 EXE smoke。

---

### Task 1: 统一交易日与快照有效性工具

**Files:**
- Create: `apps/web/src/shared/tradingDayContext.ts`
- Create: `apps/web/src/shared/tradingDayContext.test.ts`
- Modify: `apps/web/src/shared/dailySnapshotCache.ts`
- Modify: `apps/web/src/shared/marketOverviewCache.ts` 或现有市场缓存实现文件

**Produces:** `shanghaiTradingDay`, `marketPhase`, `isSameTradingDaySnapshot` 和统一的 `SnapshotFreshness` 类型；缓存读取必须显式返回交易日、来源和状态。

- [ ] 写测试：盘前允许最近已知交易日作为 previous-close；盘中只接受当前交易日；跨日缓存不返回实时状态。
- [ ] 运行聚焦 Vitest，确认新增测试先失败。
- [ ] 实现最小交易日和阶段判断，复用现有上海时区格式化逻辑。
- [ ] 将同日判断接入每日快照缓存，保留现有公开读取形状并增加可选元数据。
- [ ] 运行缓存相关测试，确认空响应和跨日缓存边界通过。

### Task 2: 全站统一数据水位文案

**Files:**
- Modify: `apps/web/src/shared/evidence/DataWatermarkStrip.tsx`
- Modify: `apps/web/src/shared/visualization/VisualPrimitives.tsx`
- Modify: `apps/web/src/features/market-overview/MarketDataWatermarkCenter.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Create: `apps/web/src/shared/evidence/freshnessCopy.ts`
- Create: `apps/web/src/shared/evidence/freshnessCopy.test.ts`

**Produces:** 统一的“数据就绪/部分覆盖/历史快照/不可用/读取失败”文案、交易日、采集时间、覆盖率和缺口原因展示，禁止内部英文阻断码直接出现在界面。

- [ ] 写状态映射测试，覆盖旧日期、覆盖率不足、来源不可用和真实就绪。
- [ ] 运行测试确认失败。
- [ ] 提取状态文案与原因映射，保留原始错误码仅在诊断层。
- [ ] 接入水位条和日线修复中心。
- [ ] 运行前端证据组件和市场总览测试。

### Task 3: 数据域级刷新与页面切换复用

**Files:**
- Modify: `apps/web/src/shared/coalescedFetch.ts`
- Modify: `apps/web/src/shared/incrementalResource.ts`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`

**Produces:** 页面切换保留完整快照，后台只刷新变化数据；同一数据域并发请求合并；空响应、旧响应和区块失败不清空当前内容。

- [ ] 写回归测试：切页复用同日快照、刷新失败保留快照、旧响应不覆盖新响应。
- [ ] 运行测试确认失败。
- [ ] 接入现有单飞请求和增量资源，按数据域设置刷新频率。
- [ ] 移除重复启动整页加载状态的触发点。
- [ ] 运行四个页面聚焦测试和生产构建。

### Task 4: 统计钻取与股票名称完整性

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/MetricDrilldown.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceInsightDashboard.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`
- Modify: `apps/web/src/shared/instruments/*`
- Modify: corresponding API contracts/routes when member data is missing

**Produces:** 可还原的统计数字统一支持点击筛选；股票条目始终显示名称与六位代码；只有聚合统计时显示明确边界，不提供虚假代表样本。

- [ ] 写测试：点击统计数字得到成员列表；缺名称时显示“名称待补齐”；不可还原时显示聚合说明。
- [ ] 运行测试确认失败。
- [ ] 接入共享证券目录和成员快照。
- [ ] 将钻取目标统一映射到个股观察、公司研究和量化分析。
- [ ] 运行信息总览全量回归。

### Task 5: 量化与研究决策证据深化

**Files:**
- Modify: `apps/web/src/features/quant-analysis/CandidateFunnel.tsx`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantShadowLedgerPanel.tsx`
- Modify: `apps/web/src/features/company-research/ResearchDecisionLedger.tsx`
- Modify: relevant API contracts and snapshot services

**Produces:** 推荐条目显示有效样本数、覆盖率、入选理由、淘汰理由、触发条件、失效条件、仓位依据和证据日期；研究与量化共享当前股票和同日缓存。

- [ ] 写测试：真实样本不足时显示不可用/部分覆盖；候选缺字段不能进入 ready；触发和失效条件可见。
- [ ] 运行测试确认失败。
- [ ] 接入现有真实候选过程、策略快照和影子账本。
- [ ] 在公司研究和量化页面共享选择状态与缓存版本。
- [ ] 运行量化、研究和 API 相关测试。

### Task 6: EXE 验收与交付

**Files:**
- Modify: `docs/verification/2026-08-13-data-truth-speed-research-loop.md`
- Modify: `scripts/build-portable.ps1` only if verification exposes a release regression
- Modify: `scripts/run-portable-smoke.ps1` only if verification exposes a smoke gap

- [ ] 运行 API 全量测试和 Web 全量测试。
- [ ] 运行 TypeScript/Vite 生产构建、UTF-8/乱码扫描和 `git diff --check`。
- [ ] 运行 `scripts/build-portable.ps1`，保留八个持久目录。
- [ ] 运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`，确认首页、信息总览、量化分析、公司研究和数据设置状态。
- [ ] 核验通达信 PID 与 `127.0.0.1:17709` 监听不变，烟测进程退出。
- [ ] 写入验证报告并标明剩余的真实数据不可用项。
