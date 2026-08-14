# Market Evidence and Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved data-watermark, candidate-funnel, evidence-ledger, strategy-evaluation, research, news, and local-operations improvements in the portable Windows product.

**Architecture:** Extend existing validated read models rather than adding another data pipeline. Compute full-universe evidence in the existing background market-review and quant candidate process, persist date-scoped snapshots, and render them through focused React components that preserve cached content during refresh.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, DuckDB, SQLite, React, TypeScript, Vitest, ECharts, PyInstaller portable EXE.

## Global Constraints

- EXE is the only user-facing entry point.
- No simulated, random, or proxy data may be presented as real evidence.
- Red is rise/improvement/inflow; green is fall/deterioration/outflow.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups`.
- Never close, restart, or control TongdaXin.
- Every behavior change follows test-first red/green verification.

---

### Task 1: Collapsible Source Health

**Files:**
- Modify: `apps/web/src/features/data-settings/SourceHealthPanel.tsx`
- Modify: `apps/web/src/features/data-settings/SourceHealthPanel.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:** `SourceHealthPanel` remains compatible with `SourceHealthLoader`; detailed loading becomes lazy until expansion.

- [x] Add a failing test proving the panel is collapsed and has not loaded on first render.
- [x] Add a failing test proving manual expansion loads and displays health rows.
- [x] Implement the accessible disclosure header and lazy first load.
- [x] Run focused and data-settings tests.

### Task 2: Market Data Watermark Contract

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/market_review.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_review.py`
- Modify: `apps/api/tests/a_shares/test_market_review.py`
- Modify: `apps/web/src/features/market-overview/types.ts`

**Interfaces:** Produce `MarketDataWatermark` with dominant date, universe count, ready count, coverage, fragmented count, missing-history count, quality, and blockers.

- [x] Add failing contract and service tests for complete, fragmented, and unavailable history.
- [x] Compute the watermark from real grouped daily-bar dates in the existing review pass.
- [x] Preserve nulls and explicit blockers when the source is unavailable.
- [x] Run focused API tests.

### Task 3: Candidate Selection Funnel

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_candidate_process.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/tests/a_shares/test_quant_candidate_process.py`
- Modify: `apps/api/tests/a_shares/test_quant_strategy.py`
- Create: `apps/web/src/features/quant-analysis/CandidateFunnel.tsx`
- Create: `apps/web/src/features/quant-analysis/CandidateFunnel.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`

**Interfaces:** Produce deterministic funnel stages and exclusion-reason counts with a data-completeness verdict.

- [x] Add failing tests for stage monotonicity, exclusion totals, and incomplete-history zero candidates.
- [x] Count each existing real filter stage inside the isolated scan process.
- [x] Keep the last real funnel during pending/failed refresh.
- [x] Render the funnel and zero-candidate explanation.
- [x] Run focused API and web tests.

### Task 4: Unified Evidence Ledger

**Files:**
- Create: `apps/api/src/qibao_api/contracts/evidence_ledger.py`
- Create: `apps/api/tests/contracts/test_evidence_ledger.py`
- Create: `apps/web/src/shared/evidence/EvidenceLedger.tsx`
- Create: `apps/web/src/shared/evidence/EvidenceLedger.test.tsx`
- Modify: market, quant, research, and news response contracts only where verified metadata already exists.

**Interfaces:** Uniform fields: source, operation, status, trade date, observed time, formula version, sample count, limitations.

- [x] Add failing validation tests for truthful null handling and explicit limitations.
- [x] Add the shared API contract and adapters for existing evidence metadata.
- [x] Add the reusable disclosure component.
- [x] Attach it to representative market, quant, research, and news conclusions.
- [x] Run focused tests.

### Task 5: Background Update and Operations Center

**Files:**
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Create: `apps/api/src/qibao_api/operations/read_model.py`
- Create: `apps/api/tests/routes/test_operations.py`
- Modify: `apps/web/src/features/operations/OperationsView.tsx`
- Modify: `apps/web/src/features/operations/OperationsView.test.tsx`

**Interfaces:** Expose refresh jobs, cache inventory, database size, persistent directories, and safe incremental actions without executing full scans in request handlers.

- [x] Add failing API tests for non-blocking status and safe path boundaries.
- [x] Implement read-only inventory and background job status.
- [x] Add guarded incremental refresh and cache cleanup actions that never target persistent data or TongdaXin.
- [x] Render progress, failure reason, and last-success evidence.
- [x] Run focused tests.

### Task 6: Strategy Evaluation Center

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/backtest.py`
- Modify: `apps/api/src/qibao_api/zhongshu/backtest.py`
- Modify: `apps/api/tests/zhongshu/test_backtest.py`
- Modify: `apps/web/src/features/backtest/BacktestPanel.tsx`
- Modify: `apps/web/src/features/backtest/BacktestPanel.test.tsx`

**Interfaces:** Extend existing sample governance with rolling/regime evidence only when closed-trade gates pass.

- [x] Add failing tests for rolling windows, regime segments, and gated unavailable metrics.
- [x] Compute deterministic evaluation slices from existing trades.
- [x] Render sample, stability, drawdown, Sharpe, and invalidation evidence.
- [x] Run focused tests.

### Task 7: Company Research Decision Ledger

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/api/tests/a_shares/test_company_research.py`
- Create: `apps/web/src/features/company-research/ResearchDecisionLedger.tsx`
- Create: `apps/web/src/features/company-research/ResearchDecisionLedger.test.tsx`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`

**Interfaces:** Summarize verified peer context, valuation scenarios, catalysts, contrary evidence, and thesis invalidation without target-price fabrication.

- [x] Add failing tests for verified-only summaries and missing-estimate behavior.
- [x] Build the research ledger from existing enrichment and evidence records.
- [x] Render compact expandable evidence rows.
- [x] Run focused tests.

### Task 8: News Event Graph

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/news.py`
- Modify: existing news aggregation service and tests.
- Create: `apps/web/src/features/news-intelligence/NewsEventGraph.tsx`
- Create: `apps/web/src/features/news-intelligence/NewsEventGraph.test.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`

**Interfaces:** Reuse deduplicated news identifiers and verified stock/sector/theme links; impact is neutral unless supported.

- [x] Add failing tests for deduplication, source count, and neutral unverified impact.
- [x] Extend the existing event read model with category and link evidence.
- [x] Render a compact stock-sector-theme relationship view and synchronize event selection with the K-line.
- [x] Run focused tests.

### Task 9: Performance and Release Acceptance

**Files:**
- Modify: `scripts/run-portable-smoke.ps1`
- Create: `docs/verification/2026-08-11-market-evidence-operations.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

**Interfaces:** Verify window, cache-first screen, route requests, background stability, data watermark, funnel, persistent directories, and process boundaries.

- [x] Run API and web full suites plus production build.
- [x] Run UTF-8/mojibake scan and `git diff --check`.
- [x] Rebuild with `scripts/build-portable.ps1`.
- [x] Run `scripts/run-portable-smoke.ps1 -UseReleaseData` and background refresh probes.
- [x] Record EXE SHA-256, real data states, residual limitations, and TongdaXin process boundary.
- [x] Update project memory and validate the Vault.
