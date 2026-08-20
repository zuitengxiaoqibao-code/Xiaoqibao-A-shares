# 全站性能与数据架构升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 让一树-A股观测台在 Windows EXE 中做到首屏快速可见、缓存优先、慢任务后台化、AI 状态准确、真实数据可追溯，并逐步消除各菜单的重复模板。

**Architecture:** 保留现有 EXE 外壳、数据库和发布链路，新增统一的快照状态/缓存索引/任务调度边界。页面始终先渲染最近一次可用快照，最新请求只允许以更完整且更新的快照替换；慢速分析拆成后台任务，使用任务 ID、进度和状态轮询，不阻塞首页或其他菜单。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、DuckDB/SQLite、React 19、TypeScript、Vite、PyInstaller、pytest、Vitest。

## Global Constraints

- Windows EXE 是唯一用户交付和验收入口，不交付 HTML 页面。
- 保留 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。
- 不关闭、重启或控制通达信；不控制鼠标或桌面。
- 不使用模拟行情、模拟新闻或伪造 AI 结果补齐真实数据。
- 中文源文件使用 UTF-8 安全编辑；修改后执行乱码扫描、测试、构建和 `git diff --check`。
- 任何 `partial/stale/unavailable/error` 必须保留真实原因，不得伪装为 `ready`。

## 阶段 0：基线审计与可观测性

**目标：** 建立每个菜单、接口和数据源的实际耗时、缓存命中、空结果原因与重复请求基线。

**主要文件：**
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/*.py`（仅增加统一请求追踪字段，不改业务口径）
- Modify: `apps/web/src/shared/performance/requestLedger.ts`
- Create: `docs/verification/2026-08-20-sitewide-performance-baseline.md`

**验收：** EXE smoke 输出首页、信息总览、量化、公司研究、风险、新闻的首屏和完整请求耗时；每项包含缓存命中率与失败原因。

## 阶段 1：统一快照契约与缓存优先

**目标：** 所有重点接口统一返回 `data/status/freshness/observed_at/generated_at/source/coverage/cache/progress/error/trace_id` 语义；空响应不能覆盖已有非空缓存。

**主要文件：**
- Create: `apps/api/src/qibao_api/contracts/runtime_snapshot.py`
- Create: `apps/api/src/qibao_api/runtime_snapshot.py`
- Modify: `apps/api/src/qibao_api/contracts/task_progress.py`
- Modify: `apps/web/src/shared/incrementalResource.ts`
- Modify: `apps/web/src/shared/dailySnapshotCache.ts`
- Create: `apps/web/src/shared/snapshotState.ts`

**验收：** 增加 API/前端回归测试：旧快照存在时，新的空响应、旧日期响应、低覆盖响应都不能清空当前内容；失败时继续展示缓存并显示中文原因。

## 阶段 2：本地配置与 AI 状态持久化

**目标：** 配置只从本地持久化仓库读取一次并缓存；AI 状态拆分为“未配置、已配置未验证、已连接、连接失败、超时、限流、模型错误”，不再把调用失败显示成未配置。

**主要文件：**
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/api/src/qibao_api/settings_repository.py`
- Create: `apps/api/src/qibao_api/ai_status.py`
- Modify: `apps/web/src/features/company-research/CompanyResearchAIInsight.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`
- Add tests beside each changed module.

**验收：** 保存配置后重启 EXE 仍能读取；连接失败显示具体中文原因；已有规则分析不因 AI 失败消失。

## 阶段 3：EXE 启动与统一任务调度

**目标：** 窗口先出现，首屏读本地配置/缓存，慢任务后台化；同一任务去重、可取消、可重试，页面切换不触发重复全量扫描。

**主要文件：**
- Modify: `apps/api/src/qibao_desktop/window.py`
- Modify: `apps/api/src/qibao_desktop/startup_progress.py`
- Create: `apps/api/src/qibao_api/runtime_tasks.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/web/src/shared/coalescedFetch.ts`

**验收：** 冷启动窗口 ≤300ms、API ≤2s、首页缓存 ≤3s；慢任务不阻塞首页；后台任务状态可见。

## 阶段 4：量化分析与候选池

**目标：** TICK 限定当前标的，市场策略读取快照，候选池分粗筛/精筛，AI 解释最后执行；保留上一轮候选池直到新结果完整。

**主要文件：**
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/web/src/features/quant-analysis/*.tsx`
- Add API/Web regression tests.

**验收：** 量化摘要 ≤3s；后台候选任务有真实进度；空结果展示无结果原因；新空结果不能覆盖上一轮候选池。

## 阶段 5：公司研究与风险提醒

**目标：** 先显示公司研究摘要和风险总览，再后台补齐财务、估值、竞争、新闻、反方检查和详细风险。

**主要文件：**
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/api/src/qibao_api/a_shares/preparation.py`
- Modify: `apps/web/src/features/company-research/*`
- Modify: `apps/web/src/features/beginner-shell/BeginnerRiskView.tsx`
- Add API/Web regression tests.

**验收：** 公司研究摘要 ≤3s；风险摘要 ≤3s；扩展数据失败不清空摘要；每个失败环节有中文原因。

## 阶段 6：新闻、事件 K 线与板块资金

**目标：** 新闻按事件去重并绑定股票/板块/K 线；事件 K 线区分无事件、缺 K 线、时间不匹配和数据源失败；板块资金重新核对净流入口径和日期。

**主要文件：**
- Modify: `apps/api/src/qibao_api/gongbu/news_linking.py`
- Modify: `apps/api/src/qibao_api/routes/event_impact.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Modify: `apps/web/src/features/news-intelligence/*`
- Modify: `apps/web/src/features/stock-timeline/*`
- Modify: `apps/web/src/features/market-overview/workspaces/*`

**验收：** 每条热点可定位股票/板块/K 线；资金动图展示数据时间、覆盖率、成分贡献，禁止成交额冒充净流入。

## 阶段 7：菜单差异化

**目标：** 依据菜单名称建立独立数据契约、指标、筛选和图表，禁止所有菜单复用同一套股票列表和数字卡片。

**主要文件：**
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceSelectors.ts`
- Add workspace-specific tests for all registered menus.

**验收：** 每个菜单至少有独立主指标、独立明细筛选、独立空数据原因和对应的 A 股字段；菜单切换不串数据。

## 阶段 8：EXE 发布与真实性验收

**目标：** 通过真实便携 EXE 完成冷/热启动、页面切换、缓存恢复、配置恢复、任务失败保留旧快照、八个持久目录和通达信保护验证。

**主要文件：**
- Use: `scripts/build-portable.ps1`
- Use: `scripts/run-portable-smoke.ps1`
- Use: `scripts/verify-release-quality.ps1`
- Create: `docs/verification/2026-08-20-sitewide-performance-final.md`

**验收：** API/Web/Ruff/构建/乱码扫描通过；EXE 实际启动成功；真实数据边界按 `ready/partial/unavailable` 如实交付；无本程序测试残留；通达信状态不变。

