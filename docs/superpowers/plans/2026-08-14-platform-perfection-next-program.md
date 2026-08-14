# 一树 A 股观测台平台完善下一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 在不伪造数据、不关闭通达信、不改变 EXE 交付边界的前提下，让一树-A股观测台的真实数据更快、更完整、更可追溯，并完成两项必要工程治理：可观测性告警、可复现发布与数据库迁移/回滚。

**Architecture:** 以 API 契约和追加式存储为可信边界，前端只消费带来源、观察时间、样本量、覆盖率和限制说明的数据。数据域通过统一质量矩阵、日级重放快照和观察篮子风险模式复用现有真实数据；发布侧通过 UTF-8 清单、迁移版本、备份恢复演练和 smoke 质量门禁形成闭环。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、SQLite/DuckDB 现有仓储、React/TypeScript、Vitest、Pytest、PowerShell、便携 PyInstaller EXE。

## Global Constraints

- Windows 便携 EXE 是唯一用户交付入口；不交付独立 HTML 或 localhost 页面。
- 所有行情、新闻、资金流、研究和量化数值必须来自真实源；缺失时只能显示 `partial`、`stale` 或 `unavailable`。
- A 股红色表示上涨/改善，绿色表示下跌/恶化；内部原始错误码只进日志，用户界面使用中文说明。
- 不关闭、不重启、不控制通达信；不连接券商、不下单、不生成纸面资金或模拟成交。
- 变更中文文件使用 UTF-8 和 `apply_patch`；每批修改后执行乱码扫描、测试和 `git diff --check`。
- 发布重建必须保留 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。

---

### Task 1: 统一来源健康口径与诊断编码

**状态：已完成**

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/source_health.py`
- Modify: `apps/api/src/qibao_api/shangshu/operations_repository.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Test: `apps/api/tests/contracts/test_source_health.py`
- Test: `apps/api/tests/shangshu/test_operations_repository.py`

**Interfaces:**
- `SourceHealthResponse` 新增 `probed_count`、`ready_count`、`degraded_count`、`unavailable_count` 和 `observed_at`，原 `source_count` 仅作为兼容字段并明确等于 `probed_count`。
- `OperationsRepository.source_health_snapshot()` 输出上述聚合字段；不会把“已配置”误称为“已就绪”。
- smoke 发布清单写入 `probe_count`、`ready_count`、`degraded_count`、`unavailable_count`，并在写入前做 UTF-8 round-trip 检查，禁止 `å`、`æ`、`ï¼` 等乱码片段。

- [ ] **Step 1: 写失败测试**：构造 ready/degraded/unavailable 三类来源，断言响应聚合计数和 `source_count == probed_count`。
- [ ] **Step 2: 运行定向 Pytest**：`pytest apps/api/tests/contracts/test_source_health.py apps/api/tests/shangshu/test_operations_repository.py -q`，确认新字段缺失导致失败。
- [ ] **Step 3: 实现契约和仓储聚合**：只基于最近窗口的实际探针记录计算计数，空窗口保持 `unavailable`。
- [ ] **Step 4: 修复 smoke 清单编码和字段命名**：使用 UTF-8 无 BOM 写入，并增加发布清单乱码扫描。
- [ ] **Step 5: 运行定向测试和 PowerShell 单元测试**：确认中文诊断详情原样保留。

### Task 2: 统一数据质量矩阵与证据水位

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/contracts/data_quality.py`
- Modify: `apps/api/src/qibao_api/contracts/evidence_ledger.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Create: `apps/api/tests/contracts/test_data_quality.py`
- Modify: `apps/web/src/shared/evidence/DataWatermarkStrip.tsx`

**Interfaces:**
- `DataQualityMatrix` 包含 `domain`、`status`、`source`、`trade_date`、`observed_at`、`valid_count`、`total_count`、`coverage_percent`、`cache_state`、`limitations`。
- `DataQualityMatrix.coverage_percent` 必须与有效/总样本一致，不能由前端猜算；`ready` 必须有观察时间和正样本。
- `/api/v1/operations/diagnostics` 暴露 `quality_matrix`，不改变现有领域 API。

- [ ] **Step 1: 写 Pydantic 失败测试**：覆盖率越界、有效样本大于总样本、ready 无时间、unavailable 无限制说明。
- [ ] **Step 2: 运行定向测试确认失败**。
- [ ] **Step 3: 实现冻结契约和诊断聚合适配器**：沿用现有来源健康、市场概览、量化和研究状态。
- [ ] **Step 4: 将水位条改为消费 API 口径**：显示来源、观察时间、有效/总样本、缓存状态和限制。
- [ ] **Step 5: 运行 API/Web 定向测试和乱码扫描**。

### Task 3: 追加式日级重放快照

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/storage/replay_snapshot_store.py`
- Create: `apps/api/src/qibao_api/contracts/replay_snapshot.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/storage/test_replay_snapshot_store.py`
- Create: `apps/api/tests/routes/test_replay_snapshots.py`

**Interfaces:**
- `ReplaySnapshotStore.append(trading_date, captured_at, inputs, source_health, strategy_version) -> ReplaySnapshot` 使用 SHA-256 内容哈希和不可更新/不可删除 SQLite 表。
- `GET /api/v1/operations/replay-snapshots?trading_date=YYYY-MM-DD` 返回按捕获时间倒序的快照元数据与可验证内容哈希。
- 快照输入只引用已有真实快照 ID/文件哈希，不复制或生成模拟行情。

- [ ] **Step 1: 写失败测试**：相同内容生成相同语义版本；更新和删除被拒绝；按交易日查询可复现。
- [ ] **Step 2: 运行定向测试确认失败**。
- [ ] **Step 3: 实现 append-only 仓储、索引和校验**。
- [ ] **Step 4: 注册依赖和只读 API**；API 对未来交易日返回中文错误。
- [ ] **Step 5: 在每日阶段完成后追加快照**，失败只记录 unavailable，不阻断已有确定性结果。
- [ ] **Step 6: 运行定向/全量 API 测试**。

### Task 4: 观察篮子风险模式

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/contracts/watchlist_risk.py`
- Create: `apps/api/src/qibao_api/a_shares/watchlist_risk.py`
- Create: `apps/api/src/qibao_api/routes/watchlist_risk.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/a_shares/test_watchlist_risk.py`
- Create: `apps/api/tests/routes/test_watchlist_risk.py`

**Interfaces:**
- `GET /api/v1/a-shares/watchlist-risk` 返回 `mode="observation_basket"`、股票名称+代码、行业/主题集中度、波动、资金流相关性、事件风险和覆盖率。
- 没有真实持仓时状态为 `unavailable` 或 `partial`，但仍可展示观察篮子风险；响应不得使用 `portfolio` 或“持仓”措辞冒充真实仓位。
- 缺少行业、资金流或事件字段时按域标记限制，不补零。

- [ ] **Step 1: 写无仓位与多标的风险计算失败测试**。
- [ ] **Step 2: 运行测试确认失败**。
- [ ] **Step 3: 使用现有目录、行情、资金流、新闻/事件仓储实现确定性计算**。
- [ ] **Step 4: 接入路由和依赖，增加名称解析失败时的中文提示**。
- [ ] **Step 5: 运行 API 测试并验证不影响现有 portfolio-risk 路由**。

### Task 5: 量化走样校准与研究版本差异

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/contracts/quant_calibration.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_calibration.py`
- Create: `apps/api/src/qibao_api/routes/quant_calibration.py`
- Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research_versions.py`
- Create: `apps/api/tests/a_shares/test_quant_calibration.py`
- Create: `apps/api/tests/a_shares/test_company_research_version_diff.py`

**Interfaces:**
- 量化校准报告必须包含样本区间、训练/验证/测试分段、交易数、胜率、盈亏比、回撤、Sharpe、手续费、滑点、因子贡献和数据完整性检查。
- 任何未来函数、幸存者偏差、缺失关键因子或样本不足都只返回 `unavailable/partial`，不生成分数。
- 公司研究版本差异输出 `strengthened`、`weakened`、`unchanged`、`new`、`resolved`，绑定前后证据 ID 和观察时间。

- [ ] **Step 1: 写校准和版本差异失败测试**。
- [ ] **Step 2: 运行定向测试确认失败**。
- [ ] **Step 3: 实现只读报告生成器，复用现有回测与公司研究版本仓储**。
- [ ] **Step 4: 暴露 API 并保留旧响应兼容**。
- [ ] **Step 5: 运行定向/全量 API 测试**。

### Task 6: 多股票研究比较与性能闭环

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/contracts/research_compare.py`
- Create: `apps/api/src/qibao_api/routes/research_compare.py`
- Modify: `apps/web/src/shared/api/*`
- Create: `apps/web/src/shared/performance/routePerformance.ts`
- Create: `apps/web/src/shared/performance/routePerformance.test.ts`
- Modify: `apps/web/src/features/company-research/*`

**Interfaces:**
- `POST /api/v1/a-shares/company-research/compare` 最多接受 5 个已验证 A 股代码，返回业务、行业、营收/利润、现金流、估值、竞争、催化、风险和证据覆盖对比。
- 请求去重键必须包含域、交易日和标的集合；缓存命中不清空上次完整结果。
- 记录首屏、API、可交互、完整更新的 P50/P95，未达到阈值只产生告警不伪造完成。

- [ ] **Step 1: 写比较契约和请求账本失败测试**。
- [ ] **Step 2: 运行定向 Web/API 测试确认失败**。
- [ ] **Step 3: 实现批量比较和共享请求去重**。
- [ ] **Step 4: 将研究页改为名称+代码标签、证据水位和可展开差异表**。
- [ ] **Step 5: 运行生产构建和性能回归**。

### Task 7: 可观测性与告警闭环（工程治理项一）

**状态：已完成**

**Files:**
- Create: `apps/api/src/qibao_api/operations/observability.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/operations/test_observability.py`
- Create: `docs/operations/observability.md`

**Interfaces:**
- 记录 source/API/cache/route 四类事件，字段包含 `event_id`、`observed_at`、`status`、`latency_ms`、`coverage_percent`、`error_code`、`trace_id`。
- 告警规则：连续失败、覆盖率低于阈值、数据超过 freshness、P95 超阈值、发布 smoke 失败；告警写本地日志/SQLite，用户看到中文摘要。
- `/api/v1/operations/observability` 提供最近窗口和活动告警，不能暴露密钥或原始供应商异常堆栈。

- [ ] **Step 1: 写事件聚合和告警阈值失败测试**。
- [ ] **Step 2: 实现内存窗口 + SQLite append-only 持久化**。
- [ ] **Step 3: 接入来源健康、性能账本、刷新任务和发布 smoke**。
- [ ] **Step 4: 增加数据设置中的折叠诊断入口和中文错误摘要**。
- [ ] **Step 5: 运行 API/Web 测试并确认告警不阻断可用缓存**。

### Task 8: 可复现发布与迁移/回滚治理（工程治理项二）

**状态：已完成**

**Files:**
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Create: `scripts/verify-migrations.ps1`
- Create: `scripts/rollback-portable-data.ps1`
- Create: `docs/operations/release-and-rollback.md`
- Test: `apps/api/tests/desktop/test_packaging.py`

**Interfaces:**
- 发布清单必须包含源码 commit、工作树状态、依赖锁哈希、迁移版本、数据库文件哈希、八个持久目录、EXE 哈希、smoke 时间和质量矩阵。
- 构建前备份持久目录；迁移失败自动恢复到上一个备份；回滚脚本必须先校验备份哈希再替换。
- 发布质量脚本拒绝乱码、缺字段、脏源码、哈希不匹配、持久目录缺失和迁移版本倒退。

- [x] **Step 1: 写发布清单和迁移回滚失败测试**。
- [x] **Step 2: 实现备份、迁移前置检查、哈希校验和回滚命令**。
- [x] **Step 3: 将 smoke 输出接入质量清单并保留真实数据目录**。
- [x] **Step 4: 运行迁移演练、发布脚本测试和真实 EXE smoke**。

### Final Verification

- [x] API 全量 Pytest、Web 全量 Vitest、Ruff、TypeScript/Vite 构建通过。
- [x] 变更中文文件 UTF-8/mojibake 扫描通过，`git diff --check` 通过。
- [x] `scripts/build-portable.ps1` 成功并保留八个持久目录。
- [x] `scripts/run-portable-smoke.ps1 -UseReleaseData` 成功，窗口、API、首页和关键接口均可用。
- [x] `scripts/verify-release-quality.ps1` 成功，发布清单中的真实状态、哈希、迁移版本和编码均通过。
- [x] smoke 前后通达信均未运行；本轮未启动、关闭或控制通达信，smoke 结束无本程序残留进程。
- [x] 更新 `D:\Users\90090\Documents\知识库\02-项目记忆\金融财经.md`，并从知识库根目录运行 Vault 校验。
