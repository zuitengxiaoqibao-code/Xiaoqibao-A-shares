# 一树-A股观测台性能与维护闭环 v5.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成真实进度、快速启动、公司研究增量展示、下次启动更新、性能仪表盘、完整缓存与安全存储治理。

**Architecture:** 在现有 FastAPI/React/SQLite/便携启动器上增加小型独立模块，保留现有完整接口作为兼容层。后台工作使用任务登记表和轮询，缓存与更新使用版本信封及原子替换。

**Tech Stack:** Python 3.12、FastAPI、SQLite、React 19、TypeScript、Vitest、pytest、PyInstaller、pywebview。

## Global Constraints

- EXE 是唯一用户交付入口。
- 不生成模拟数据，不用缺失值补零，不把缓存冒充实时。
- 不关闭、重启或控制通达信及用户正在运行的观测台。
- 持久目录固定为 `config/data/news/cache/logs/models/exports/backups`。
- 中文文件只用 UTF-8 安全方式修改并在最终执行乱码扫描。

---

### Task 1: 通用真实任务进度

**Files:**
- Create: `apps/api/src/qibao_api/tasks/progress.py`
- Create: `apps/api/src/qibao_api/contracts/task_progress.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Test: `apps/api/tests/tasks/test_progress.py`
- Test: `apps/api/tests/routes/test_operations.py`

- [x] 写失败测试：无总量不显示百分比，有总量按真实 processed/total 计算，完成与失败状态不可回退。
- [x] 运行聚焦测试确认 RED。
- [x] 实现有界任务登记表和 `/api/v1/operations/tasks/{task_id}` 查询接口。
- [x] 运行聚焦测试确认 GREEN。

### Task 2: API 核心与扩展服务分层

**Files:**
- Create: `apps/api/src/qibao_api/bootstrap/lazy_service.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`
- Test: `apps/api/tests/bootstrap/test_lazy_service.py`

- [x] 写失败测试：扩展服务构造器在启动时不执行，首次依赖访问只执行一次，失败可重试且不会把核心健康标为 ready。
- [x] 运行测试确认 RED。
- [x] 实现线程安全异步延迟服务并迁移可安全延迟的公司研究增强与重型运行时。
- [x] 记录核心 ready 与扩展初始化耗时。
- [x] 运行启动专项测试确认 GREEN。

### Task 3: 公司研究分块增量展示

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/company-research/types.ts`
- Test: `apps/api/tests/a_shares/test_company_research.py`
- Test: `apps/web/src/features/company-research/CompanyResearchView.test.tsx`

- [x] 写失败测试：任务创建后返回六块状态；已完成块可先读取；单块失败不清空其他块；全部完成才生成 complete。
- [x] 运行前后端聚焦测试确认 RED。
- [x] 实现分块任务端点和前端缓存优先、逐块替换。
- [x] 运行聚焦测试确认 GREEN。

### Task 4: 下次启动原子更新

**Files:**
- Create: `apps/api/src/qibao_desktop/pending_update.py`
- Modify: `apps/api/src/qibao_desktop/entrypoint.py`
- Modify: `scripts/build-portable.ps1`
- Test: `apps/api/tests/desktop/test_pending_update.py`
- Test: `apps/api/tests/desktop/test_packaging.py`

- [x] 写失败测试：路径越界拒绝、持久目录不替换、成功清除清单、失败恢复旧版。
- [x] 运行测试确认 RED。
- [x] 实现 pending 清单、原子文件替换与 rollback。
- [x] 让旁路构建写入清单，但不操作运行中程序。
- [x] 运行专项测试确认 GREEN。

### Task 5: 页面与端点性能仪表盘

**Files:**
- Create: `apps/api/src/qibao_api/operations/performance_store.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/features/operations/types.ts`
- Test: `apps/api/tests/operations/test_performance_store.py`
- Test: `apps/web/src/features/operations/OperationsView.test.tsx`

- [x] 写失败测试：最近 10 次、P50、P95、失败率和命中率计算正确。
- [x] 运行测试确认 RED。
- [x] 实现非阻塞采样中间件、SQLite 聚合端点和默认折叠仪表盘。
- [x] 运行专项测试确认 GREEN。

### Task 6: 版本化完整快照治理

**Files:**
- Create: `apps/api/src/qibao_api/storage/snapshot_store.py`
- Modify: `apps/web/src/shared/dailySnapshotCache.ts`
- Test: `apps/api/tests/storage/test_snapshot_store.py`
- Test: `apps/web/src/shared/dailySnapshotCache.test.ts`

- [x] 写失败测试：版本/标的/完整性校验，partial 不覆盖 complete，原子写失败保留旧快照。
- [x] 运行测试确认 RED。
- [x] 实现后端原子信封和前端 v2 信封兼容迁移。
- [x] 运行专项测试确认 GREEN。

### Task 7: 存储预览、安全清理与新鲜度策略

**Files:**
- Create: `apps/api/src/qibao_api/operations/freshness.py`
- Modify: `apps/api/src/qibao_api/operations/read_model.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Test: `apps/api/tests/operations/test_read_model.py`
- Test: `apps/api/tests/operations/test_freshness.py`

- [x] 写失败测试：预览不删除、只清缓存与过期日志、禁止越界和核心数据、新鲜度分类边界准确。
- [x] 运行测试确认 RED。
- [x] 实现清理预览/确认接口、新鲜度注册表和可视化说明。
- [x] 运行专项测试确认 GREEN。

### Task 8: 全量发布验收

- [x] 运行 API 全量测试。
- [x] 运行 Web 全量测试和 production build。
- [x] 运行 UTF-8/乱码扫描与 `git diff --check`。
- [x] 执行 `scripts/build-portable.ps1` 并保留八个持久目录。
- [x] 执行 `scripts/run-portable-smoke.ps1 -UseReleaseData`，核验窗口、API、首页、公司研究、量化、运维和进程释放。
- [x] 更新 `docs/verification/2026-08-12-performance-maintenance-loop-v5.md` 与长期项目卡。
