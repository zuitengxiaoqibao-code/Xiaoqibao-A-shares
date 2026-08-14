# Evidence-First Performance Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Make the A-share observation terminal fast to open, stable during refresh, explicit about evidence quality, and capable of measuring strategy outcomes without fabricating market data.

**Architecture:** Keep the existing EXE and embedded React/API architecture. Add a date-scoped, versioned quant snapshot store under the portable `cache` directory; serve the last valid snapshot immediately while one background refresh runs. Expose evidence metadata as structured API fields, render it through shared visual primitives, and persist outcome records for later walk-forward review.

**Tech Stack:** Python 3.12, FastAPI, DuckDB/local TDX adapters, Pydantic contracts, React + TypeScript, ECharts, Vitest, pytest, PyInstaller portable EXE.

## Execution Status (2026-08-11)

- Stage 1 completed: date-scoped snapshots, stale-while-refresh response fields, and frontend merge behavior.
- Stage 2 completed: factor cache, process-isolated local candidate scan, bounded refresh requests, and smoke assertions.
- Stage 3 completed through the existing evidence/source/freshness contracts and shared data-status panels.
- Stage 4 completed through the existing signal vote engine, score breakdown, regime gauge, and red/green semantic palette.
- Stage 5 completed through the existing post-close outcome resolver, History Review, and strategy backtest metrics.
- Stage 6 completed through the existing evidence-bound AI gateways, contrary evidence fields, and invalid-output fallback.
- Stage 7 completed: final full-suite verification, portable rebuild, smoke, continuous-refresh probe, and delivery record.

## Global Constraints

- The Windows EXE is the only user-facing delivery entry point.
- Use local TDX/DuckDB data first; never replace missing fields with zero, random, or unrelated proxy values.
- Same-trading-day stale data may be shown only with an explicit timestamp and refresh state; cross-day snapshots are invalid.
- A-share colors remain red for rise/improvement/inflow and green for fall/deterioration/outflow.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` during portable rebuilds.
- Do not close, restart, or control the user's TongdaXin process.
- Every behavior change requires a failing test before production code, then targeted and full verification.

---

### Stage 1: Durable Quant Snapshots and Refresh Contract

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_strategy_snapshot.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/routes/a_shares.py`
- Modify: `apps/api/tests/a_shares/test_quant_strategy.py`
- Create: `apps/api/tests/a_shares/test_quant_strategy_snapshot.py`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/strategySnapshot.ts`
- Modify: `apps/web/src/features/quant-analysis/useQuantLiveRefresh.ts`

**Interfaces:**
- `QuantStrategySnapshotStore.load(trading_date, formula_version) -> QuantStrategyDashboard | None`
- `QuantStrategySnapshotStore.save(dashboard) -> None`
- `QuantStrategyService.current(...)` returns the previous same-day dashboard with `refresh_state=pending|failed` while a single refresh job runs.
- The API response includes `snapshot_at`, `refresh_started_at`, `refresh_finished_at`, `refresh_state`, and `snapshot_source`.

- [x] Write failing tests for UTF-8 JSON snapshot round-trip, cross-day rejection, formula-version rejection, and stale-while-refresh API behavior.
- [x] Run the focused pytest tests and confirm they fail because the store and response fields do not exist.
- [x] Implement an atomic JSON store under the portable cache path using a temporary file plus `os.replace`; write only validated Pydantic response data.
- [x] Load the latest same-day snapshot before starting a refresh; keep it during pending/failed refresh and replace it only after a ready result is validated.
- [x] Add frontend merge behavior that preserves the last ready dashboard across pending/failed responses and surfaces refresh state without clearing chart data.
- [x] Run focused API/frontend tests, then full API/frontend tests and production build.

### Stage 2: Incremental Candidate Scanning and Startup Performance

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_review.py`
- Modify: `apps/api/src/qibao_api/gongbu/local_market_review.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_factor_cache.py`
- Create: `apps/api/tests/a_shares/test_quant_factor_cache.py`
- Modify: `apps/api/tests/a_shares/test_quant_strategy.py`
- Modify: `scripts/run-portable-smoke.ps1`

**Interfaces:**
- `QuantFactorCache.get_or_compute(trading_date, symbol, factor_version, loader) -> FactorSnapshot`
- Candidate scans report real `processed`, `total`, `cache_hits`, and `elapsed_ms` values.

- [x] Write failing tests proving unchanged symbols are not recomputed and a partial scan returns the previous candidate list.
- [x] Add date/version keyed factor caching backed by DuckDB or compact JSON, with explicit invalidation on source-date or formula-version changes.
- [x] Bound local TDX concurrency and separate market overview, candidate factors, and trigger evidence queues.
- [x] Change the portable smoke test to assert first response latency, cached response latency, and no candidate loss during the refresh window.
- [x] Verify the target: cached first paint under 1 second, API readiness under 10 seconds, and no user-visible blank state after the first valid snapshot.

### Stage 3: Data Credibility Instrumentation

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/contracts/market_overview.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/routes/market_overview.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Create: `apps/web/src/features/data-status/EvidenceQualityStrip.tsx`
- Create: `apps/web/src/features/data-status/EvidenceQualityStrip.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`

**Interfaces:**
- `EvidenceQuality`: `{ source, observed_at, sample_count, coverage_percent, latency_ms, freshness, state, missing_fields }`.
- Every aggregate metric includes its sample scope and evidence state.

- [x] Write failing component/API tests for source, timestamp, coverage, latency, and missing-field labels.
- [x] Implement a shared evidence strip with `ready`, `partial`, `stale`, `unavailable`, and `error` states.
- [x] Ensure unavailable metrics render `--` plus a reason, never a numeric placeholder.
- [x] Add response-level source provenance for TDX, DuckDB, news, and derived calculations.
- [x] Verify all affected pages at desktop and narrow widths.

### Stage 4: Explainable Scores and Visual Semantics

**Files:**
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantChartOptions.ts`
- Create: `apps/web/src/features/quant-analysis/SignalEvidenceDrawer.tsx`
- Create: `apps/web/src/features/quant-analysis/SignalEvidenceDrawer.test.tsx`
- Modify: `apps/web/src/app/theme.css`

- [x] Write failing tests for expanding a candidate into signal votes, formula inputs, missing evidence, trigger, and invalidation sections.
- [x] Render the compact dashboard by default and expose detail only on demand.
- [x] Apply the site-wide red/green semantic palette and neutral structural colors consistently.
- [x] Keep numeric precision bounded to what the source supports and prevent label overlap through stable chart dimensions.
- [x] Verify ECharts options and responsive layouts with unit tests and production build.

### Stage 5: Historical Review and Strategy Outcome Loop

**Files:**
- Modify: `apps/api/src/qibao_api/zhongshu/postclose_review.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Create: `apps/api/src/qibao_api/a_shares/strategy_outcomes.py`
- Create: `apps/api/tests/a_shares/test_strategy_outcomes.py`
- Modify: `apps/web/src/features/beginner-shell/HistoryReview.tsx`
- Create: `apps/web/src/features/backtest/StrategyOutcomePanel.tsx`
- Create: `apps/web/src/features/backtest/StrategyOutcomePanel.test.tsx`

- [x] Write failing tests for recording a recommendation, resolving its outcome from later real bars, and preventing look-ahead data.
- [x] Store immutable recommendation inputs and derived outcome fields with source dates.
- [x] Calculate win rate, payoff ratio, max drawdown, Sharpe, and regime-specific performance only when sample counts meet declared minimums.
- [x] Add strategy selection and walk-forward review controls; show “样本不足” instead of unstable statistics.
- [x] Verify historical dates, source coverage, and no future-bar leakage.

### Stage 6: AI Evidence Explanation and Counter-Case Review

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/assessment_ai.py`
- Modify: `apps/api/src/qibao_api/zhongshu/news_ai.py`
- Modify: `apps/api/src/qibao_api/zhongshu/decision_ai.py`
- Modify: `apps/api/src/qibao_api/contracts/decision.py`
- Create: `apps/api/src/qibao_api/a_shares/evidence_explanation.py`
- Create: `apps/api/tests/a_shares/test_evidence_explanation.py`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`

- [x] Write failing tests requiring every AI claim to reference an observed source item or be labeled unavailable.
- [x] Implement structured prompts from numeric evidence, news, filings, and risk flags; never ask AI to invent prices or scores.
- [x] Add a “反方审查” section with separated supporting evidence, opposing evidence, unresolved questions, and invalidation conditions.
- [x] Display model/source timestamp and configuration state; handle missing AI configuration explicitly.
- [x] Verify prompt payload redaction and AI failure fallback.

### Stage 7: Release Acceptance and EXE Delivery

**Files:**
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/run-portable-smoke.ps1`
- Create: `docs/verification/2026-08-11-evidence-first-performance-loop.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

- [x] Run API and frontend full suites, TypeScript/Vite build, UTF-8/mojibake scan, and `git diff --check`.
- [x] Rebuild the portable EXE while preserving all persistent directories.
- [x] Run the smoke test against the rebuilt release and a separate continuous-refresh probe.
- [x] Verify the final EXE hash, startup timings, honest statuses, and that only the test process exits.
- [x] Record confirmed results and remaining unavailable sources in the verification document and project memory.
