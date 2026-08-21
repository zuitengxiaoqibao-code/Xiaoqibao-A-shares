# 公司研究与量化分析快速加载实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让公司研究和量化分析优先显示当天真实快照，消除候选扫描对正式 DuckDB 的锁竞争，并让事件 K 线、高频采样、信号、回测和风险闸门独立、快速、清晰地展示。

**Architecture:** 全市场候选扫描改读主进程生成的独立只读 DuckDB 快照，正式数据库不再交给长生命周期子进程。前端资源统一采用按交易日、股票和数据域隔离的 last-good 缓存，按首屏优先级延迟启动重任务；风险闸门按股票卡片分组。所有降级继续显式保留 `partial/stale/unavailable` 和真实原因。

**Tech Stack:** Python 3.12、FastAPI、DuckDB、Pydantic、pytest、React 18、TypeScript、Vitest、Testing Library、Vite、Windows PowerShell、PyInstaller 便携 EXE。

## Global Constraints

- Windows 便携 EXE 是唯一用户交付入口；不交付 HTML 或 localhost。
- 不关闭、重启或控制通达信，不关闭用户正在运行的正式 EXE，不控制鼠标或桌面。
- 不生成模拟行情、模拟 TICK、虚构候选或伪造 `ready` 状态。
- 中文源码只用 `apply_patch` 修改；修改后必须执行 UTF-8/乱码扫描。
- 重建时保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
- 每个行为变更先写失败测试并确认按预期失败，再写最小实现。

---

### Task 1: 修复量化校准账本读取上限

**Files:**
- Modify: `apps/api/tests/a_shares/test_quant_calibration.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_calibration.py`

**Interfaces:**
- Consumes: `QuantShadowLedger.recent(*, limit: int)`，合法范围 `1..500`。
- Produces: `build_calibration_report(... )` 最多读取 500 条真实记录，样本不足继续返回 `partial/unavailable`。

- [ ] **Step 1: 写失败测试**

  将测试账本断言改为 `limit == 500`，并增加 500 条上限内记录的分割与样本计数断言。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/a_shares/test_quant_calibration.py -q`
  Expected: FAIL，实际收到 `5000`。

- [ ] **Step 3: 写最小实现**

  ```python
  records = sorted(ledger.recent(limit=500), key=lambda item: (item.as_of, item.symbol))
  ```

- [ ] **Step 4: 运行测试确认 GREEN**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/a_shares/test_quant_calibration.py -q`
  Expected: PASS。

### Task 2: 用独立只读快照隔离候选扫描和正式 DuckDB

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_scan_snapshot.py`
- Create: `apps/api/tests/a_shares/test_quant_scan_snapshot.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/tests/a_shares/test_quant_strategy.py`
- Modify: `apps/api/tests/a_shares/test_quant_candidate_process.py`

**Interfaces:**
- Produces: `QuantScanSnapshotManager.prepare(source_database: Path, source_parquet: Path, *, as_of: date) -> QuantScanInput`。
- `QuantScanInput` 包含 `database_path`、`parquet_path`、`source_size`、`source_mtime_ns`、`as_of`、`created_at`。
- 候选子进程只接收 `QuantScanInput.database_path`，绝不直接接收正式 `market.duckdb`。

- [ ] **Step 1: 写失败测试**

  覆盖同一水位复用快照、源库水位变化后重建、快照失败不替换 last-good，以及候选扫描运行时正式 `BarRepository` 仍可连接和读取。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/a_shares/test_quant_scan_snapshot.py apps/api/tests/a_shares/test_quant_candidate_process.py apps/api/tests/a_shares/test_quant_strategy.py -q`
  Expected: FAIL，管理器尚不存在或子进程路径仍指向正式库。

- [ ] **Step 3: 写最小实现**

  使用 DuckDB `CHECKPOINT` 后的文件级副本生成到 `cache/quant-scan/<watermark>/market.duckdb`；先写临时文件，再原子替换。快照元数据包含正式库大小、mtime 和交易日，复用条件全部匹配才返回旧快照。正式 parquet 目录只读；若扫描依赖 parquet 文件，则复制所需清单到相同快照目录。

- [ ] **Step 4: 接入候选服务**

  删除 ASCII junction 直连正式库的 `_prepare_process_paths()` 路径策略；在提交 `ProcessPoolExecutor` 前调用快照管理器，并记录源水位、快照路径和耗时。快照准备失败时保留现有同日候选快照和明确失败状态。

- [ ] **Step 5: 运行测试确认 GREEN**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/a_shares/test_quant_scan_snapshot.py apps/api/tests/a_shares/test_quant_candidate_process.py apps/api/tests/a_shares/test_quant_strategy.py -q`
  Expected: PASS。

### Task 3: 允许结构有效的公司研究 `partial` 快照作为 last-good

**Files:**
- Modify: `apps/web/src/shared/dailySnapshotCache.ts`
- Modify: `apps/web/src/shared/dailySnapshotCache.test.ts`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.test.tsx`

**Interfaces:**
- Produces: `SnapshotReadOptions<T> = { allowPartial?: boolean; validate?: (value: T) => boolean }`。
- `readDailySnapshot`、`readDailySnapshotMetadata`、`listDailySnapshots` 接受相同读取选项；默认行为继续拒绝 partial，避免影响其他页面。
- 公司研究仅在代码匹配、结构版本可识别且核心研究区块存在时设置 `allowPartial: true`。

- [ ] **Step 1: 写失败测试**

  覆盖默认读取仍拒绝 partial、公司研究显式允许有效 partial、无核心区块的 partial 被删除、刷新失败后继续显示缓存内容并显示中文失败原因。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `pnpm --filter @qibao/web test -- dailySnapshotCache.test.ts CompanyResearchView.test.tsx`
  Expected: FAIL，现有读取逻辑无条件删除 partial。

- [ ] **Step 3: 写最小实现**

  将“是否允许 partial”与“值结构是否有效”集中在 `readEnvelope`，三个公共读取入口复用；公司研究提供本地类型守卫。complete 快照仍优先于 partial，partial 刷新不得覆盖 complete。

- [ ] **Step 4: 运行测试确认 GREEN**

  Run: `pnpm --filter @qibao/web test -- dailySnapshotCache.test.ts CompanyResearchView.test.tsx`
  Expected: PASS。

### Task 4: 为量化模块增加按域 last-good 缓存和分级启动

**Files:**
- Modify: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.ts`
- Modify: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.test.tsx`

**Interfaces:**
- `useQuantLiveResource` 新增 `cache?: { key: string; day: string; validate: (value: unknown) => value is T }` 与 `initialDelayMs?: number`。
- 缓存键必须包含数据域、交易日和股票；写入带 schema 版本、observedAt 和 cachedAt。
- 第一优先级立即启动候选、事件和选中标的采样；策略/信号延迟一个空闲周期；回测、walk-forward、Kronos 和研究智能在首屏稳定后启动；影子、校准和日志最后启动。

- [ ] **Step 1: 写失败测试**

  覆盖挂载时立即恢复缓存、失败保留缓存、换股不串数据、延迟资源不会在首个 render 同时调用、事件/TICK/信号/回测任一失败不清空其他区域。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `pnpm --filter @qibao/web test -- useQuantLiveRefresh.test.tsx QuantAnalysisDashboard.test.tsx QuantResearchIntelligencePanel.test.tsx`
  Expected: FAIL，当前无资源缓存和启动优先级。

- [ ] **Step 3: 写最小实现**

  复用交易日工具和已有 request ledger；恢复缓存只设置 `data` 与 `delayed/live` 状态，后台刷新失败只更新 `error`。使用可取消的 `setTimeout`/`requestIdleCallback` 启动低优先级请求，页面隐藏时不启动。

- [ ] **Step 4: 将回测和 walk-forward 改为独立 last-good 资源**

  股票切换时仅在目标股票无缓存才显示局部骨架；旧股票响应不得覆盖新股票；Kronos、研究智能、影子和校准采用相同隔离键。

- [ ] **Step 5: 运行测试确认 GREEN**

  Run: `pnpm --filter @qibao/web test -- useQuantLiveRefresh.test.tsx QuantAnalysisDashboard.test.tsx QuantResearchIntelligencePanel.test.tsx`
  Expected: PASS。

### Task 5: 让自定义分析标的进入真实盘中高频采样范围

**Files:**
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Modify: `apps/api/tests/routes/test_research.py`
- Modify: `apps/api/tests/shangshu/test_intraday_monitor.py`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`

**Interfaces:**
- Produces: 选中标的注册接口或等价服务调用，注册记录包含 symbol、来源页面和过期时间。
- `focus_symbols(now)` 合并策略候选、自选范围和未过期的用户选中标的；同一股票去重。
- 本地归档同一股票同一观测秒只保留一条真实快照。

- [ ] **Step 1: 写失败测试**

  覆盖自定义股票注册后进入采样、TTL 到期后退出、同秒去重、非交易时段不伪造采样、行情源失败保留明确原因。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_research.py apps/api/tests/shangshu/test_intraday_monitor.py -q`
  Expected: FAIL，自定义标的尚未进入 `focus_symbols`。

- [ ] **Step 3: 写最小实现**

  复用现有 `PollStateRepository`，注册只改变观测范围，不触发交易能力。前端选股后注册一次，后续每秒仅读取本地归档；用户看见“高频采样”而非无法证明的“交易所逐笔”。

- [ ] **Step 4: 运行后端和前端聚焦测试确认 GREEN**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_research.py apps/api/tests/shangshu/test_intraday_monitor.py -q`
  Run: `pnpm --filter @qibao/web test -- QuantAnalysisDashboard.test.tsx`
  Expected: PASS。

### Task 6: 风险闸门按股票卡片和状态标签展示

**Files:**
- Modify: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- 每个 `QuantRiskGateSummary` 渲染一张卡片。
- 卡头展示股票名称或代码、综合状态；标签统计 pass/warn/block/unavailable；阻断与警告原因优先；审计明细用原生 `details` 展开。

- [ ] **Step 1: 写失败测试**

  覆盖两只股票生成两张卡、状态数量正确、阻断原因优先、指标/阈值/来源位于展开区、长原因保留完整文本。

- [ ] **Step 2: 运行测试确认 RED**

  Run: `pnpm --filter @qibao/web test -- QuantResearchIntelligencePanel.test.tsx`
  Expected: FAIL，当前按检查项平铺。

- [ ] **Step 3: 写最小实现和样式**

  使用 `repeat(auto-fit, minmax(280px, 1fr))`；风险状态使用青色、琥珀色、洋红红和灰蓝，不借用 K 线涨跌色；正文不低于 13px。

- [ ] **Step 4: 运行测试确认 GREEN**

  Run: `pnpm --filter @qibao/web test -- QuantResearchIntelligencePanel.test.tsx`
  Expected: PASS。

### Task 7: 全量验证、乱码扫描和便携 EXE 验收

**Files:**
- Create: `docs/verification/2026-08-21-fast-research-loading.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`（仅在全部验证完成后，按 Vault 写入协议更新）

**Interfaces:**
- Produces: 可追溯测试结果、启动耗时、各量化子模块状态、发布清单和 EXE SHA-256。

- [ ] **Step 1: 运行聚焦回归**

  运行 Tasks 1–6 的所有聚焦测试，确认零失败。

- [ ] **Step 2: 运行全量质量检查**

  Run: `.venv\Scripts\python.exe -m pytest apps/api/tests -q`
  Run: `.venv\Scripts\python.exe -m ruff check apps/api/src apps/api/tests`
  Run: `pnpm --filter @qibao/web test -- --run`
  Run: `pnpm --filter @qibao/web build`
  Run: 项目现有 UTF-8/乱码扫描脚本，以及 `git diff --check`。
  Expected: 全部 exit 0；已知环境跳过项单独记录。

- [ ] **Step 3: 重建便携 EXE**

  Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`
  Expected: 保留八个持久目录；正式 EXE 被占用时生成 staged 发布，不关闭用户进程。

- [ ] **Step 4: 对新 EXE 执行真实 smoke**

  Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1 -UseReleaseData`
  Expected: 实际 EXE 窗口可见、API 就绪；公司研究、事件时间线、高频采样、策略、回测、walk-forward 和研究智能接口均返回可解释状态；不要求缺失证据伪装为 ready。

- [ ] **Step 5: 记录验证证据并更新项目记忆**

  在验证文档记录命令、通过数量、耗时、发布路径、SHA-256、持久目录和未解决的真实数据边界。读取 `99-系统` 协议后，只把已确认事实写入项目卡片，不写入密钥。

