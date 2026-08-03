# Local Market Source Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed local terminal paths and the unconditional `17709` probe with validated, persistent, user-configurable local data-source discovery in the portable EXE.

**Architecture:** A focused settings repository owns `config/data-sources.json`; a Windows discovery service returns validated TDX/THS installations; startup resolves one active TDX `vipdoc` and creates an RPC client only when explicitly enabled. The existing settings page consumes three local API endpoints and keeps unsupported THS local data clearly labeled.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, React 19, TypeScript, Vitest, PyInstaller.

## Global Constraints

- The Windows desktop executable is the only user-facing delivery.
- Local TDX daily files have priority; unavailable sources must not produce simulated data.
- `tdx_rpc_enabled` defaults to `false`; no request to port `17709` is allowed while disabled.
- Settings live in `config/data-sources.json`; runtime caches remain under `cache`.
- Chinese files must be edited with `apply_patch` and checked for mojibake.
- Existing persistent directories must survive every portable rebuild.

---

### Task 1: Local Source Settings And Discovery

**Files:**
- Create: `apps/api/src/qibao_api/local_sources/models.py`
- Create: `apps/api/src/qibao_api/local_sources/repository.py`
- Create: `apps/api/src/qibao_api/local_sources/discovery.py`
- Create: `apps/api/tests/local_sources/test_repository.py`
- Create: `apps/api/tests/local_sources/test_discovery.py`

**Interfaces:**
- Produces: `LocalSourceSettings`, `LocalSourceSettingsRepository.load/save`, `LocalTerminalDiscovery.inspect`.
- Consumes: standard-library `pathlib`, `json`, `tempfile`, `winreg`, and `ctypes`; no new runtime dependency.

- [ ] **Step 1: Write failing model, repository, and discovery tests**

Cover default-disabled RPC, ordered path round-trip, atomic UTF-8 storage, invalid UNC rejection, direct/root `vipdoc` normalization, TDX file counts, and THS `detected_only` status.

- [ ] **Step 2: Run the focused tests and confirm missing-module failures**

Run: `uv run pytest tests/local_sources -q`

Expected: collection fails because `qibao_api.local_sources` does not exist.

- [ ] **Step 3: Implement the settings and discovery modules**

Use immutable Pydantic models, path deduplication with case-insensitive Windows keys, atomic `os.replace`, and injected process/registry candidates for deterministic tests.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest tests/local_sources -q`

Expected: all local-source tests pass.

### Task 2: Optional RPC And Startup Resolution

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_daily.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_desktop/entrypoint.py`
- Modify: `apps/api/tests/gongbu/test_tdx_local_overview.py`
- Modify: `apps/api/tests/gongbu/test_tdx_local_daily.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Consumes: `LocalSourceSettingsRepository`, `LocalTerminalDiscovery`, and `DiscoveryResult.active_tdx_vipdoc`.
- Produces: `application.state.local_source_settings_repository`, `application.state.local_terminal_discovery`, and an RPC-free default overview source.

- [ ] **Step 1: Write failing tests for disabled RPC and configured directory priority**

Assert that `LocalTdxOverviewSource(rpc=None)` calls its fallback without constructing or closing a JSON-RPC client, and that startup prefers the first valid manual TDX path.

- [ ] **Step 2: Run focused tests and confirm failures**

Run: `uv run pytest tests/gongbu/test_tdx_local_overview.py tests/gongbu/test_tdx_local_daily.py tests/libu_compliance/test_main_lifespan.py -q`

Expected: failures show unconditional RPC construction and fixed-path discovery.

- [ ] **Step 3: Implement optional RPC and settings-driven startup**

Remove hard-coded `D:/new_tdx_mock` and `C:/new_tdx_mock` candidates. Construct `TdxJsonRpcClient(endpoint=...)` only when the validated configuration enables it; otherwise pass no RPC and use fallback immediately.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2.

Expected: all focused tests pass.

### Task 3: Settings API

**Files:**
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/api/tests/routes/test_settings.py`

**Interfaces:**
- Consumes: repositories and discovery objects stored on `request.app.state`.
- Produces: `GET /data-sources`, `POST /data-sources/detect`, and `PUT /data-sources`.

- [ ] **Step 1: Write failing route tests**

Cover default response, manual TDX validation, explicit RPC URL validation, automatic detection without persistence, successful save, and 422 for invalid directories.

- [ ] **Step 2: Run route tests and confirm 404/validation failures**

Run: `uv run pytest tests/routes/test_settings.py -q`

Expected: new endpoints return 404 before implementation.

- [ ] **Step 3: Add dependency helpers, response models, and routes**

Return only normalized paths and health metadata; never expose filesystem exceptions or arbitrary file contents.

- [ ] **Step 4: Run route tests**

Run: `uv run pytest tests/routes/test_settings.py -q`

Expected: all settings route tests pass.

### Task 4: Desktop Settings Interface

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/terminal.css`

**Interfaces:**
- Consumes: the three settings API endpoints.
- Produces: typed loaders/savers and a responsive “本地行情软件” settings section.

- [ ] **Step 1: Write failing component tests**

Assert automatic discovery is enabled, the active TDX path and coverage are visible, paths can be added and removed, THS is labeled detected-only, RPC is collapsed/off by default, and save reports restart required.

- [ ] **Step 2: Run focused frontend tests and confirm failures**

Run: `pnpm test -- src/features/data-settings/DataSettingsView.test.tsx`

Expected: tests fail because local-source props and controls do not exist.

- [ ] **Step 3: Implement types, API clients, controls, and styling**

Use existing Lucide icons, compact terminal sections, standard text inputs, toggles, and explicit status colors. Do not add nested cards or browser-only delivery paths.

- [ ] **Step 4: Run focused and full frontend verification**

Run: `pnpm test` and `pnpm build` from `apps/web`.

Expected: all tests and production build pass.

### Task 5: Full Verification And Portable Delivery

**Files:**
- Modify: `README.md`
- Rebuild: `dist/XiaoQiBao-Portable/xiaoqibao.exe`

**Interfaces:**
- Consumes: completed API and Web behavior.
- Produces: verified portable EXE with preserved user data.

- [ ] **Step 1: Run API tests, lint, and mojibake scans**

Run API tests in the existing split groups, `uv run ruff check src tests`, and scan source files for replacement characters or repeated question marks.

- [ ] **Step 2: Stop only the current portable EXE and rebuild**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -SkipTests`

Expected: the build succeeds and persistent directory counts remain intact.

- [ ] **Step 3: Run portable smoke verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`

Expected: `Portable smoke passed`.

- [ ] **Step 4: Launch the final EXE and verify settings**

Open `dist/XiaoQiBao-Portable/xiaoqibao.exe`, confirm the local-source section detects the running `D:/new_tdx_mock` installation, and confirm no `17709` request occurs while RPC is disabled.
