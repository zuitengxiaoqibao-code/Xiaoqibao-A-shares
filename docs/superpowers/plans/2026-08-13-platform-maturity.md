# 平台成熟化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将真实数据变得更快、更完整、更容易追溯，并以可观测性质量门禁、可复现发布与数据库迁移回滚两个工程治理项保障持续交付。

**Architecture:** 在现有 `dailySnapshotCache`、`incrementalResource`、`coalescedFetch`、来源健康和证据账本之上，增加轻量性能事件、历史质量报告、字段冲突索引和发布/迁移清单。前端先展示同日完整快照，后端按域增量刷新；所有结论引用快照与规则版本。

**Tech Stack:** React 19、TypeScript、Vitest、FastAPI、pytest、DuckDB/SQLite、PowerShell、PyInstaller、ECharts。

## Global Constraints

- 只交付 Windows 便携 EXE，不生成浏览器或 HTML 交付物。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。
- 不使用模拟行情、随机数据、零值或无关字段填充缺失数据。
- A 股红色表示上涨/改善，绿色表示下跌/恶化。
- 保留 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。
- 字体和图表文字不得降到 12px 以下。
- 修改中文文件使用 UTF-8，完成乱码扫描、测试、构建、`git diff --check` 和真实 EXE smoke。

### Task 1: 性能基线与数据域事件

**Files:**
- Create: `apps/web/src/shared/performance/perfLedger.ts`
- Create: `apps/web/src/shared/performance/perfLedger.test.ts`
- Modify: `apps/web/src/shared/coalescedFetch.ts`
- Modify: `apps/web/src/shared/incrementalResource.ts`
- Modify: `apps/api/src/qibao_api/operations/` existing source-health/event modules
- Test: matching API operations tests

**Interfaces:**
- `recordPerfEvent(event: { domain: string; phase: string; durationMs: number; cacheHit: boolean; status: string; observedAt: string }): void`
- `readPerfSummary(domain?: string): { count: number; p50Ms: number | null; p95Ms: number | null; cacheHitRate: number | null }[]`

- [ ] Write tests for percentile calculation, empty domain, and same-request coalescing counters.
- [ ] Run `pnpm --filter web exec vitest run src/shared/performance/perfLedger.test.ts`; expected initial failure because the ledger is absent.
- [ ] Implement an in-memory bounded ledger (maximum 500 events), percentile interpolation, and safe no-op behavior when `performance` is unavailable.
- [ ] Instrument `coalescedFetch` and incremental resource completion without changing public fetch behavior.
- [ ] Run the focused test and existing `coalescedFetch`/`incrementalResource` tests.
- [ ] Commit: `perf: add bounded data-domain performance ledger`.

### Task 2: 首屏和切页快照复用

**Files:**
- Modify: `apps/web/src/shared/dailySnapshotCache.ts`
- Modify: `apps/web/src/features/market-overview/marketOverviewCache.ts`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Test: each page's cache and refresh tests

**Interfaces:**
- `readDailySnapshot` continues returning the existing value and `cachedAt`, with optional `sourceCutoff` and `completeness` metadata.
- A visible page must render a complete same-day snapshot before requesting latest data.

- [ ] Add regression tests proving a page switch reuses a same-day complete snapshot and does not start duplicate full-page loads.
- [ ] Add a test proving a partial/empty response leaves the complete snapshot visible and records a stale/partial status.
- [ ] Route each page's refresh through existing single-flight calls and domain-specific intervals.
- [ ] Add lightweight background status updates for cache hit, latest fetch, and monitoring state.
- [ ] Run the four focused page test suites and production web build.
- [ ] Commit: `perf: reuse same-day snapshots across core workspaces`.

### Task 3: 历史覆盖质量与缺口修复闭环

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/history_quality.py`
- Create: `apps/api/src/qibao_api/contracts/history_quality.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/api/src/qibao_api/gongbu/full_market_history.py`
- Test: `apps/api/tests/a_shares/test_history_quality.py`, route tests

**Interfaces:**
- `inspect_history_quality(trading_dates, symbols, bars) -> HistoryQualityReport`
- `HistoryQualityReport` includes `expected_sessions`, `covered_sessions`, `coverage_ratio`, `gaps`, `status`, `source`, `observed_at`.
- `POST /api/v1/operations/history-quality/repair` accepts an explicit gap batch and returns append-only task progress.

- [ ] Write tests for missing middle dates, duplicate bars, future dates, and zero-symbol input.
- [ ] Run focused pytest and verify failures before implementation.
- [ ] Implement deterministic checks against existing bar repository and TDX import records; do not synthesize bars.
- [ ] Add repair task progress with batch ID, source, before/after coverage and failure reasons.
- [ ] Expose the report to the existing operations/data settings panel with Chinese status copy.
- [ ] Run API quality, import, and operations tests.
- [ ] Commit: `feat: add historical coverage quality and repair ledger`.

### Task 4: 字段证据与来源冲突中心

**Files:**
- Create/extend: `apps/api/src/qibao_api/contracts/field_evidence.py`, `evidence_ledger.py`
- Modify: relevant source merge modules under `apps/api/src/qibao_api/a_shares/` and `gongbu/`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Test: field evidence, source health and route tests

**Interfaces:**
- `FieldEvidence(field, value_hash, source, observed_at, parser_version, snapshot_id, selected, selection_reason)`.
- `SourceConflict(field, candidates, selected_source, severity, detected_at)`.

- [ ] Add tests for equal values from two sources, conflicting values, and missing source timestamps.
- [ ] Store only hashes and redacted summaries in user-visible diagnostics; preserve raw payloads in local data storage.
- [ ] Make source selection deterministic by source priority, freshness and completeness; never silently overwrite a newer value.
- [ ] Add a compact conflict count and drill-down to operations without blocking unrelated pages.
- [ ] Run API and focused web evidence tests.
- [ ] Commit: `feat: expose field evidence and source conflicts`.

### Task 5: 研究/量化生命周期与变更追踪

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/company_research_versions.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy_snapshot.py`
- Modify: `apps/api/src/qibao_api/a_shares/decision_journal.py`
- Modify: related routes/contracts and `apps/web/src/features/company-research/` and `quant-analysis/`
- Test: lifecycle, decision journal and candidate evidence tests

**Interfaces:**
- Every research/quant result stores `input_snapshot_ids`, `formula_version`, `generated_at`, `status`, `change_summary`.
- Candidate lifecycle states are `observed`, `triggered`, `invalidated`, `reviewed`; transitions append events and never mutate history.

- [ ] Add tests for same-input reuse, changed-input new version, invalidation, and unavailable evidence.
- [ ] Add deterministic change summaries comparing field hashes, not free-form AI claims.
- [ ] Link candidate cards and research summaries to the exact source snapshot and observed date.
- [ ] Ensure no `ready` result is emitted when required evidence is missing.
- [ ] Run API and web lifecycle tests.
- [ ] Commit: `feat: track research and quant decision lifecycles`.

### Task 6: 治理项 A：可观测性与质量门禁

**Files:**
- Create: `apps/api/src/qibao_api/operations/quality_gates.py`
- Create: `apps/api/tests/operations/test_quality_gates.py`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/build-portable.ps1`
- Modify: `docs/verification/2026-08-13-platform-maturity.md`

**Interfaces:**
- `evaluate_quality_gates(result) -> QualityGateReport` checks test/build/encoding/diff/smoke/data-integrity outcomes.
- Smoke output includes window visible, API ready, first-screen, full validation, source health, coverage and process cleanup.

- [ ] Write tests for pass, warning and fail gate combinations; secrets must never appear in output.
- [ ] Add a release gate that fails on test/build/encoding/smoke failure or integrity below the configured threshold.
- [ ] Record P50/P95 and data coverage in the smoke manifest.
- [ ] Keep raw diagnostics local and export only redacted summaries.
- [ ] Run gate tests and smoke script syntax checks.
- [ ] Commit: `chore: enforce observable release quality gates`.

### Task 7: 治理项 B：可复现发布与数据库迁移/回滚

**Files:**
- Create/modify: `apps/api/src/qibao_desktop/data_migration.py`
- Create: `apps/api/src/qibao_desktop/release_manifest.py`
- Create: matching tests under `apps/api/tests/desktop/`
- Modify: `scripts/build-portable.ps1`
- Modify: `apps/api/src/qibao_desktop/pending_update.py`

**Interfaces:**
- `ReleaseManifest(version, commit, dependency_lock_hash, migration_version, persistent_dirs, exe_sha256)`.
- `apply_migrations(db, target_version)` is idempotent and records applied versions; failed migration restores the pre-migration backup.

- [x] Add tests for idempotent migration, failed migration rollback, persistent directory preservation and manifest hash completeness.
- [x] Generate a manifest containing commit, dependency lock hash, migration version, eight directory names and EXE SHA-256.
- [x] Add preflight backup and postflight verification to portable build; never delete persistent data on failure.
- [x] Run desktop packaging and migration tests.
- [ ] Commit: `chore: make portable releases reproducible and migratable`.

### Task 8: 全量验收与 EXE 交付

**Files:**
- Create: `docs/verification/2026-08-13-platform-maturity.md`
- Modify: project plan checkboxes and `知识库/02-项目记忆/金融财经.md` after completion

- [x] Run API full suite, web full suite, production build, UTF-8/mojibake scan and `git diff --check`.
- [x] Run `scripts/build-portable.ps1` and preserve `config/data/news/cache/logs/models/exports/backups`.
- [x] Run `scripts/run-portable-smoke.ps1 -UseReleaseData` against the rebuilt EXE.
- [x] Verify no test EXE/API process remains; this environment had no TdxW process or local 17709 listener to compare.
- [x] Record measured P50/P95, coverage, conflicts, unavailable domains and EXE SHA-256.
- [x] Update Vault with confirmed facts and no secrets; validator reported an environment encoding limitation.
- [ ] Commit: `docs: record platform maturity verification` (留在当前用户工作树，不自动提交)。
