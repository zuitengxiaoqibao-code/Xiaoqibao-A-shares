# External Source Capability Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Detect each configured TickFlow and Tushare capability independently and show unavailable capabilities with a clear strike-through state in 数据设置.

**Architecture:** Keep the existing source definitions and credential boundary, add a persisted per-capability probe result beside the aggregate source status, and use documented read-only endpoints for each capability. The web card keeps the compact capability list but decorates each item from the probe result; unknown or unverified protocols remain visibly unverified rather than being claimed as available.

**Tech Stack:** Python, urllib, FastAPI/Pydantic, React/TypeScript, CSS, pytest, Vitest, Vite, PyInstaller.

## Global Constraints

- Preserve Chinese source text as UTF-8 and use `apply_patch` for manual edits.
- Never write API keys or tokens to logs, responses, tests, or durable memory.
- TickFlow and Tushare probes must use documented read-only endpoints; Fuyao remains unverified until its public contract is confirmed.
- A valid HTTP response with the documented response envelope proves endpoint access even when the returned data list is empty.
- HTTP 401/403 and provider permission messages become `limited`; network, malformed, and missing-endpoint failures become `unavailable`.
- Windows EXE is the only user-facing delivery; rebuild it after source changes and run the actual portable smoke test.

### Task 1: Capability Contract And Failing Tests

**Files:**
- Modify: `apps/api/src/qibao_api/external_sources.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/web/src/features/data-settings/types.ts`
- Test: `apps/api/tests/test_external_data_sources.py`
- Test: `apps/web/src/features/data-settings/ExternalDataSourceSection.test.tsx`

**Interfaces:**
- `ExternalCapabilityView` fields: `key`, `label`, `status`, `detail`, `reason_code`, `tested_at`.
- `ExternalDataSourceView.capability_checks` is an optional list for backward-compatible clients.

- [ ] Add a backend test that persists and returns independent capability results, including a limited capability.
- [ ] Add a backend test that a TickFlow probe calls the documented daily K-line endpoint in addition to real-time quotes.
- [ ] Add a frontend test that a limited capability renders its label with `text-decoration: line-through` semantics and an accessible reason.
- [ ] Run the focused tests and verify they fail because `capability_checks` and per-capability rendering do not exist.

### Task 2: Independent Backend Probes

**Files:**
- Modify: `apps/api/src/qibao_api/external_sources.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Test: `apps/api/tests/test_external_data_sources.py`

**Interfaces:**
- `ExternalDataSourceService.test(source_id)` returns aggregate status plus ordered `capability_checks`.
- Repository persists `capability_checks` under each source without persisting plaintext credentials in views.

- [ ] Add source-specific documented probe specifications for TickFlow (`quotes`, `klines`, `intraday`, `ex-factors`, `financials/metrics`, `depth`) and Tushare (`rt_k`, `daily`, `stk_mins`, `adj_factor`, `fina_indicator`).
- [ ] Implement response-envelope validation and permission/error classification without echoing credentials.
- [ ] Probe capabilities concurrently with bounded per-request timeout while preserving definition order in the response.
- [ ] Mark Fuyao capabilities `unverified` with a concise explanation rather than making unsupported calls.
- [ ] Aggregate status as `ready` when all probes pass, `limited` when any permission probe is limited, `unavailable` when probes fail for other reasons, and `configured` when no capability can yet be verified.
- [ ] Run backend focused tests until green.

### Task 3: Capability Status UI

**Files:**
- Modify: `apps/web/src/features/data-settings/ExternalDataSourceSection.tsx`
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/data-settings/ExternalDataSourceSection.test.tsx`

**Interfaces:**
- Capability tags expose `data-status` and a title/accessible description containing the probe detail.
- `limited` and `unavailable` tags use strike-through and subdued styling; `ready` tags retain normal styling; `unverified` tags remain muted without being falsely marked ready.

- [ ] Render persisted capability checks in definition order with compact Chinese status text.
- [ ] Add a short capability summary showing how many items were tested and explain that struck-through items cannot be called.
- [ ] Preserve key masking, save/test/clear actions, and existing aggregate status messages.
- [ ] Add CSS for strike-through, muted unavailable states, and mobile wrapping.
- [ ] Run frontend focused tests and production build.

### Task 4: Release Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-09-04-external-source-capability-probe.md`
- Modify: `C:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

- [ ] Run backend and frontend full test suites, UTF-8/mojibake scan, and `git diff --check`.
- [ ] Force-stop any existing `xiaoqibao.exe`, run `scripts/build-portable.ps1`, preserving persistent directories.
- [ ] Run `scripts/run-portable-smoke.ps1` against the rebuilt release and verify no exit residue.
- [ ] Record the final EXE hash and exact test evidence in project memory without credentials.
- [ ] Run the Vault validator from the Vault working directory.
