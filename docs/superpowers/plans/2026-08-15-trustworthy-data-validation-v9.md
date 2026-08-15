# 可信数据自动维护与样本外决策验证 v9 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 在不伪造数据、不关闭或控制通达信的前提下，让已有真实数据更快、更完整、更容易追溯，并把量化与公司研究提升到点时、样本外和证据可回溯的标准。

**Architecture:** 所有新能力复用现有 `EvidenceLedger`、`DataQualityMatrix`、`ReplaySnapshotStore`、`HistoryQuality`、`Observability` 和 portable manifest。新增的血缘记录、修复任务、walk-forward 报告、事件影响报告和预计算快照都采用追加式本地 SQLite/Parquet 存储，并返回来源、观察时间、交易日、覆盖率、限制和状态。前端只消费这些证据，不在浏览器计算或填充缺失值。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、SQLite/DuckDB/Parquet、React/TypeScript、Vitest、Pytest、PowerShell、PyInstaller portable EXE。

## Global Constraints

- Windows portable EXE 是唯一用户交付入口；不交付独立 HTML 或 localhost 页面。
- 所有数值必须来自真实本地通达信、腾讯或已登记来源；缺失时只能返回 `partial/stale/unavailable/error`。
- 所有点时计算必须使用公告/财报/行情的有效时间，不允许未来函数和幸存者偏差。
- A 股红色表示上涨/改善，绿色表示下跌/恶化；内部异常码不得直接展示给用户。
- 不启动、关闭、重启或控制通达信；不连接券商、不下单、不生成模拟成交。
- 发布重建保留 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。
- 每个新增 API 必须有契约测试、真实数据边界测试和前端状态测试。

## Task 1: 数据契约与血缘治理（工程治理项一）

**Files:**
- Create: `apps/api/src/qibao_api/contracts/data_lineage.py`
- Create: `apps/api/src/qibao_api/operations/data_lineage.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/operations/test_data_lineage.py`
- Create: `apps/api/tests/routes/test_data_lineage.py`

**Interface:** `DataLineageRecord` 记录 `domain`, `field`, `symbol`, `trade_date`, `observed_at`, `source`, `source_version`, `content_hash`, `status`, `coverage_percent`, `limitations`。`DataLineageRepository.append()` 只追加，`GET /api/v1/operations/data-lineage` 按域、标的和日期查询，并返回可验证哈希。

## Task 2: 点时数据和来源裁决

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/point_in_time.py`
- Create: `apps/api/src/qibao_api/a_shares/source_arbitration.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Create: `apps/api/tests/a_shares/test_point_in_time.py`
- Create: `apps/api/tests/a_shares/test_source_arbitration.py`

**Interface:** `as_of(value, cutoff)` 只接受 `observed_at <= cutoff` 的证据；`select_preferred(records)` 按来源优先级、观察时间、字段覆盖和一致性选择记录，冲突时返回 `conflict` 与全部候选证据，不返回代理值。

## Task 3: 交易日缺口和自动增量修复

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/data_gap_repair.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Create: `apps/api/tests/a_shares/test_data_gap_repair.py`
- Create: `apps/api/tests/routes/test_data_gap_repair.py`

**Interface:** `inspect_gaps(trading_dates, symbols, bars)` 输出缺失交易日、缺失股票、字段缺口和真实来源建议；`POST /api/v1/operations/data-gaps/repair` 只接受明确缺口批次，返回追加式任务进度、来源、写入行数、失败原因和哈希。

## Task 4: Walk-forward 样本外量化验证

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/walk_forward.py`
- Create: `apps/api/src/qibao_api/contracts/walk_forward.py`
- Create: `apps/api/src/qibao_api/routes/walk_forward.py`
- Create: `apps/api/tests/a_shares/test_walk_forward.py`
- Create: `apps/api/tests/routes/test_walk_forward.py`
- Modify: `apps/web/src/features/quant-analysis/*`

**Interface:** `run_walk_forward(dataset, windows, costs)` 返回训练/验证/测试区间、闭合交易数、胜率、盈亏比、最大回撤、Sharpe、因子衰减和完整性状态；少于 5 笔闭合交易或关键字段缺失时不返回策略分数，状态为 `unavailable/partial`。

## Task 5: 公司研究证据图谱与事件影响

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/evidence_graph.py`
- Create: `apps/api/src/qibao_api/a_shares/event_impact.py`
- Create: `apps/api/src/qibao_api/contracts/event_impact.py`
- Create: `apps/api/src/qibao_api/routes/event_impact.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/web/src/features/company-research/*`
- Modify: `apps/web/src/features/news-intelligence/*`
- Create: `apps/api/tests/a_shares/test_evidence_graph.py`
- Create: `apps/api/tests/a_shares/test_event_impact.py`

**Interface:** 研究事实、推导、判断和不可用结论形成有向证据图；新闻事件按首次发布时间、事件类型、关联股票/板块和 1/3/5/20 日真实收益生成影响报告。重复新闻、低置信关联和缺行情窗口必须显式标注。

## Task 6: 收盘后预计算与性能闭环

**Files:**
- Create: `apps/api/src/qibao_api/operations/precompute_snapshots.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/web/src/shared/performance/*`
- Create: `apps/api/tests/operations/test_precompute_snapshots.py`
- Create: `apps/web/src/shared/performance/precomputeStatus.test.ts`

**Interface:** 以交易日和数据版本为键生成总览、量化、研究摘要快照；请求优先读取完整快照，后台增量刷新；记录 P50/P95、命中率和首屏/可交互时间，失败保留上一份完整快照。

## Task 7: 全站钻取和工作区恢复

**Files:**
- Modify: `apps/web/src/shared/instruments/*`
- Create: `apps/web/src/shared/workspace/workspaceState.ts`
- Modify: `apps/web/src/features/market-overview/*`
- Modify: `apps/web/src/features/quant-analysis/*`
- Modify: `apps/web/src/features/company-research/*`
- Create: `apps/web/src/shared/workspace/workspaceState.test.ts`

**Interface:** 所有统计数字、图表和排名均携带可钻取标的集合；点击后进入统一股票上下文。菜单、股票、日期、筛选条件和滚动位置写入版本化本地状态，重启后恢复；状态失效时安全降级。

## Task 8: 发布安全与灾备恢复（工程治理项二）

**Files:**
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Create: `scripts/sign-release-manifest.ps1`
- Create: `scripts/verify-restore-drill.ps1`
- Modify: `docs/operations/release-and-rollback.md`
- Create: `scripts/sign-release.tests.ps1`
- Create: `scripts/restore-drill.tests.ps1`

**Interface:** 发布清单增加签名摘要、工具链版本、备份基线和恢复演练结果；恢复演练在临时目录校验数据库哈希、迁移版本和关键 API，不修改正式发布目录；签名/恢复失败阻断交付。

## Final Verification

- API 全量 Pytest、Web 全量 Vitest、Ruff、TypeScript/Vite 构建和 PowerShell/Pester 测试通过。
- UTF-8/乱码扫描和 `git diff --check` 通过。
- 数据缺口、点时规则、冲突裁决、walk-forward、事件影响和预计算均有真实边界测试。
- 便携 EXE 重建成功并保留八个持久目录。
- 真实 EXE smoke、迁移核验、恢复演练和发布质量门禁通过。
- 信息总览保持真实 `ready/partial`；量化、公司研究和通达信专业字段不满足证据门槛时继续诚实降级。
- 更新 `D:\Users\90090\Documents\知识库\02-项目记忆\金融财经.md` 并通过 Vault 校验。
