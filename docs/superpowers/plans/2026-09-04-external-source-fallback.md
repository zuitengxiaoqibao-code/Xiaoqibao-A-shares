# External Source Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Make configured TickFlow and Tushare sources participate in real-time market quote fallback without exposing credentials or inventing unsupported Fuyao capabilities.

**Architecture:** Add a small synchronous quote-source adapter layer that implements the existing `TencentOverviewSource` shape (`fetch_indices`, `fetch_stocks`, `fetch_minutes` where supported). Compose it with the existing Tencent source so the primary source is attempted first and external sources are only attempted when the primary result is empty or raises. Keep source, observed time, and quality metadata from the upstream response.

**Tech Stack:** Python, httpx, Pydantic contracts, pytest, FastAPI lifespan wiring.

## Global Constraints

- Preserve Chinese source files as UTF-8 and use `apply_patch` for manual edits.
- Never write API keys or tokens to logs, responses, tests, or durable memory.
- TickFlow and Tushare are optional fallback sources; Tencent/local TDX remain primary.
- Fuyao remains configuration/test-only until its official endpoint contract is verified.
- Windows EXE remains the only user-facing delivery; rebuild it after source changes.

### Task 1: Unified External Quote Adapters

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/external_quote_sources.py`
- Test: `apps/api/tests/gongbu/test_external_quote_sources.py`

**Interfaces:**
- `ExternalQuoteSource.fetch_indices() -> tuple[tuple[OverviewIndexQuote, ...], tuple[str, ...]]`
- `ExternalQuoteSource.fetch_stocks(symbols) -> tuple[tuple[OverviewStockQuote, ...], tuple[str, ...]]`
- `ExternalQuoteFallbackSource` composes configured adapters and exposes the same methods.

- [ ] Write tests for TickFlow normalization, Tushare normalization, primary-first fallback, and unavailable unconfigured sources.
- [ ] Run the focused tests and observe expected failures.
- [ ] Implement the minimal adapters with bounded network timeouts and redacted errors.
- [ ] Run focused tests until green.

### Task 2: Lifespan Wiring

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/routes/test_market_overview.py`

- [ ] Add a regression test proving the market overview source is composed with enabled configured external sources.
- [ ] Wire repository-backed key lookup into the adapter factory without returning credentials.
- [ ] Verify existing market overview tests remain green.

### Task 3: Long-Task Smoke Reliability

**Files:**
- Modify: `scripts/run-portable-smoke.ps1`
- Test: `apps/api/tests/desktop/test_packaging.py`

- [ ] Add a smoke-script assertion that the quant strategy poll uses a long-operation timeout and does not hard-cancel at 10 seconds.
- [ ] Replace the single 10-second poll timeout with condition-based polling up to the existing smoke budget.
- [ ] Run packaging tests and the portable smoke script.

### Task 4: Full Verification and Release

- [ ] Run Web/API tests, production build, UTF-8/garbled-text scan, and `git diff --check`.
- [ ] Force-stop `xiaoqibao.exe`, run `scripts/build-portable.ps1`, and preserve persistent directories.
- [ ] Run `scripts/run-portable-smoke.ps1 -UseReleaseData`; record any environmental data-source limitations precisely.
- [ ] Update the project memory with confirmed results, excluding credentials.
