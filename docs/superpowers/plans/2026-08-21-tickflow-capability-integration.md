# TickFlow 能力原生整合实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有一树-A股观测台真实性和 EXE 交付约束的前提下，原生增加可扩展策略、回测、多格式数据导入、多源裁决、监控中心、Edge TTS、飞书告警和自动盘后复盘。

**Architecture:** 以现有 `contracts`、`a_shares`、`gongbu`、`shangshu` 和实时事件总线为边界，新增可序列化契约与版本仓储。所有重计算使用后台任务和 last-good 快照；所有结果带来源、时间、水位和质量状态。前端只消费 API 契约，不自行计算或填充缺失数据。

**Tech Stack:** Python 3.11、FastAPI、Pydantic v2、DuckDB、Polars、PyArrow、React 18、TypeScript、Edge TTS、现有 APScheduler、SSE/事件总线、Windows PyInstaller EXE。

## Global Constraints

- EXE 是唯一用户交付入口，不交付 HTML 或 localhost 页面。
- 新功能必须缓存优先、后台执行，读取端点不得同步启动全市场重算。
- 所有数据结果必须保留 `source_id`、`observed_at`、`as_of`、`ingested_at`、`content_hash` 和质量状态。
- 不使用模拟行情、随机曲线或未验证 AI 结果填充真实数据。
- A 股涨跌颜色遵循红涨绿跌；所有英文错误提示在用户界面转换为中文。
- 不关闭、重启或控制用户通达信；自动烟测结束立即释放测试进程。
- 手工编辑中文文件使用 `apply_patch`；触碰中文 UI 后执行 UTF-8/乱码扫描。
- 每个任务遵守 TDD：先写失败测试，确认失败，再写最小实现，再运行聚焦测试。
- 用户向源码变更后运行 `scripts/build-portable.ps1`，交付前运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`。

---

### Task 1: P0 统一数据、策略、任务和结果契约

**Files:**
- Create: `apps/api/src/qibao_api/contracts/data_source.py`
- Create: `apps/api/src/qibao_api/contracts/strategy_plugin.py`
- Create: `apps/api/src/qibao_api/contracts/research_tasks.py`
- Create: `apps/api/src/qibao_api/a_shares/data_version.py`
- Modify: `apps/api/src/qibao_api/contracts/__init__.py`
- Test: `apps/api/tests/contracts/test_data_source_contract.py`
- Test: `apps/api/tests/contracts/test_strategy_plugin_contract.py`
- Test: `apps/api/tests/a_shares/test_data_version.py`

**Interfaces:**
- `DataSourceHealth(source_id, status, observed_at, coverage, latency_ms, reason)`。
- `NormalizedBatch(source_id, as_of, observed_at, records, content_hash, quality_status)`。
- `DataSourceAdapter` protocol with `discover()`, `fetch(request)`, `normalize(batch)`, `health()`。
- `StrategyPluginDefinition(id, version, source, fields, parameters, entry, exit, risk_gates, content_hash)`。
- `ResearchTaskSnapshot(task_id, task_type, state, stage, progress, processed, total, error_code, error_message)`。
- `DataVersionStore.publish(domain, as_of, source_ids, content_hash, quality_status)` and `latest(domain, as_of)`。

- [ ] **Step 1: Write failing contract tests**

```python
def test_normalized_batch_rejects_missing_provenance() -> None:
    with pytest.raises(ValidationError):
        NormalizedBatch(source_id="tdx", as_of=date(2026, 8, 21), records=[])

def test_strategy_definition_rejects_unapproved_field() -> None:
    with pytest.raises(ValidationError, match="字段未在白名单"):
        StrategyPluginDefinition(id="demo", version="1", source="custom", fields=("os",))
```

- [ ] **Step 2: Run focused tests and confirm the expected validation failures**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/contracts/test_data_source_contract.py apps/api/tests/contracts/test_strategy_plugin_contract.py -q`

Expected: FAIL because the new models do not exist.

- [ ] **Step 3: Implement Pydantic models and the append-only data version store**

Implement strict models with `extra="forbid"`, timezone-aware datetimes, enum quality states, SHA-256 format validation, and SQLite/DuckDB-independent JSON metadata storage under `data/versions/{domain}/{as_of}.json`. `publish` writes a temporary file, flushes it, then atomically replaces the target; `latest` returns only versions whose `as_of` is not later than the requested point-in-time date.

- [ ] **Step 4: Run focused tests and the contract import check**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/contracts/test_data_source_contract.py apps/api/tests/contracts/test_strategy_plugin_contract.py apps/api/tests/a_shares/test_data_version.py -q`

Expected: all focused tests pass and no test imports a module from the external repository.

- [ ] **Step 5: Commit**

```powershell
git add apps/api/src/qibao_api/contracts apps/api/src/qibao_api/a_shares/data_version.py apps/api/tests/contracts apps/api/tests/a_shares/test_data_version.py
git commit -m "feat: add versioned data and strategy contracts"
```

### Task 2: P0 多源适配器注册与数据导入中心

**Files:**
- Create: `apps/api/src/qibao_api/data_sources/registry.py`
- Create: `apps/api/src/qibao_api/data_sources/file_adapter.py`
- Create: `apps/api/src/qibao_api/data_sources/merge_policy.py`
- Create: `apps/api/src/qibao_api/routes/data_import.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Test: `apps/api/tests/data_sources/test_file_adapter.py`
- Test: `apps/api/tests/data_sources/test_merge_policy.py`
- Test: `apps/api/tests/routes/test_data_import.py`
- Test: `apps/web/src/features/data-settings/DataImportPanel.test.tsx`

**Interfaces:**
- `DataSourceRegistry.register(adapter)`, `discover(source_id)`, `health_all()`。
- `FileImportService.inspect(path) -> ImportPreview`。
- `FileImportService.ingest(path, mapping, task_id) -> NormalizedBatch`。
- `MergePolicy.resolve(records, as_of) -> ResolvedRecordSet`。
- API: `POST /api/data-import/inspect`、`POST /api/data-import/ingest`、`GET /api/data-import/tasks/{task_id}`、`GET /api/data-sources/health`。

- [ ] **Step 1: Write failing tests for format detection, isolation and conflict resolution**

Cover UTF-8/GBK CSV, TSV, JSON list, JSONL, XLSX, Parquet, SQLite, DuckDB and ZIP containing one supported file. Add assertions that malformed rows enter quarantine with a Chinese reason, duplicate rows do not overwrite originals, and two sources resolve according to priority/newest observation while preserving both source records.

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/data_sources apps/api/tests/routes/test_data_import.py -q`

Expected: FAIL because the registry, adapter and routes are absent.

- [ ] **Step 3: Implement the registry and file adapter**

Use Polars/PyArrow for tabular files, `zipfile` for ZIP inspection, and DuckDB read-only queries for SQLite/DuckDB. Enforce a 250 MB compressed-file limit, a 2 GB extracted-size limit, path traversal protection, explicit schema mapping, stock-code normalization, timezone-aware date parsing and numeric-unit declaration. Write raw upload metadata and quarantined rows under `data/imports/{task_id}/`; publish only validated Parquet partitions through `DataVersionStore`.

- [ ] **Step 4: Implement source merge policy and progress API**

Progress stages are `inspect`, `decode`, `normalize`, `validate`, `merge`, `publish`, `completed` or `failed`. Every stage updates `ResearchTaskSnapshot`; failure includes `error_code` and a Chinese `error_message`. The merge policy never substitutes zero for missing values.

- [ ] **Step 5: Add compact EXE-facing import and source-health UI**

Add an expandable import panel to 数据设置/本地运维. Show file type, detected columns, row counts, quarantined count, source health, real progress and retry action. Keep all existing sections at the same menu level and preserve default fold behavior.

- [ ] **Step 6: Run focused API/Web tests and commit**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/data_sources apps/api/tests/routes/test_data_import.py -q`; `pnpm --dir apps/web test -- --run apps/web/src/features/data-settings/DataImportPanel.test.tsx`

Expected: all focused tests pass with no fabricated ready state.

```powershell
git add apps/api/src/qibao_api/data_sources apps/api/src/qibao_api/routes/data_import.py apps/api/tests/data_sources apps/api/tests/routes/test_data_import.py apps/web/src/features/data-settings apps/web/src/features/operations/OperationsView.tsx
git commit -m "feat: add multi-format data import and source registry"
```

### Task 3: P1 受控策略注册、复合策略和 AI 草稿门禁

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/strategy_registry.py`
- Create: `apps/api/src/qibao_api/a_shares/strategy_dsl.py`
- Create: `apps/api/src/qibao_api/a_shares/strategy_draft_gate.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Test: `apps/api/tests/a_shares/test_strategy_registry.py`
- Test: `apps/api/tests/a_shares/test_strategy_dsl.py`
- Test: `apps/api/tests/a_shares/test_strategy_draft_gate.py`
- Test: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.test.tsx`

**Interfaces:**
- `StrategyRegistry.register(definition)`, `enable(strategy_id, version)`, `disable(strategy_id)`。
- `StrategyDSL.compile(expression, fields) -> CompiledSignal`，只允许白名单字段、比较、算术、窗口函数和布尔组合。
- `StrategyDraftGate.review(draft, data_version) -> GateResult`，返回 `accepted/rejected/partial` 和每项证据。
- `POST /api/v1/a-shares/strategies/drafts/validate` 不执行策略代码，只返回门禁报告。

- [ ] **Step 1: Write failing tests for DSL restrictions and AI gating**

Test that `close > ma20` compiles, `os.system(...)` and unknown fields reject, composite strategies cannot nest more than eight children, and a draft with insufficient samples cannot become enabled or expose a probability.

- [ ] **Step 2: Run tests and confirm red**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_strategy_registry.py apps/api/tests/a_shares/test_strategy_dsl.py apps/api/tests/a_shares/test_strategy_draft_gate.py -q`

Expected: FAIL because the registry, DSL and gate are absent.

- [ ] **Step 3: Implement the registry and DSL**

Store immutable strategy versions in `data/user_data/strategy_registry/`. Compile expressions to Polars expressions; do not import or execute arbitrary Python from a draft. Composite strategies reference child IDs and weights only.

- [ ] **Step 4: Implement the draft gate and preserve existing quant API**

Run current quant candidate scoring after deterministic checks. A gate failure returns reasons such as `字段未在白名单`, `点时数据不足`, `样本交易不足` or `风险闸门未通过`; it never clears the last-good candidate snapshot.

- [ ] **Step 5: Add UI controls**

In the existing 短线风格与策略 workbench, add strategy source, version, gate state, evidence coverage, enable/disable and “生成草稿” actions. Keep AI text as an explanation layer and show deterministic score/risk values separately.

- [ ] **Step 6: Run focused tests and commit**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_strategy_registry.py apps/api/tests/a_shares/test_strategy_dsl.py apps/api/tests/a_shares/test_strategy_draft_gate.py apps/api/tests/a_shares/test_quant_strategy.py -q`; `pnpm --dir apps/web test -- --run apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.test.tsx`

```powershell
git add apps/api/src/qibao_api/a_shares/strategy_registry.py apps/api/src/qibao_api/a_shares/strategy_dsl.py apps/api/src/qibao_api/a_shares/strategy_draft_gate.py apps/api/src/qibao_api/a_shares/quant_strategy.py apps/api/src/qibao_api/routes/quant_strategy.py apps/api/tests/a_shares apps/web/src/features/quant-analysis
git commit -m "feat: add governed strategy registry and AI draft gates"
```

### Task 4: P1 A 股矩阵回测、组合回测与稳健性报告

**Files:**
- Create: `apps/api/src/qibao_api/zhongshu/backtest_matrix.py`
- Create: `apps/api/src/qibao_api/zhongshu/backtest_portfolio.py`
- Modify: `apps/api/src/qibao_api/zhongshu/backtest.py`
- Modify: `apps/api/src/qibao_api/contracts/backtest.py`
- Modify: `apps/api/src/qibao_api/routes/backtest.py`
- Modify: `apps/web/src/features/backtest/BacktestPanel.tsx`
- Test: `apps/api/tests/zhongshu/test_backtest_matrix.py`
- Test: `apps/api/tests/zhongshu/test_backtest_portfolio.py`
- Test: `apps/api/tests/zhongshu/test_backtest_reproducibility.py`
- Test: `apps/web/src/features/backtest/BacktestPanel.test.tsx`

**Interfaces:**
- `BacktestMatrixRunner.run(request, matrix, progress) -> BacktestResult`。
- `PortfolioBacktestRunner.run(request, symbols, data_version, progress) -> PortfolioBacktestResult`。
- `BacktestResult.reproducibility_hash` is SHA-256 over request, data version, strategy version, costs and trades.

- [ ] **Step 1: Write failing tests for T+1, limits, portfolio constraints and reproducibility**

Use deterministic bars covering a buy signal before a limit-up open, a sell signal before a limit-down open, a suspension, 100-share rounding, fees and a two-symbol maximum-position portfolio. Assert blocked trades contain Chinese reasons and two identical runs have the same hash.

- [ ] **Step 2: Run focused tests and confirm red**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/zhongshu/test_backtest_matrix.py apps/api/tests/zhongshu/test_backtest_portfolio.py apps/api/tests/zhongshu/test_backtest_reproducibility.py -q`

- [ ] **Step 3: Implement matrix and portfolio runners**

Use existing bar contracts and market calendar. Read only point-in-time fields, apply historical board limits, preserve blocked orders, and keep existing single-stock result fields compatible.

- [ ] **Step 4: Add progress and result cards**

Backtest API exposes `prepare`, `scan`, `simulate`, `metrics`, `persist`, `completed` stages. UI shows equity, drawdown, trade count, cost, sample status, OOS status and warnings in compact cards; insufficient evidence remains visibly gated.

- [ ] **Step 5: Run focused tests, the existing backtest suite and commit**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/zhongshu apps/api/tests/routes/test_backtest.py -q`; `pnpm --dir apps/web test -- --run apps/web/src/features/backtest/BacktestPanel.test.tsx`

```powershell
git add apps/api/src/qibao_api/zhongshu apps/api/src/qibao_api/contracts/backtest.py apps/api/src/qibao_api/routes/backtest.py apps/api/tests/zhongshu apps/web/src/features/backtest
git commit -m "feat: extend point-in-time portfolio backtesting"
```

### Task 5: P3 监控中心、Edge TTS 和飞书投递

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/monitor_center.py`
- Create: `apps/api/src/qibao_api/contracts/monitor_center.py`
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Modify: `apps/api/src/qibao_api/routes/speech.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Create: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Create: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`
- Test: `apps/api/tests/a_shares/test_monitor_center.py`
- Test: `apps/api/tests/routes/test_monitor_center.py`

**Interfaces:**
- `MonitorCenterService.save_rule(rule)`, `evaluate(snapshot)`, `acknowledge(alert_id)`, `history(limit)`。
- Rule conditions support price, volume, strategy, news, sector and risk-gate fields with `all/any` logic.
- `AlertDeliveryQueue.submit(alert)` dispatches in-app, Edge TTS and Feishu channels independently.
- API: `GET/POST/PUT /api/v1/monitor-center/rules`, `GET /api/v1/monitor-center/alerts`, `POST /api/v1/monitor-center/test`.

- [ ] **Step 1: Write failing tests for rule evaluation, cooldown, dedupe and delivery isolation**

Assert a matching rule produces one immutable alert, a second snapshot inside cooldown is suppressed, a changed input hash can alert again, TTS failure does not prevent in-app persistence, and unconfigured Feishu reports `未配置` rather than success.

- [ ] **Step 2: Run focused tests and confirm red**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_monitor_center.py apps/api/tests/routes/test_monitor_center.py -q`

- [ ] **Step 3: Implement monitor service and route**

Reuse the existing realtime event bus and alert inbox. Store rules and alerts append-only with rule version, snapshot hash, exact matched conditions, source time, delivery states and Chinese error messages.

- [ ] **Step 4: Connect Edge TTS and Feishu queues**

Reuse `speech/edge_tts_service.py` and existing Feishu webhook adapter. Queue delivery on separate executors/tasks; never await network delivery in quote polling. Add voice settings and channel status to existing settings API.

- [ ] **Step 5: Add the first-level 监控中心 menu and UI**

Add a same-level navigation item, rule editor, active rule cards, alert history, source timestamp, matched conditions, “打开个股观察/公司研究/量化分析” actions and visible delivery states. Do not add beginner/expert mode switches.

- [ ] **Step 6: Run tests and commit**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_monitor_center.py apps/api/tests/routes/test_monitor_center.py apps/api/tests/routes/test_speech.py -q`; `pnpm --dir apps/web test -- --run apps/web/src/features/monitor-center/MonitorCenterView.test.tsx apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`

```powershell
git add apps/api/src/qibao_api/contracts/monitor_center.py apps/api/src/qibao_api/a_shares/monitor_center.py apps/api/src/qibao_api/shangshu/intraday_monitor.py apps/api/src/qibao_api/routes/speech.py apps/api/src/qibao_api/routes/settings.py apps/api/tests/a_shares/test_monitor_center.py apps/api/tests/routes/test_monitor_center.py apps/web/src/features/beginner-shell/BeginnerNavigation.tsx apps/web/src/features/monitor-center
git commit -m "feat: add monitor center with voice and feishu delivery"
```

### Task 6: P4 盘后冻结、AI 复盘和飞书推送

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/postclose_report.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_review.py`
- Modify: `apps/api/src/qibao_api/shangshu/scheduler.py`
- Modify: `apps/api/src/qibao_api/routes/market_review.py`
- Modify: `apps/web/src/features/beginner-shell/HistoryReview.tsx`
- Test: `apps/api/tests/a_shares/test_postclose_report.py`
- Test: `apps/api/tests/shangshu/test_postclose_scheduler.py`
- Test: `apps/web/src/features/beginner-shell/HistoryReview.test.tsx`

**Interfaces:**
- `PostCloseReportBuilder.freeze(trading_date) -> FrozenMarketReport`。
- `PostCloseReportBuilder.explain(frozen, ai_provider) -> VersionedReviewReport`。
- `PostCloseReportRepository.append(report)` and `latest(trading_date)` are immutable.
- Scheduler job `postclose_review` runs only after a confirmed trading day and records a task snapshot.

- [ ] **Step 1: Write failing tests for freeze ordering, partial data and retry**

Assert that a report cannot freeze before close, facts remain available when AI is unavailable, missing coverage yields `partial`, a failed Feishu delivery is recorded without changing the report, and a retry does not rerun completed data collection.

- [ ] **Step 2: Run focused tests and confirm red**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_postclose_report.py apps/api/tests/shangshu/test_postclose_scheduler.py -q`

- [ ] **Step 3: Implement deterministic freeze and immutable report versions**

Freeze market breadth, limit-up/down ladder, strategy candidates, monitor alerts, news clusters, data health and candidate outcomes. Each section carries source timestamps and coverage. Never write “暂无数据” as a successful result when the source failed; return a reason code.

- [ ] **Step 4: Add AI explanation and Feishu delivery**

Send only the frozen evidence package to the configured OpenAI-compatible provider. Store prompt/input hash, model, generated time and explanation status. Reuse the existing Feishu adapter and report delivery queue; send a concise card with a linkable local report ID, trading date, coverage and status.

- [ ] **Step 5: Connect scheduler and history UI**

Register the confirmed post-close job, expose manual rerun with idempotency, and add report cards with “事实数据/AI解释/数据缺口/推送状态” sections. Preserve old historical reports.

- [ ] **Step 6: Run tests and commit**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_postclose_report.py apps/api/tests/shangshu/test_postclose_scheduler.py apps/api/tests/zhongshu/test_postclose_review.py -q`; `pnpm --dir apps/web test -- --run apps/web/src/features/beginner-shell/HistoryReview.test.tsx`

```powershell
git add apps/api/src/qibao_api/a_shares/postclose_report.py apps/api/src/qibao_api/a_shares/market_review.py apps/api/src/qibao_api/shangshu/scheduler.py apps/api/src/qibao_api/routes/market_review.py apps/api/tests/a_shares/test_postclose_report.py apps/api/tests/shangshu/test_postclose_scheduler.py apps/web/src/features/beginner-shell/HistoryReview.tsx apps/web/src/features/beginner-shell/HistoryReview.test.tsx
git commit -m "feat: add immutable post-close review reports"
```

### Task 7: P5 EXE 性能、迁移、验收和发布

**Files:**
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Create: `scripts/verify-tickflow-integration.ps1`
- Create: `docs/verification/2026-08-21-tickflow-capability-integration.md`
- Modify: `README.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- `verify-tickflow-integration.ps1` checks migration version, source health, import task states, strategy gate states, backtest reproducibility, monitor delivery isolation, post-close report status and persistent directory preservation.

- [ ] **Step 1: Add failing release-gate assertions**

The script must fail if any new endpoint returns an unstructured error, if an import task has no progress/error state, if a report claims `ready` without coverage, if a backtest hash changes on identical input, or if a test run leaves the user-facing EXE or TDX altered.

- [ ] **Step 2: Run the new gate against the current release and confirm the expected missing-capability failures**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify-tickflow-integration.ps1 -ReleaseRoot dist/XiaoQiBao-Portable`

Expected: FAIL until Tasks 1–6 are present; failure output must list Chinese capability names and exact missing checks.

- [ ] **Step 3: Implement release preservation and integration checks**

Ensure the portable builder preserves `config/data/news/cache/logs/models/exports/backups`, supports staged output when the current release is occupied, and records source commit, EXE SHA-256, test counts and quality warnings.

- [ ] **Step 4: Run full verification**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q
pnpm --dir apps/web test -- --run
pnpm --dir apps/web build
apps/api/.venv/Scripts/ruff.exe check apps/api/src apps/api/tests
rg -n -S "\?\?\?|锟斤拷|Ã|Â" apps/api/src apps/web/src
git diff --check
scripts/build-portable.ps1
scripts/run-portable-smoke.ps1 -UseReleaseData
scripts/verify-tickflow-integration.ps1 -ReleaseRoot dist/XiaoQiBao-Portable
```

Expected: all required commands exit 0; any real data warning remains explicitly `partial/stale/unavailable`.

- [ ] **Step 5: Write verification evidence and update project memory**

Record API/Web test counts, build and smoke timings, EXE path/hash, release preservation, data source statuses, monitor delivery results, post-close report status and the fact that TDX was not closed or restarted. Validate the memory vault with `tools/validate_vault.py` and do not store keys or tokens.

- [ ] **Step 6: Commit release and documentation changes**

```powershell
git add scripts docs/verification README.md docs/roadmap.md
git commit -m "chore: verify tickflow capability integration release"
```

## Self-review checklist

- Every design requirement has a task: contracts (1), import/multi-source (2), strategy/AI (3), backtest (4), monitor/TTS/Feishu (5), post-close review (6), EXE governance (7).
- No task depends on copying external code or on a browser-only delivery.
- All new public interfaces are named before their consumers.
- Every task begins with a failing test and ends with a focused verification command.
- No `TODO`, `TBD`, or unspecified “appropriate handling” placeholder remains.
