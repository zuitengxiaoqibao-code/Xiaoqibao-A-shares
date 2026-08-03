# Intraday AI Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one evidence-bound AI explanation call for each newly persisted ready intraday advice change while preserving deterministic decisions.

**Architecture:** `IntradayMonitor` detects and freezes deterministic advice changes first, then optionally sends the changed advice through the existing synchronous reloadable decision gateway. Production premarket, intraday, and postclose share one gateway; the frontend keeps its deterministic numeric formatting and appends the stored model supplement.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, React 19, TypeScript, Vitest.

## Global Constraints

- Deterministic code exclusively controls action, confidence, conclusion, evidence, risks, gates, values, and version creation.
- AI is called once only for a non-empty ready intraday change set.
- AI output only appends explanatory text and safe metadata.
- No model call for unchanged polling, blocked snapshots, or empty recovery snapshots.
- Never include the API key in requests, models, logs, hashes, or stored metadata.
- Preserve append-only history and the dirty worktree; do not commit or push.
- Edit Chinese files with `apply_patch`; run strict UTF-8 and mojibake scans.

---

### Task 1: Intraday AI Enrichment

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/intraday_monitor.py`
- Test: `apps/api/tests/shangshu/test_intraday_monitor.py`

**Interfaces:**
- Consumes: optional `ai_gateway.explain(DecisionAIRequest) -> DecisionAIResult`.
- Produces: ready intraday `AdviceCard` values with appended model text and `DecisionCycleSnapshot.ai_status`.

- [ ] Add tests for ready AI, unavailable AI, unchanged polling, blocked results, and inherited AI metadata removal.
- [ ] Run the focused tests and verify they fail because `IntradayMonitor` has no AI enrichment.
- [ ] Add optional `ai_gateway`, build one deduplicated frozen request after change detection, and apply only safe metadata.
- [ ] Keep deterministic `status` and `data_quality` unchanged when AI is unavailable.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Shared Production Gateway

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: one `ReloadableDecisionAIGateway` instance shared by all three decision phases.

- [ ] Add a failing lifecycle assertion that the intraday monitor uses the premarket/postclose gateway instance.
- [ ] Inject `decision_ai_gateway` into `IntradayMonitor`.
- [ ] Re-run lifecycle and intraday tests.

### Task 3: Beginner Explanation Preservation

**Files:**
- Modify: `apps/web/src/features/decision-workbench/explanation.ts`
- Test: `apps/web/src/features/decision-workbench/explanation.test.ts`

**Interfaces:**
- Produces: `beginnerAdviceExplanation()` output with rounded deterministic values followed by the stored `模型补充：` suffix.

- [ ] Add a failing test using a high-precision intraday percentage and an AI supplement.
- [ ] Preserve the suffix after rebuilding the deterministic sentence.
- [ ] Run the focused Web tests.

### Task 4: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`

- [ ] Document that all three phases use optional evidence-bound AI explanation and that intraday calls only occur on real advice changes.
- [ ] Run all API tests, Ruff, all Web tests, and the production build.
- [ ] Run strict UTF-8 decoding, mojibake scan, and `git diff --check`.
- [ ] Restart the API, confirm the real AI configuration state, and verify the A-share page has no alerts, console errors, 500s, or horizontal overflow.
