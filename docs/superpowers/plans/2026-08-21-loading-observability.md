# 加载状态与研究性能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为一树-A股观测台增加全局加载状态中心，并修复个股事件 K 线与公司研究的慢加载、无限等待和失败不透明问题。

**Architecture:** 前端使用轻量活动任务账本驱动左侧状态中心；事件 K 线采用缓存首屏和有界增量刷新；公司研究使用后端单源/总时限与前端停滞检测，保留真实缓存和状态。

**Tech Stack:** React、TypeScript、FastAPI、asyncio、pytest、Vitest、PyInstaller。

## Global Constraints

- EXE 是唯一用户入口。
- 不关闭、重启或控制通达信，不控制鼠标和桌面。
- 不伪造行情、AI、进度或数据完整状态。
- 修改中文文件后执行 UTF-8/乱码扫描、全量测试和生产构建。

### Task 1: 全局状态中心

**Files:**
- Create: `apps/web/src/shared/taskActivity.ts`
- Create: `apps/web/src/shared/TaskActivityStatus.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/shared/TaskActivityStatus.test.tsx`

- [ ] 写测试：展示 AI 未配置、处理中任务、失败任务和真实百分比；无任务不发起轮询。
- [ ] 运行 Vitest 聚焦测试确认失败。
- [ ] 实现活动任务注册/更新/完成/失败 API 和导航下方状态面板。
- [ ] 运行聚焦测试确认通过。

### Task 2: 事件 K 线分层加载

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/stock_timeline.py`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Modify: `apps/web/src/features/stock-timeline/api.ts`
- Test: `apps/api/tests/a_shares/test_stock_timeline.py`
- Test: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`

- [ ] 写测试：已有缓存时首次渲染不清空，后端事件查询使用有界日期/数量，增量刷新合并而非替换。
- [ ] 运行聚焦测试确认失败。
- [ ] 实现缓存首屏、任务阶段上报、增量合并和有界事件读取。
- [ ] 运行聚焦测试确认通过。

### Task 3: 公司研究超时隔离

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research_tasks.py`
- Modify: `apps/web/src/features/company-research/api.ts`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Test: `apps/api/tests/a_shares/test_company_research_tasks.py`
- Test: `apps/web/src/features/company-research/api.test.ts`

- [ ] 写测试：单源超时转 partial、总任务超时结束、前端停滞轮询给出中文阶段原因并保留缓存。
- [ ] 运行聚焦测试确认失败。
- [ ] 实现单源超时、总时限、前端停滞检测和任务活动状态接入。
- [ ] 运行聚焦测试确认通过。

### Task 4: 全量验收与 EXE

**Files:**
- Create: `docs/verification/2026-08-21-loading-observability.md`
- Modify: `docs/superpowers/plans/2026-08-21-loading-observability.md`

- [ ] 运行 API/Web 全量、Ruff、生产构建和乱码扫描。
- [ ] 运行 `scripts/build-portable.ps1`，保留八个持久目录。
- [ ] 运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`、恢复演练和发布质量门禁。
- [ ] 记录真实耗时、状态和 EXE 哈希，提交文档。
