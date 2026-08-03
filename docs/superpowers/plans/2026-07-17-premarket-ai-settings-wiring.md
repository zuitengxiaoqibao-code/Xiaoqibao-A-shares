# Premarket AI Settings Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make saved OpenAI-compatible settings power premarket frozen-evidence explanations without restart or secret leakage.

**Architecture:** A synchronous reloadable decision gateway resolves local settings per explanation and delegates all output validation to `DecisionAIGateway`. A non-secret settings revision participates in the premarket input identity so explicit settings changes append a new immutable phase snapshot.

**Tech Stack:** Python 3.12, Pydantic 2, httpx, FastAPI, pytest.

## Global Constraints

- AI only explains frozen evidence and deterministic conclusions.
- AI cannot change actions, confidence, values, risk gates, or compliance gates.
- Never include the API key in prompts, representations, errors, models, revision tokens, or hashes.
- Preserve existing decision snapshots append-only.
- Preserve the dirty worktree and do not commit or push.
- Edit Chinese files with `apply_patch`; finish with strict UTF-8 and mojibake scans.

---

### Task 1: Non-Secret Local Settings Revision

**Files:**
- Modify: `apps/api/src/qibao_api/settings_repository.py`
- Test: `apps/api/tests/test_settings_repository.py`

**Interfaces:**
- Produces: `AISettingsRepository.revision() -> str | None`.
- Changes: `AISettingsRepository.save(settings)` persists a fresh random revision token beside the three secret settings fields.

- [ ] Add failing tests proving each save rotates a valid revision while `load()` still returns the same `AISettings` and the revision never contains the key.
- [ ] Run the settings repository tests and verify the missing method fails.
- [ ] Implement revision persistence and tolerant reading of legacy files without a revision.
- [ ] Re-run the settings tests and confirm they pass.

### Task 2: Reloadable Synchronous Decision Gateway

**Files:**
- Modify: `apps/api/src/qibao_api/zhongshu/decision_ai.py`
- Test: `apps/api/tests/zhongshu/test_decision_ai.py`

**Interfaces:**
- Produces: `OpenAICompatibleDecisionProvider.complete(request) -> str`.
- Produces: `ReloadableDecisionAIGateway.explain(request) -> DecisionAIResult`.
- Produces: `ReloadableDecisionAIGateway.configuration_identity() -> tuple[str, ...]`.

- [ ] Add failing tests for unconfigured zero-request behavior, saved settings without restart, JSON mode, model changes, frozen generated time, public identity changes, and secret-safe representations.
- [ ] Run the decision AI tests and verify failures are caused by missing classes.
- [ ] Implement the provider and reloadable gateway with the shared `httpx.Client` pattern.
- [ ] Re-run the decision AI tests and confirm they pass.

### Task 3: Premarket Snapshot Upgrade And Production Wiring

**Files:**
- Modify: `apps/api/src/qibao_api/zhongshu/premarket_decision.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/zhongshu/test_premarket_decision.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Consumes: `configuration_identity()` from Task 2.
- Production wiring uses `application.state.effective_ai_settings` and the lifespan `httpx.Client`.

- [ ] Add a failing premarket test proving a configuration identity change appends a new ready snapshot without changing deterministic action or confidence.
- [ ] Add a failing lifespan assertion for `ReloadableDecisionAIGateway` and the shared resolver/client.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Add the public AI identity to the canonical premarket input and replace the fixed unavailable provider in `main.py`.
- [ ] Re-run all focused tests and confirm they pass.

### Task 4: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`

- [ ] Document that saved settings power single-stock, news, and premarket explanations without restart; postclose AI remains a later slice.
- [ ] Run all API tests, Ruff, all Web tests, and the production build.
- [ ] Run strict UTF-8 decoding, mojibake scan, and `git diff --check`.
- [ ] Restart the API and verify real configured or unconfigured behavior without injecting fake credentials.
