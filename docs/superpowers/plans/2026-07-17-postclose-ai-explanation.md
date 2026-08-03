# Postclose AI Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional AI explanations to deterministic postclose outcomes while preserving all frozen decisions and append-only history.

**Architecture:** `PostcloseReviewService` computes outcomes and derived advice first, then sends one evidence-bound `DecisionAIRequest` through the existing reloadable synchronous gateway. Public AI configuration identity participates in input hashing; production premarket and postclose services share one gateway.

**Tech Stack:** Python 3.12, Pydantic 2, httpx, pytest.

## Global Constraints

- Deterministic code exclusively controls outcome status, attribution, next-day observations, action, confidence, values, and gates.
- AI output only appends explanatory text to the existing deterministic explanation.
- Never include the API key in prompts, models, logs, errors, configuration identity, or hashes.
- Keep snapshots append-only and preserve the dirty worktree without commit or push.
- Edit Chinese files with `apply_patch`; run strict UTF-8 and mojibake scans.

---

### Task 1: Postclose AI Behavior

**Files:**
- Modify: `apps/api/src/qibao_api/zhongshu/postclose_review.py`
- Test: `apps/api/tests/zhongshu/test_postclose_review.py`

**Interfaces:**
- Consumes: `DecisionAIRequest`, `DecisionAIEvidence`, and optional gateway `configuration_identity()` / `explain()`.
- Produces: postclose `DecisionCycleSnapshot.ai_status` values `ready`, `unavailable`, or `not_requested`.

- [ ] Add failing tests proving ready AI appends text without changing deterministic fields, unavailable AI preserves deterministic text, empty reviews do not call AI, and configuration changes append a new snapshot.
- [ ] Run the postclose tests and verify expected failures.
- [ ] Add public AI identity to canonical input, build a single frozen request, apply safe metadata, and set `ai_status` without altering data quality.
- [ ] Re-run the postclose tests and confirm they pass.

### Task 2: Shared Production Gateway

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: one `ReloadableDecisionAIGateway` instance shared by `PremarketDecisionService` and `PostcloseReviewService`.

- [ ] Add a failing lifespan assertion that premarket and postclose reference the same gateway and shared resolver/client.
- [ ] Run the lifespan test and verify the missing postclose wiring fails.
- [ ] Construct the gateway once and inject it into both services.
- [ ] Re-run focused lifecycle and phase tests.

### Task 3: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`

- [ ] Document postclose AI as optional explanation over deterministic outcomes.
- [ ] Run all API tests, Ruff, all Web tests, and the production build.
- [ ] Run strict UTF-8 decoding, mojibake scan, and `git diff --check`.
- [ ] Restart the API and verify the real configured or unconfigured state without fake credentials.
