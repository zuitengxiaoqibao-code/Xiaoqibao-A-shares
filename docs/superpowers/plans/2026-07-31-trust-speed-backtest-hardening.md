# Trust, Speed, and Backtest Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the desktop product start promptly, degrade honestly when remote sources fail, reduce quote latency, expose decision-grade backtest metrics, simplify the default navigation, and protect locally stored API credentials.

**Architecture:** Keep the existing React renderer and Python desktop/API process. Improve narrow service boundaries: overview sources degrade independently, first-limit-up quote enrichment uses bounded batches, remote universe refresh runs after readiness, backtest metrics stay pure and deterministic, navigation mode is client-local, and Windows secrets are protected at the repository boundary.

**Tech Stack:** Python 3.12, FastAPI, httpx, Pydantic, pytest, React 18, TypeScript, Vitest, Windows DPAPI, PyInstaller portable build.

## Global Constraints

- The portable Windows executable is the only user-facing delivery entry point.
- Do not generate synthetic market, news, benchmark, or performance values.
- Prefer local TDX data; remote failures must be explicit partial-data states.
- Preserve existing routes and bookmarks.
- Preserve `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` during rebuild.
- Use `apply_patch` for manual edits and scan Chinese files for mojibake before completion.

---

### Task 1: Market overview network degradation

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Test: `apps/api/tests/a_shares/test_market_overview.py`

**Interfaces:**
- Consumes: synchronous source methods `fetch_indices`, `fetch_minutes`, and `fetch_stocks`.
- Produces: `MarketOverviewResponse` with `status="partial"` and source-specific warnings when any remote call raises `httpx.HTTPError`.

- [x] Add a test source that raises `httpx.ConnectError` for each remote stage and assert the service still returns a response.
- [x] Run the focused test and confirm the network exception escapes before implementation.
- [x] Catch `httpx.HTTPError` together with existing parse and OS errors at each independent source boundary.
- [x] Run the full market-overview test module.

### Task 2: Batched first-limit-up quote enrichment

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/first_limit_up_service.py`
- Test: `apps/api/tests/a_shares/test_first_limit_up_service.py`

**Interfaces:**
- Consumes: symbols with local history eligible for first-limit-up evaluation.
- Produces: `SynchronousTencentQuoteSource.fetch_many(symbols: Sequence[str]) -> dict[str, snapshot]`; `fetch_snapshot` remains compatible.

- [x] Add tests for one request per bounded batch, partial symbol omission, and a failed batch that does not discard successful batches.
- [x] Run the focused tests and confirm `fetch_many` is missing or the request count is excessive.
- [x] Implement chunked Tencent requests and parse each symbol independently.
- [x] Update the service to evaluate local histories first and enrich eligible symbols through `fetch_many`, with a compatibility fallback for test doubles and older sources.
- [x] Run all first-limit-up tests.

### Task 3: Decision-grade backtest metrics

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/backtest.py`
- Modify: `apps/api/src/qibao_api/zhongshu/performance.py`
- Modify: `apps/api/src/qibao_api/zhongshu/backtest.py`
- Test: `apps/api/tests/zhongshu/test_performance.py`
- Test: `apps/api/tests/zhongshu/test_backtest.py`
- Modify: `apps/web/src/features/backtest/types.ts`
- Modify: `apps/web/src/features/backtest/BacktestPanel.tsx`
- Test: `apps/web/src/features/backtest/BacktestPanel.test.tsx`

**Interfaces:**
- Produces: `annualized_return`, `sharpe_ratio`, and `calmar_ratio`; ratios are `null` when the denominator is zero.
- Produces honest warnings: `corporate_actions_not_adjusted`, `benchmark_not_available`, and `survivorship_bias_not_eliminated`.

- [x] Add deterministic metric tests covering normal, zero-volatility, and zero-drawdown curves.
- [x] Run focused API tests and confirm the new fields are absent.
- [x] Implement annualized compounding, annualized Sharpe, and Calmar without infinity placeholders.
- [x] Add the three data-quality warnings to backtest results.
- [x] Add typed UI metrics and readable Chinese labels, then verify them with a component test.
- [x] Run focused API and web tests.

### Task 4: Non-blocking universe startup

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: API and desktop readiness without awaiting remote universe synchronization.
- Owns: one background refresh task that is cancelled and awaited on shutdown.

- [x] Add a lifecycle test with a never-completing universe future and assert lifespan enters promptly.
- [x] Run the test and confirm startup blocks.
- [x] Move remote synchronization into a named background coroutine; local directory state remains immediately available.
- [x] Cancel and await the task during shutdown without leaking cancellation errors.
- [x] Run lifecycle and desktop smoke-related tests.

### Task 5: Beginner and expert navigation modes

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Test: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`
- Test: `apps/web/src/features/dashboard/Dashboard.test.tsx`

**Interfaces:**
- Produces: beginner mode by default and expert mode on explicit toggle.
- Persists: mode in local storage while retaining every existing view and route.

- [x] Add tests for beginner defaults, expert expansion, persistence, and retained route navigation.
- [x] Run the focused tests and confirm the toggle is absent.
- [x] Implement a compact segmented mode control and filter only navigation visibility.
- [x] Run focused navigation tests and the web suite.

### Task 6: Windows-protected AI credentials

**Files:**
- Modify: `apps/api/src/qibao_api/settings_repository.py`
- Test: `apps/api/tests/test_settings_repository.py`

**Interfaces:**
- Produces: DPAPI-protected `api_key` persistence on Windows, transparent reads, and one-time migration from legacy plaintext JSON.
- Preserves: the current non-Windows restricted-file fallback and unchanged API contract.

- [x] Add repository tests for protected round trip and legacy plaintext migration using an injectable protector.
- [x] Run tests and confirm plaintext remains in the stored document.
- [x] Add a small credential protector boundary backed by Windows DPAPI and atomic migration writes.
- [x] Run settings tests and assert the stored document does not contain the raw key.

### Task 7: Verification and portable desktop delivery

**Files:**
- Verify: all changed source and test files
- Build: `scripts/build-portable.ps1`
- Smoke: `scripts/run-portable-smoke.ps1`

- [x] Run focused API and web tests for all six tasks.
- [x] Run the full API and web test suites plus production builds.
- [x] Scan changed Chinese files for mojibake and run `git diff --check`.
- [x] Rebuild the portable release while preserving persistent directories.
- [x] Smoke-test the actual executable, record window/API readiness timing, and terminate all test processes.
- [x] Verify final artifact path and SHA-256: `dist/XiaoQiBao-Portable/xiaoqibao.exe`.
