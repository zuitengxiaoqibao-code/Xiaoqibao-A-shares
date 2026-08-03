# News AI Settings Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make saved OpenAI-compatible settings power news interpretation without restart, progressively upgrade fetched degraded events, and synchronize the currently selected A-share from the news page.

**Architecture:** A reloadable news gateway resolves the existing local settings for each interpretation and delegates schema and citation validation to `NewsAIGateway`. Ingestion appends at most ten missing current-model interpretations per sync. A symbol-specific route and frontend argument carry the selected A-share into the existing stock-news path.

**Tech Stack:** Python 3.12, Pydantic 2, httpx, FastAPI, pytest, React 19, TypeScript 5.8, Vitest.

## Global Constraints

- Do not update or delete existing articles, events, corrections, interpretations, or runtime databases.
- AI may explain frozen citations only; it cannot change actions, confidence, numbers, or risk gates.
- Never serialize, log, persist, or include the API key in prompts or hashes.
- Generate at most 10 AI interpretations in one news sync.
- Keep A-share symbol sync isolated from the convertible-bond domain.
- Edit Chinese files with `apply_patch`; run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree and do not commit or push.

---

### Task 1: Reloadable OpenAI-Compatible News Gateway

**Files:**
- Modify: `apps/api/src/qibao_api/zhongshu/news_ai.py`
- Test: `apps/api/tests/zhongshu/test_news_ai_gateway.py`

**Interfaces:**
- Produces: `OpenAICompatibleNewsProvider.complete(request: dict) -> Awaitable[str]`.
- Produces: `ReloadableNewsAIGateway.interpret(event) -> Awaitable[AIInterpretation]`.
- Produces: `ReloadableNewsAIGateway.needs_interpretation(event_id, interpretations) -> bool`.

- [ ] Add failing tests proving unconfigured settings create no HTTP request, saved settings are read without restart, the OpenAI request uses strict JSON mode, and a model change requires a new interpretation.
- [ ] Run `apps\api\.venv\Scripts\python.exe -m pytest apps\api\tests\zhongshu\test_news_ai_gateway.py -q` and verify failures are caused by missing reloadable classes.
- [ ] Implement the provider and reloadable gateway using `EffectiveAISettingsResolver`, the shared `httpx.AsyncClient`, current citation validation, and secret-safe representations.
- [ ] Re-run the focused gateway tests and confirm they pass.

### Task 2: Append-Only Interpretation Upgrade And Production Wiring

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/news_ingestion.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/gongbu/test_news_ingestion.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Consumes: `needs_interpretation(event_id, interpretations)` from Task 1.
- Produces: `NewsIngestionService(..., max_ai_interpretations_per_sync=10)`.

- [ ] Add failing ingestion tests proving a refetched event with only a degraded interpretation receives one appended ready interpretation, a third sync is idempotent, and no more than ten interpretations are generated per sync.
- [ ] Add a failing lifespan assertion that production news ingestion uses `ReloadableNewsAIGateway` backed by `application.state.effective_ai_settings`.
- [ ] Run the focused ingestion and lifespan tests and confirm the expected failures.
- [ ] Implement bounded upgrade selection without modifying prior rows, and replace the fixed unavailable gateway in `main.py`.
- [ ] Re-run the focused backend tests and confirm they pass.

### Task 3: Selected A-Share News Synchronization

**Files:**
- Modify: `apps/api/src/qibao_api/routes/news.py`
- Modify: `apps/api/tests/routes/test_news.py`
- Modify: `apps/web/src/features/news-intelligence/api.ts`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`

**Interfaces:**
- Produces: `POST /api/v1/news/sync/{symbol}`.
- Produces: `syncNews(symbol?: string | null): Promise<Record<string, number>>`.

- [ ] Add a failing route test that `600519` delegates to `sync_symbol("600519")` and preserves the existing authorization/error mapping.
- [ ] Add a failing component test that the sync button passes `selectedSymbol`, while the unselected view passes no symbol.
- [ ] Run the focused backend and frontend tests and verify the missing route and argument failures.
- [ ] Implement the route, API URL selection, prop signatures, and selected-symbol call.
- [ ] Re-run the focused tests and confirm they pass.

### Task 4: Documentation And Production Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- Documents the actual AI coverage and append-only upgrade behavior.

- [ ] Update documentation to state that saved AI settings power both the single-stock action card and newly synchronized news explanations, with deterministic degradation when unavailable.
- [ ] Run all API tests, Ruff, all Web tests, and the production build.
- [ ] Run strict UTF-8 decoding and mojibake scans over every changed text file, then run `git diff --check`.
- [ ] Restart the API and inspect AI settings plus news quality. Do not create a fake local provider configuration; verify configured or unconfigured behavior according to the real environment.
- [ ] Browser-check the selected-stock news sync, event explanation state, console messages, and horizontal overflow. Keep the A-share page available for handoff.
