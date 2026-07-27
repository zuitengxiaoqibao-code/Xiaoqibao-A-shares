# Kronos Forecast Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional Kronos OHLCV forecast evidence layer to the first-limit-up quant dashboard without changing existing rule, sentiment, backtest, risk, or trading behavior.

**Architecture:** Add a lazy, dependency-injected Kronos runtime behind a `KronosForecastService`. The service reads verified daily bars, returns explicit status-bearing forecast evidence, and exposes it through the existing first-limit-up router. The React dashboard loads the evidence independently and renders a fifth ECharts panel that remains honest when the optional model is unavailable.

**Tech Stack:** FastAPI, Pydantic v2, DuckDB daily bars, optional PyTorch + official Kronos repository, React, TypeScript, ECharts, Vitest.

## Global Constraints

- Kronos is an evidence source only; it must not emit buy, sell, or position commands.
- Do not auto-download model weights or block API startup on model loading.
- Missing dependencies, source code, weights, or history must produce an explicit non-ready status and no synthetic numbers.
- A-share daily data must remain point-in-time and use the existing `BarRepository`.
- Preserve Chinese UTF-8 source files; edit with `apply_patch` and scan for mojibake.
- Do not add simulated funds, broker connectivity, or automatic order execution.

---

### Task 1: Define the forecast contract and deterministic summary math

**Files:**
- Create: `apps/api/src/qibao_api/contracts/kronos_forecast.py`
- Create: `apps/api/tests/contracts/test_kronos_forecast.py`
- Create: `apps/api/tests/a_shares/test_kronos_forecast_math.py`

**Interfaces:**
- `KronosForecastStatus = Literal["ready", "unavailable", "insufficient", "error"]`.
- `KronosForecastPoint(trade_date, median_close, lower_close, upper_close)`.
- `KronosForecastSummary(median_return_pct, upper_return_pct, lower_return_pct, path_dispersion_pct, downside_probability_pct)`.
- `KronosForecastResponse(status, symbol, as_of, observed_through, model, frequency, lookback_bars, horizon_bars, sample_count, summary, points, reasons, sources, warnings)`.
- `summarize_forecast_paths(last_close, future_dates, paths) -> tuple[KronosForecastPoint, KronosForecastSummary]`.

- [ ] **Step 1: Write failing tests** for valid quantile aggregation, empty paths, mismatched path lengths, and response status validation.
- [ ] **Step 2: Run the focused tests and verify they fail for missing contract/math symbols.**
- [ ] **Step 3: Implement the minimal Pydantic models and Decimal-safe summary math.**
- [ ] **Step 4: Re-run the focused tests and verify they pass without `NaN` or `Infinity`.**

### Task 2: Add optional Kronos runtime and service

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/kronos_forecast.py`
- Create: `apps/api/src/qibao_api/a_shares/kronos_runtime.py`
- Modify: `apps/api/src/qibao_api/settings.py`
- Create: `apps/api/tests/a_shares/test_kronos_forecast_service.py`
- Create: `apps/api/tests/a_shares/test_kronos_runtime.py`

**Interfaces:**
- `KronosPathPredictor.predict_paths(bars, future_dates, sample_count) -> list[list[Decimal]]`.
- `KronosForecastService.forecast(symbol, as_of, horizon) -> KronosForecastResponse`.
- `LazyKronosRuntime.predict_paths(...)` lazily imports the configured official Kronos source and raises typed unavailable errors when configuration or dependencies are absent.

- [ ] **Step 1: Write failing service tests** for insufficient history, missing runtime, successful fake-path summarization, and runtime exception isolation.
- [ ] **Step 2: Run the tests and verify the expected failures.**
- [ ] **Step 3: Implement settings fields for `kronos_enabled`, `kronos_repo_path`, model/tokenizer names, device, lookback, and sample count with safe defaults.**
- [ ] **Step 4: Implement the lazy runtime adapter using the official `model` package only when requested; never import Torch at module import time.**
- [ ] **Step 5: Implement the service using `BarRepository.latest`, the existing trading calendar, and `asyncio.to_thread` for blocking inference.**
- [ ] **Step 6: Re-run service and runtime tests and verify all four response states are covered.**

### Task 3: Expose the forecast through the FastAPI route

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/first_limit_up.py`
- Create: `apps/api/tests/routes/test_kronos_forecast.py`

**Interfaces:**
- `get_kronos_forecast_service(request) -> KronosForecastService`.
- `GET /api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&as_of=YYYY-MM-DD&horizon=20`.

- [ ] **Step 1: Write failing route tests** for valid unavailable response, invalid symbol, future date, horizon bounds, and ready fake service response.
- [ ] **Step 2: Run the route tests and verify the expected failures.**
- [ ] **Step 3: Wire the service in application lifespan after the trading calendar and bar repository are available.**
- [ ] **Step 4: Add route validation and map source/configuration failures to status-bearing JSON rather than opaque 500 errors.**
- [ ] **Step 5: Re-run route tests and the existing first-limit-up route tests.**

### Task 4: Add the frontend API types and forecast panel

**Files:**
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Create: `apps/web/src/features/quant-analysis/KronosForecastPanel.tsx`
- Create: `apps/web/src/features/quant-analysis/KronosForecastPanel.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- `KronosForecastResponse` mirrors the API contract with string numeric fields.
- `QuantForecastLoader(symbol, asOf, horizon) -> Promise<KronosForecastResponse>`.
- `KronosForecastPanel({ forecast, loading, error })` renders ready/unavailable/insufficient/error states and an ECharts path chart only for ready data.

- [ ] **Step 1: Write failing component tests** for ready interval chart, unavailable configuration guidance, insufficient history, error isolation, and no synthetic values.
- [ ] **Step 2: Run the tests and verify they fail because the panel and loader do not exist.**
- [ ] **Step 3: Implement API types/loader and the panel using the existing quant colors and ECharts wrapper.**
- [ ] **Step 4: Load the forecast when the selected candidate changes without clearing the other four evidence panels.**
- [ ] **Step 5: Wire `loadQuantForecast` through `App` and `Dashboard`, then add responsive styles and keyboard-visible focus.**
- [ ] **Step 6: Re-run focused frontend tests and verify no `NaN`, `Infinity`, or hidden fake chart is rendered.**

### Task 5: Verification and operational handoff

**Files:**
- Modify: `apps/api/pyproject.toml` only if an optional dependency group is needed.
- Modify: `README.md` with Kronos setup and honest data-state guidance.
- Create: `docs/superpowers/plans/2026-07-27-kronos-forecast-evidence.md` (this plan).

- [ ] **Step 1: Run the API focused and full test suites from `apps/api`.**
- [ ] **Step 2: Run the quant-analysis frontend tests and Web full build.**
- [ ] **Step 3: Run `git diff --check` and a targeted UTF-8/mojibake scan.**
- [ ] **Step 4: Start the local API and query the forecast route with the current database; verify the response is explicitly `unavailable` or `insufficient` until Kronos is configured, never an empty ambiguous payload.**
- [ ] **Step 5: Document the exact optional setup: clone Kronos, install its requirements, configure `QIBAO_KRONOS_REPO_PATH`, and provide local model names.**

