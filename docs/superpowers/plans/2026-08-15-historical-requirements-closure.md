# Historical Requirements Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Close the gap between the historical requirement backlog and current evidence without redoing completed work, while adding measurable guards for the remaining real risks.

**Architecture:** Treat the current source tree, tests, release manifest, and EXE smoke output as the only completion evidence. The ledger classifies each requirement as `confirmed-current`, `confirmed-historical`, `partial`, `unavailable-by-source-boundary`, or `not-started`; new gates consume machine-readable release evidence and never turn a warning into a pass.

**Tech Stack:** PowerShell 5.1+, Pester, Python 3.12, FastAPI, React/TypeScript, portable PyInstaller EXE.

## Global Constraints

- The Windows portable EXE remains the only user-facing delivery entry point.
- Real data only; missing or unverified data remains `partial`, `stale`, `unavailable`, or `error`.
- Do not start, stop, restart, or control TongdaXin; do not connect to a broker or place orders.
- Preserve `config/data/news/cache/logs/models/exports/backups` during rebuilds.
- Chinese files remain UTF-8 and all edits use `apply_patch`.

### Requirement Ledger

| Area | Current classification | Evidence | Next action |
| --- | --- | --- | --- |
| Evidence lineage, point-in-time rules, gap repair, walk-forward, event impact, snapshots, workspace restore | `confirmed-current` | v9 tests, release manifest, smoke and recovery drill | Do not reimplement; keep regression coverage |
| Release signing, migration checks, rollback, observability and quality gates | `confirmed-current` | current release manifest and PowerShell/Pester checks | Extend only when a new boundary is found |
| Quantitative analysis with real candidates | `partial` | current smoke: real candidates and 85% factor coverage | Preserve truthful partial state; improve source coverage only with verified fields |
| Company research | `partial` | current smoke: 600519 and 0.65 evidence coverage | Preserve evidence limits; do not fabricate missing filings |
| Portfolio risk | `unavailable-by-source-boundary` | no real positions configured | Keep unavailable and explain why |
| TongdaXin professional fields (`Fn193`, `GP1`, `BK5`, `SC1`, `GO1`) | `unavailable-by-source-boundary` | capability probes show missing/undocumented professional packages; semantic tests already block business binding | Keep the existing semantic evidence workflow; do not assign guessed units |
| Historical daily coverage | `partial` | coverage and repair-center APIs already expose dominant/latest dates, fragmented counts, blockers and repair audits | Keep the existing broad-date arbitration and add changes only when a current gap is reproduced |
| Cold/hot startup performance | `not-started` | smoke records single-run timings only | Add repeatable comparison gate and release evidence |
| Historical visual/menu requests | `confirmed-current` or `partial` per current route tests | current route/workspace tests and screenshots in verification docs | Audit only when a current failing behavior is reproduced |

### Task 1: Historical ledger and performance contract

**Files:**
- Create: `docs/superpowers/plans/2026-08-15-historical-requirements-closure.md`
- Create: `scripts/startup-performance.ps1`
- Create: `scripts/startup-performance.tests.ps1`

**Interface:** `Get-StartupPerformanceSummary -Runs <object[]> -ColdRunCount <int> -HotRunCount <int> -MaxColdMs <int> -MaxHotMedianMs <int> -MaxHotP95Ms <int>` returns `state`, `cold`, `hot`, `thresholds`, `warnings`, and `observed_at`. A missing timing or an invalid run state is a warning, never a pass.

- [x] Write Pester tests for cold/hot aggregation, percentile calculation, missing timing, and threshold failure.
- [x] Run the tests and observe the expected failures before implementation.
- [x] Implement the pure summary function and a CLI that reads smoke result JSON files.
- [x] Run the focused Pester tests and `git diff --check`.

### Task 2: Smoke output and release manifest integration

**Files:**
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Modify: `scripts/release-manifest.tests.ps1`

**Interface:** Smoke writes `startup_metrics` with `window_visible_ms`, `api_ready_ms`, and `full_verification_ms`; the performance gate can compare those records without inferring missing values.

- [x] Add a machine-readable smoke result beside the release manifest without changing user data.
- [x] Add release-manifest validation for the shape and numeric bounds of `startup_metrics`.
- [x] Add a Pester regression test for malformed or missing metrics.
- [x] Run all PowerShell tests and a real release-data smoke.

### Task 3: TDX professional semantic evidence workflow

**Status:** `confirmed-current`; no duplicate implementation required. Existing contracts, capability probes and focused tests already keep unverified fields in `detected_only`/`semantic_unmapped` and block business binding.

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_professional.py`
- Modify: `apps/api/src/qibao_api/contracts/tdx_local.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Create: `apps/api/tests/gongbu/test_tdx_semantic_evidence.py`

**Interface:** Probes record response shape, source package status, observed timestamp, and an explicit `semantic_status`; no field becomes business data until a verified sample dictionary is supplied.

- [x] Add failing tests for detected-only, verified, missing-package, and contradictory-unit states.
- [x] Implement evidence storage and diagnostics only; keep business consumers blocked for unverified fields.
- [x] Run focused API tests and confirm UI remains `unavailable` when semantics are unverified.

### Task 4: Historical coverage release warning

**Status:** `confirmed-current`; no duplicate implementation required. Existing coverage and market-review contracts already distinguish dominant broad dates from sparse latest outliers and expose repair/audit provenance.

**Files:**
- Modify: `apps/api/src/qibao_api/routes/data.py`
- Modify: `apps/api/src/qibao_api/gongbu/full_market_history.py`
- Modify: `scripts/run-portable-smoke.ps1`
- Create: `apps/api/tests/a_shares/test_history_release_warning.py`

**Interface:** Coverage output includes `latest_broad_trade_date`, `latest_sparse_trade_date`, `coverage_ratio`, `repair_action`, and `trace_id`; sparse dates cannot silently replace a broad cross-section date.

- [x] Add boundary tests for broad versus sparse dates and missing repair provenance.
- [x] Implement explicit warning fields and expose them in release quality evidence.
- [x] Run API tests and a real smoke using release data.

### Final Verification

- [x] Current evidence ledger is updated from fresh test/smoke outputs.
- [x] API/Web/Ruff/build checks pass.
- [x] PowerShell/Pester tests pass, including startup performance and manifest validation.
- [x] Portable EXE rebuild preserves all eight persistent directories.
- [x] Real EXE smoke and release quality gate pass or explicitly report truthful warnings.
- [x] Project memory and Vault validation are updated from confirmed facts only.
