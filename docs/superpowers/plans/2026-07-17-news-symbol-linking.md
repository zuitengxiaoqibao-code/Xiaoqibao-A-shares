# News Symbol Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已验证的个股新闻查询上下文接入确定性链接器，使个股新闻可进入盘前研判和单股证据，同时保持全市场新闻隔离。

**Architecture:** 在链接器增加可选的单股上下文参数；摄取服务只在 `sync_symbol` 路径传入已验证 A 股代码。仓储继续使用不可变原始事件和幂等有效修正，所有确定性消费者继续读取有效事件视图。

**Tech Stack:** Python 3.12、Pydantic 2、SQLite、pytest。

## Global Constraints

- 不更新、不删除或重建现有新闻事件和运行时数据库。
- 只有关联标的、行业、主题、关联置信度和复核状态允许系统修正。
- 全市场同步不使用个股上下文。
- AI 不参与关联，不改变确定性行动、数字或风控门禁。
- 中文文件只用 `apply_patch` 修改，完成后运行乱码扫描。

---

### Task 1: 链接器支持受限上下文

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/news_linking.py`
- Test: `apps/api/tests/gongbu/test_news_linking.py`

- [x] Add a failing test showing a valid A-share context links a title without a six-digit code at confidence `0.85` and leaves an empty context unchanged.
- [x] Run `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_news_linking.py -q` and confirm the new test fails because `link` has no context parameter.
- [x] Add `context_instruments: tuple[tuple[AssetKind, str], ...] = ()` to `link`, validate each context instrument, and merge it after explicit article matches. Use `Decimal("0.85")` only when the context contributes an instrument and no explicit association exists; keep explicit association at `1`.
- [x] Re-run the focused linker tests and confirm they pass.

### Task 2: 个股摄取传递上下文

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/news_ingestion.py`
- Test: `apps/api/tests/gongbu/test_news_ingestion.py`

- [x] Add a failing async ingestion test where the stock source returns an article without a code and `sync_symbol("600519")` produces a verified effective event for `600519`.
- [x] Run the focused ingestion test and confirm it fails because `_ingest` does not receive the symbol context.
- [x] Add an optional `context_instruments` parameter to `_ingest`; pass `((AssetKind.A_SHARE, symbol),)` only from `sync_symbol`, and pass no context from global `sync`. Keep append, reconcile and AI behavior unchanged.
- [x] Re-run linker and ingestion tests, including idempotent repeat sync.

### Task 3: Evidence consumer regression

**Files:**
- Modify: `apps/api/tests/a_shares/test_preparation_review.py`
- Modify: `apps/api/tests/a_shares/test_diagnosis.py`
- Modify: `apps/api/tests/zhongshu/test_premarket_decision.py`

- [x] Add assertions that the context-linked event is returned by `effective_events_for_symbol`, appears in the news preparation source, and is eligible for the verified premarket event set.
- [x] Run the focused consumer tests and confirm no raw `events_for_symbol` path is used by deterministic consumers.

### Task 4: Documentation and production verification

**Files:**
- Modify: `docs/roadmap.md`

- [x] Add the delivered context-linking behavior to the current-delivery list.
- [x] Run backend tests, Ruff, frontend tests, production build, UTF-8/mojibake scan and `git diff --check`.
- [x] Restart or reuse local services; run a real `sync_symbol`/news preparation smoke check for `600519`, verify the event is source-linked and no simulation route appears.
- [x] Browser-check the A 股 news and stock cockpit pages at desktop and 390x844, including console errors and overflow.
