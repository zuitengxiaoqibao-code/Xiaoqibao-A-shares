# 首次涨停 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persisted, evidence-first “首次涨停” A-share research domain with scheduled after-close scanning, a pullback pool, and beginner-friendly rule explanations.

**Architecture:** Keep the existing dashboard shell and add one isolated backend service, SQLite repository, contracts, and route. The service consumes the existing local daily-bar repository and authorized Tencent quote source, computes deterministic rule output, and is called by the post-close scheduler. The web app gets one loader/view and a navigation route; no existing A-share or bond data contracts are changed.

**Tech Stack:** FastAPI, Pydantic, SQLite, existing DuckDB `BarRepository`, React, TypeScript, Vitest, Testing Library.

## Global Constraints

- Do not connect a broker, execute orders, or add paper-money state.
- Do not fabricate PE, K-line, or limit-up data; missing data remains `待验证`.
- Preserve existing routes, localStorage keys, accessibility roles, and convertible-bond separation.
- Use `apply_patch` for Chinese source edits and keep files UTF-8.
- Every production behavior is introduced by a failing test first.

### Task 1: Rule contracts and pure evaluator

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/first_limit_up.py`
- Create: `apps/api/src/qibao_api/contracts/first_limit_up.py`
- Test: `apps/api/tests/a_shares/test_first_limit_up.py`

**Interfaces:**
- `evaluate_first_limit_up(symbol, name, bars, pe_ttm, as_of) -> FirstLimitUpCandidate | None`.
- `refresh_candidate_state(candidate, bars, current_close) -> FirstLimitUpCandidate`.
- `FirstLimitUpCandidate` and `FirstLimitUpBoard` are frozen Pydantic responses.

- [x] **Step 1: Write failing tests** for 10%/20% limit-up detection, negative and >50 PE exclusion, recent-limit exclusion, weekly/monthly bottom requirement, limit-up-day no-buy, and 5%–20% pullback state.
- [x] **Step 2: Run the focused API test** with `pytest apps/api/tests/a_shares/test_first_limit_up.py -q`; expect failures because the contracts/evaluator do not exist.
- [x] **Step 3: Implement the minimal contracts and pure evaluator** with board-specific 10%/20% limit rates, 20-bar first-board lookback, weekly/monthly aggregation, explicit reasons and rule version.
- [x] **Step 4: Re-run the focused test** and then `pytest apps/api/tests/a_shares/test_first_limit_up.py -q`; expect all rules to pass.

### Task 2: Persisted pool and service

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/first_limit_up_repository.py`
- Create: `apps/api/src/qibao_api/a_shares/first_limit_up_service.py`
- Test: `apps/api/tests/a_shares/test_first_limit_up_service.py`

**Interfaces:**
- `FirstLimitUpRepository.upsert_many(candidates)` and `.list_recent(limit, as_of)`.
- `FirstLimitUpService.refresh(as_of) -> FirstLimitUpBoard` and `.current(as_of) -> FirstLimitUpBoard`.

- [x] **Step 1: Write failing service tests** for scanning local bars, persisting a candidate, retaining older monthly records, and recalculating pullback state without letting missing data pass.
- [x] **Step 2: Run the service test** and confirm the expected missing-module failures.
- [x] **Step 3: Implement the SQLite repository** with a primary key on symbol/date and JSON fields for reasons, risks, and sources.
- [x] **Step 4: Implement the service** using `symbols_with_history`, `latest_many`, serial quote fetches for only current limit-up candidates, and deterministic ranking.
- [x] **Step 5: Run the service tests** and keep the old pool when a refresh source fails.

### Task 3: API route, app wiring, and post-close scheduling

**Files:**
- Create: `apps/api/src/qibao_api/routes/first_limit_up.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/shangshu/scheduler.py`
- Tests: `apps/api/tests/routes/test_first_limit_up.py`, `apps/api/tests/shangshu/test_scheduler.py`

**Interfaces:**
- `GET /api/v1/a-shares/first-limit-up` returns `FirstLimitUpBoard`.
- `POST /api/v1/a-shares/first-limit-up/refresh` runs a post-close scan and returns the same board.
- Scheduler receives an optional `first_limit_up_service` and records an independent `first_limit_up` post-close job.

- [x] **Step 1: Add failing route and scheduler tests** for dependency injection, empty board response, refresh delegation, and one post-close scan per trading date.
- [x] **Step 2: Run the focused route/scheduler tests** and confirm they fail for the missing route/service wiring.
- [x] **Step 3: Add the dependency, lifespan repository/service construction, route inclusion, and scheduler hook** without changing existing job semantics.
- [x] **Step 4: Run focused API tests and the full API suite**.

### Task 4: Web menu and research view

**Files:**
- Create: `apps/web/src/features/first-limit-up/types.ts`
- Create: `apps/web/src/features/first-limit-up/api.ts`
- Create: `apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`
- Create: `apps/web/src/features/first-limit-up/FirstLimitUpView.test.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- `loadFirstLimitUp(asOf?) -> Promise<FirstLimitUpBoard>` and `refreshFirstLimitUp() -> Promise<FirstLimitUpBoard>`.
- `BeginnerView` gains `first_limit_up`; path is `/first-limit-up`.

- [x] **Step 1: Write failing web tests** for the nav label, default “今日首板” tab, summary cards, no-buy warning, and pullback rule copy.
- [x] **Step 2: Run the focused web test** and confirm the missing view/menu failure.
- [x] **Step 3: Implement the API adapter, page, navigation route, and compact detail drawer using existing monitor-console classes and semantic colors.
- [x] **Step 4: Run focused web tests, full web tests, and build.

### Task 5: Verification and documentation

**Files:**
- Modify: `README.md` or `docs/roadmap.md` only if the existing roadmap has a feature index entry.

- [x] **Step 1: Run `pytest -q` in `apps/api` and `pnpm --filter @qibao/web test`.
- [x] **Step 2: Run `pnpm build`.
- [x] **Step 3: Run `git diff --check` and a UTF-8/mojibake scan for touched Chinese files.
- [x] **Step 4: Review the diff to ensure no simulated-funds code, broker integration, or fabricated fallback data was added.
