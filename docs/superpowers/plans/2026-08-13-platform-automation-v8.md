# A 股观测台智能自动化 v8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有真实数据与证据闭环之上，增加通达信目录自动增量导入、后台任务可观测性和便携 EXE 运维治理，减少手动操作并保持数据真实性。

**Architecture:** 复用现有 `TdxLocalImportService`、`TdxImportRepository`、共享线程执行器和运维状态接口。新增一个只读目录指纹监测器：仅统计已配置目录内 `.day`/`.zip` 文件的路径、大小和修改时间；指纹变化后才提交现有增量导入任务。监测器状态在当前进程内保留，并通过 `/api/v1/operations/status` 返回；重启后重新建立基线，不把旧状态冒充为实时状态。

**Tech Stack:** Python 3.12、FastAPI、SQLite、React 19、TypeScript、Vitest、PyInstaller。

## Global Constraints

- 只交付 Windows 便携 EXE，不生成浏览器或 HTML 交付物。
- 通达信只读：不关闭、重启、控制客户端，不连接交易账户，不下单。
- 数据缺失显示不可用或待补齐，不用零值、随机值或无关数据填充。
- A 股红色表示上涨/改善，绿色表示下跌/恶化；结构状态使用中性色。
- 自动监测只在目录指纹变化后导入，避免重复扫描和重复写入。
- 用户可见源代码修改后运行聚焦测试、全量相关测试、生产构建、UTF-8/乱码扫描、`git diff --check`，并重建便携 EXE 与 smoke。
- 重建便携版必须保留 `config/data/news/cache/logs/models/exports/backups`。

---

### Task 1: 通达信目录指纹与自动导入监测器

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_auto_import.py`
- Create: `apps/api/tests/gongbu/test_tdx_auto_import.py`
- Modify: `apps/api/src/qibao_api/shangshu/operations_repository.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`

**Produces:** `TdxAutoImportMonitor`，支持启动/停止、目录指纹比较、变更后提交已有导入服务、跳过原因、最近触发时间和当前状态；运维状态返回 `tdx_auto_import`。

- [x] 测试空目录、不存在目录、未变化目录不会提交任务。
- [x] 测试 `.day`/`.zip` 新增、大小或修改时间变化会提交一次任务。
- [x] 测试已有手动/自动任务运行时不重复提交，并记录 `active_job` 跳过原因。
- [x] 测试监测器异常不终止 API，状态记录错误原因。
- [x] 实现纯指纹函数和线程安全状态机。
- [x] 在应用生命周期中以低频后台线程启动，关闭时停止并等待线程退出。
- [x] 在运维状态接口暴露状态，不向前端伪造完成进度。

### Task 2: 后台任务账本与自动化提示

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/task_progress.py`
- Modify: `apps/api/src/qibao_api/contracts/tdx_import.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_import_repository.py`
- Modify: `apps/web/src/features/operations/types.ts`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/features/operations/operations.css`
- Create: `apps/web/src/features/operations/TdxAutoImportStatus.test.tsx`

**Produces:** 运维页显示自动监测开关、最近扫描、最近触发、跳过原因、失败原因和当前导入任务；手动导入与自动导入使用同一进度口径。

- [x] 先写状态展示测试，覆盖监测中、未配置、等待变化、运行中和错误状态。
- [x] 增加真实状态契约和 API 读取。
- [x] 在运维页增加紧凑状态条，默认不阻塞其他数据。
- [x] 验证无数据时不显示“实时已连接”。

### Task 3: EXE 诊断、备份和恢复治理

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/backup_service.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/run-portable-smoke.ps1`
- Create: `apps/api/tests/gongbu/test_backup_service_diagnostics.py`

**Produces:** 发布版本、持久目录保护、备份哈希、恢复演练和自动监测状态可导出为诊断摘要。

- [x] 测试诊断摘要不包含密钥、令牌或密码。
- [x] 增加一键导出诊断摘要和一键备份后的校验入口。
- [x] 构建脚本继续恢复八个持久目录。
- [x] smoke 验证 EXE 启动、自动监测状态、信息总览和量化页面不被阻塞。

### Task 4: 全站验收与交付

**Files:**
- Modify: `docs/verification/2026-08-13-platform-automation-v8.md`

- [x] API 聚焦和全量测试。
- [x] Web 聚焦测试与生产构建；Vitest worker 未自动退出的既有问题已记录。
- [x] UTF-8 严格解码、乱码扫描、`git diff --check`。
- [x] 生产构建、便携 EXE 重建和真实 smoke。
- [x] 核验通达信进程与 `127.0.0.1:17709` 前后保持不变。
