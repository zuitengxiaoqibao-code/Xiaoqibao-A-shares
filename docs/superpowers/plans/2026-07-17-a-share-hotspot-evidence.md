# A-Share Intraday Hotspot Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-grade, auditable A-share intraday hotspot source whose frozen theme evidence reaches the existing decision and beginner news workflows.

**Architecture:** Parse the public Tonghuashun strong-stock feed into typed hotspot observations, then append deterministic `market_hotspot` articles and events to the existing news evidence repository. Keep authorization, scheduled refresh jobs and UI errors isolated from Eastmoney news and from quote polling.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, httpx, SQLite, pytest, React 19, TypeScript 5, Vitest.

## Global Constraints

- A shares remain primary; convertible bonds never consume or display A-share hotspot events.
- The source exposes only code, name, date and reason tags; never invent price, turnover or amount fields.
- AI may explain frozen events but cannot change action, confidence, risk gates or deterministic fields.
- `market_hotspots` / `tonghuashun` authorization is independent from `market_news` / `eastmoney`.
- Scheduled hotspot failure is audited but must not block briefing or decision execution.
- Edit Chinese files with `apply_patch`, then run strict UTF-8 and mojibake scans.
- Preserve the dirty worktree; do not stage, commit, push, reset or revert unrelated work.

---

### Task 1: Parse and Persist Frozen Hotspot Evidence

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/hotspot.py`
- Create: `apps/api/tests/gongbu/test_hotspot.py`
- Modify: `apps/api/src/qibao_api/gongbu/news_repository.py`

**Interfaces:**
- Consumes: `TonghuashunHotspotSource.fetch(trading_date, fetched_at)` and the public JSON response.
- Produces: `HotspotObservation` tuples and `HotspotSyncResult` with fetched, inserted, clusters and events counts.

- [x] **Step 1: Write failing parser, transport and ingestion tests**

Cover UTF-8 BOM, strict GBK fallback, upstream error codes, invalid rows, exact request path, one retry for transient failures, authorization, raw snapshot preservation, idempotent replay and changed-reason append semantics.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_hotspot.py -q`

Expected: import failure because the hotspot module does not exist.

- [x] **Step 3: Implement typed parsing and append-only ingestion**

Create frozen models with validated A-share symbols and aware timestamps. Decode UTF-8-SIG first and GBK second with strict errors, reject nonzero `errocode`, and create source article/event IDs from trading date, symbol and semantic reason hash. Reuse `append_articles`, `append_cluster` and `reconcile_event`; never update existing rows.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Task 1 command and require all tests to pass.

### Task 2: Expose Authorization-Safe API and Runtime Wiring

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/news.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/tests/routes/test_news.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Consumes: `HotspotIngestionService.sync(trading_date, fetched_at)`.
- Produces: `POST /api/v1/news/hotspots/sync?trading_date=YYYY-MM-DD` and `application.state.hotspot_service`.

- [x] **Step 1: Write failing route and lifespan tests**

Assert default China-date resolution, explicit date forwarding, 403 authorization mapping, 422 future/non-trading-day validation, 503 upstream mapping, the `market_hotspots` source dependency and shared repository/client wiring.

- [x] **Step 2: Run focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_news.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`

Expected: missing dependency, route and application state failures.

- [x] **Step 3: Implement route, compliance registration and lifecycle wiring**

Register `market_hotspots` for A shares with source `tonghuashun`, construct the source from the existing synchronous `history_client`, and always use the stored trading calendar for date validation.

- [x] **Step 4: Re-run focused tests and verify GREEN**

Run the Task 2 command and require all tests to pass.

### Task 3: Refresh Hotspots Before Scheduled Intraday Decisions

**Files:**
- Modify: `apps/api/src/qibao_api/shangshu/scheduler.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/tests/shangshu/test_scheduler.py`

**Interfaces:**
- Consumes: optional synchronous `hotspot_service` passed to `DailyBriefingScheduler`.
- Produces: audited `{date}:intraday:{slot}:hotspots` operation jobs.

- [x] **Step 1: Write failing ordering, retry and isolation tests**

Prove 10:30/13:30/14:30 hotspot sync happens before the matching decision, a successful job is not repeated after restart, failures retry up to the scheduler limit, hotspot failure does not block briefing/decision, manual intraday runs refresh first, and background quote polling never calls hotspots.

- [x] **Step 2: Run the scheduler tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest apps/api/tests/shangshu/test_scheduler.py -q`

Expected: the scheduler does not accept or invoke a hotspot service.

- [x] **Step 3: Implement a separate audited hotspot job**

Run the hotspot job before `_run` for fixed intraday slots and before manual intraday execution. Store started/completed/failed attempts independently; return no exception to the briefing/decision path after a hotspot failure.

- [x] **Step 4: Re-run scheduler tests and verify GREEN**

Run the Task 3 command and require all tests to pass.

### Task 4: Add Beginner Hotspot Controls and Event Copy

**Files:**
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/news-intelligence/api.ts`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.tsx`
- Modify: `apps/web/src/features/news-intelligence/NewsIntelligenceView.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Consumes: the hotspot sync API and existing `NewsEvent` bundle.
- Produces: an independent “同步热点” action, beginner event labels and verified hotspot count.

- [x] **Step 1: Write failing component tests**

Assert the independent sync command, partial error preservation, `market_hotspot` to “题材热点” copy, source/time/tags, no fabricated quote metrics, hotspot count and “同花顺热点” compliance name.

- [x] **Step 2: Run the component tests and verify RED**

Run: `pnpm --filter @qibao/web test -- NewsIntelligenceView.test.tsx DataSettingsView.test.tsx`

Expected: missing prop, command and beginner copy assertions fail.

- [x] **Step 3: Implement API wiring and restrained UI changes**

Keep news and hotspot loading states separate, retain loaded bundle data after hotspot failure, and use the existing event timeline instead of adding a second nested card surface.

- [x] **Step 4: Re-run component tests and verify GREEN**

Run the Task 4 command and require all tests to pass.

### Task 5: Production Verification and Roadmap Record

**Files:**
- Modify: `docs/roadmap.md`
- Verify: all changed files and running application.

**Interfaces:**
- Consumes: completed Tasks 1-4.
- Produces: test, encoding, live-source and browser evidence.

- [x] **Step 1: Run full automated checks**

Run API tests, Ruff, Web tests and the production build using the repository-standard commands.

- [x] **Step 2: Run encoding and diff gates**

Strictly decode every changed text file as UTF-8, scan source and changed Chinese docs for repeated question marks, replacement characters, private-use characters and common mojibake markers, then run `git diff --check`.

- [x] **Step 3: Verify the live source and application**

Confirm a real trading-date response parses without fabricated fields. Verify unauthorized API behavior without mutating user authorization; if already authorized, verify one real sync and idempotent replay. At desktop and 390x844 verify independent controls, event labels, no console errors, no dialogs and no page-level overflow.

- [x] **Step 4: Update roadmap and verification record**

Record exact counts and runtime evidence. Do not claim completion until every gate passes.

## Verification Record

- Task 1 focused tests: `11 passed`.
- Task 2 route and lifespan tests: `11 passed`.
- Task 3 scheduler tests: `22 passed`.
- Task 4 component tests: `26 passed`.
- Full API suite: `751 passed, 1 skipped`; Ruff: all checks passed.
- Full Web suite: `159 passed`; TypeScript and Vite production build completed with 1614 transformed modules.
- Encoding gates: 111 changed text files decoded as strict UTF-8; 306 scoped source and changed documentation files produced zero mojibake matches; `git diff --check` passed.
- Live source: the 2026-07-17 Tonghuashun endpoint returned 35 valid observations. The typed result contained only source record, symbol, name, trading date, themes, observed/fetched timestamps, source and raw snapshot; post-close observation time capped at 15:00 China time.
- Running API: isolated application health returned 200; hotspot sync returned the expected independent 403 for missing `tonghuashun` authorization without changing user authorization.
- Browser acceptance: desktop 1440x900 and mobile 390x844 showed separate news/hotspot controls, no page-level overflow or dialogs; a clean tab produced no console warnings or errors. Mobile controls remained 44 pixels high and the quality view exposed the verified hotspot count.
