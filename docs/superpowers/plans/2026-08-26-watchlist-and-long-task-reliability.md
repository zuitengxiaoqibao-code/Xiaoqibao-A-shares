# A 股自选与长任务可靠性实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让个股观察自选股可持久保存、可在后台保温更新，并消除公司研究与首次涨停因长任务和执行器竞态造成的笼统超时。

**Architecture:** 自选股以便携目录 `config/a-share-watchlist.json` 为真实配置源，前端 localStorage 仅作秒开快照和离线回退。公司研究与首次涨停使用缓存优先、后台任务隔离；应用关闭时先取消并等待任务，再关闭线程执行器。

**Tech Stack:** FastAPI、Pydantic、SQLite/JSON 配置、React、TypeScript、Vitest、pytest、PyInstaller portable EXE。

## Global Constraints

- 只交付 Windows portable EXE；localhost 仅用于内部验证。
- 不关闭或控制用户正在运行的正式 EXE 与通达信。
- 中文源文件按 UTF-8 处理，手工修改使用 `apply_patch`。
- 保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 持久目录。

---

### Task 1: 自选股应用级持久化

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/watchlist_repository.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/a_shares/test_watchlist_repository.py`
- Test: `apps/api/tests/routes/test_watchlist.py`

- [x] 原子 JSON 保存、六位 A 股代码校验、去重和损坏文件回退。
- [x] 增加 `GET /api/v1/a-shares/watchlist` 与 `PUT /api/v1/a-shares/watchlist`。
- [x] 运行 `pytest apps/api/tests/a_shares/test_watchlist_repository.py apps/api/tests/routes/test_watchlist.py -q`，结果 5 passed。

### Task 2: 前端双层缓存和自选状态

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/watchlist.ts`
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Modify: `apps/web/src/shared/TaskActivityStatus.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/stock-cockpit/watchlist.test.ts`
- Test: `apps/web/src/features/stock-cockpit/StockSelector.test.tsx`
- Test: `apps/web/src/shared/TaskActivityStatus.test.tsx`
- Test: `apps/web/src/app/App.test.tsx`

- [x] 启动先显示本地快照，再从后端配置校准。
- [x] 搜索、候选、自选行显示醒目的加入/已自选文字按钮。
- [x] 左侧显示加载、更新、休市、实时监控中和失败状态。
- [x] 运行相关 Vitest，结果 41 passed。

### Task 3: 长任务与生命周期隔离

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/company_research_tasks.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research_ai_tasks.py`
- Modify: `apps/api/src/qibao_api/routes/first_limit_up.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/a_shares/test_company_research_tasks.py`
- Test: `apps/api/tests/routes/test_first_limit_up.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

- [x] 公司研究服务增加异步关闭并等待取消任务。
- [x] 首次涨停刷新复用单日后台任务，短预算返回当前缓存/扫描结果。
- [x] 执行器关闭后的后台循环安静退出；退出时清理路由级后台任务。
- [x] 运行相关 pytest，结果 37 passed。

### Task 4: 交付验证

**Files:**
- Run: `scripts/build-portable.ps1`
- Run: `scripts/run-portable-smoke.ps1`

- [x] 完成乱码扫描、全量测试、便携 EXE 重建和真实启动烟测；源码扫描、`git diff --check`、API `1737 passed，1 skipped`、前端相关测试 `41 passed`、Vite 构建和新 `dist/XiaoQiBao-Portable/xiaoqibao.exe` 隔离 smoke 均通过。
