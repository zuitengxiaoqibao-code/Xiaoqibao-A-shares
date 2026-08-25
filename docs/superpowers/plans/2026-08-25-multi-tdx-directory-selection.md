# 多通达信目录发现与日线主源选择实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 自动发现本机多个通达信安装目录，按真实日线完整度选择主源，并在主源缺口时从其他目录补读，避免误读不常用版本的旧数据。

**Architecture:** 新增独立的本地通达信目录发现服务，接收已知路径、进程路径、常见目录和用户配置路径，产出带扫描证据的候选目录列表。主源选择只依赖可验证的 `.day` 文件统计和最新交易日，读取层使用评分排序后的候选目录链进行逐股票回退；设置 API 与页面只展示扫描结果并保存用户覆盖，不把目录判断硬编码在前端。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、SQLite/JSON 配置、React/TypeScript、Vitest、Pytest、Windows EXE smoke。

## Global Constraints

- 保留并优先扫描 `D:\new_tdx_mock`，但不把它永久强制为主源；最终主源由真实数据评分决定。
- 不关闭、重启或控制通达信客户端；目录扫描只读文件系统和进程路径。
- 不删除或覆盖 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
- 所有用户可见状态、错误和目录说明使用中文；内部字段可以保持英文。
- 目录扫描必须后台执行，页面先显示缓存结果；不能阻塞 EXE 启动或首屏渲染。
- 日线读取必须记录来源目录和扫描时间，不能伪造最新交易日或覆盖率。

### Task 1: 目录候选模型与评分算法

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_directory_discovery.py`
- Test: `apps/api/tests/gongbu/test_tdx_directory_discovery.py`

**Interfaces:**
- Produces `TdxDirectoryCandidate`, `TdxDirectoryDiscovery`, `discover_tdx_directories()`, `rank_tdx_directories()`.
- `TdxDirectoryCandidate` exposes `root`, `vipdoc_path`, `display_name`, `version_hint`, `latest_trade_date`, `day_file_count`, `readable_day_file_count`, `a_share_coverage_percent`, `last_data_update`, `score`, `state`, `reasons`.

- [x] **Step 1: Write failing tests for candidate scoring and known-path discovery**

```python
def test_known_mock_directory_is_scanned_and_ranked_by_real_day_coverage(tmp_path):
    mock_root = tmp_path / "new_tdx_mock"
    vipdoc = mock_root / "vipdoc" / "sh" / "lday"
    vipdoc.mkdir(parents=True)
    (vipdoc / "sh600000.day").write_bytes(valid_day_bytes("20260825"))
    result = discover_tdx_directories(
        known_paths=(mock_root,),
        search_roots=(tmp_path,),
        universe_symbols=("600000",),
    )
    assert result.candidates[0].root == mock_root.resolve()
    assert result.candidates[0].latest_trade_date == date(2026, 8, 25)
    assert result.candidates[0].readable_day_file_count == 1
    assert result.candidates[0].a_share_coverage_percent == 100.0


def test_rank_prefers_newer_complete_directory_over_more_recent_but_incomplete(tmp_path):
    complete = candidate(tmp_path / "complete", latest="20260824", readable=2, universe=2)
    incomplete = candidate(tmp_path / "incomplete", latest="20260825", readable=1, universe=2)
    ranked = rank_tdx_directories((incomplete, complete))
    assert ranked[0].root == complete.root
    assert "覆盖率" in ranked[0].reasons[0] or "可读取" in ranked[0].reasons[0]
```

- [x] **Step 2: Run the focused tests and verify the expected RED failure**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_tdx_directory_discovery.py -q`

Expected: FAIL because the discovery module and scoring interfaces do not exist.

- [x] **Step 3: Implement bounded discovery and deterministic scoring**

Implement `discover_tdx_directories()` with these exact rules:

```python
KNOWN_TDX_PATHS = (Path(r"D:\new_tdx_mock"),)
MARKER_NAMES = {"vipdoc", "lday", "通达信", "new_tdx_mock"}

def discover_tdx_directories(
    *,
    known_paths: Sequence[Path] = KNOWN_TDX_PATHS,
    search_roots: Sequence[Path] = (),
    universe_symbols: Sequence[str] = (),
) -> TdxDirectoryDiscovery:
    # Probe explicit paths first, then bounded directory candidates at depth <= 4.
    # Never recurse through arbitrary files or follow symlinks.
    # For each vipdoc candidate, count only readable *.day files and inspect dates
    # from the fixed TDX_DAY_RECORD binary layout.
```

Compute `score` as `freshness_score * 0.40 + readable_coverage_score * 0.30 + universe_coverage_score * 0.20 + activity_score * 0.10`, clamp to `[0, 100]`, and sort by `(-score, -latest_trade_date, -readable_day_file_count, root_string)`.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_tdx_directory_discovery.py -q`

Expected: all discovery and scoring tests pass.

### Task 2: Settings API and persistent selection

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Modify: `apps/api/src/qibao_api/routes/settings.py`
- Modify: `apps/api/src/qibao_api/contracts/tdx_local.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Test: `apps/api/tests/routes/test_settings.py`

**Interfaces:**
- Adds `GET /api/v1/settings/tdx-directories` returning ranked candidates and active selection.
- Adds `POST /api/v1/settings/tdx-directories/scan` to start a background scan and return a scan job id.
- Adds `POST /api/v1/settings/tdx-directories/select` accepting `{ "root": "D:/new_tdx_mock" }` or `{ "root": null }` to restore automatic selection.

- [x] **Step 1: Write failing API tests**

```python
def test_tdx_directory_settings_returns_ranked_candidates_and_active_root(client):
    response = client.get("/api/v1/settings/tdx-directories")
    assert response.status_code == 200
    assert response.json()["active_mode"] == "auto"
    assert response.json()["candidates"][0]["root"] == "D:/new_tdx_mock"
    assert response.json()["candidates"][0]["score"] <= 100


def test_select_tdx_directory_persists_manual_override(client):
    response = client.post(
        "/api/v1/settings/tdx-directories/select",
        json={"root": "D:/new_tdx_mock"},
    )
    assert response.status_code == 200
    assert response.json()["active_mode"] == "manual"
    assert response.json()["active_root"] == "D:/new_tdx_mock"
```

- [x] **Step 2: Run tests and verify RED**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_settings.py -q`

Expected: FAIL because the new settings routes and response contracts are absent.

- [x] **Step 3: Implement cached discovery state and selection persistence**

Persist only the selected root and last discovery snapshot in the existing settings storage. Use a background executor for scans, return the previous snapshot while a scan is running, and mark state as `scanning`, `ready`, `partial`, or `unavailable` with Chinese `message` and `reasons`.

- [x] **Step 4: Run API tests and verify GREEN**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/routes/test_settings.py -q`

Expected: settings discovery, scan status, selection persistence, invalid-path and stale-cache tests pass.

### Task 3: Multi-directory daily-bar read fallback

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_import.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_daily.py`
- Modify: `apps/api/src/qibao_api/gongbu/full_market_history.py`
- Test: `apps/api/tests/gongbu/test_tdx_local_import.py`
- Test: `apps/api/tests/gongbu/test_full_market_history.py`

**Interfaces:**
- `TdxLocalImportService` consumes the ranked directory chain and exposes `selected_root` plus per-file `source_root`.
- Full-market history uses the active primary directory first and tries lower-ranked candidates only for missing or stale symbols.

- [x] **Step 1: Write failing fallback tests**

```python
def test_local_daily_read_uses_second_directory_for_missing_symbol(tmp_path):
    primary = make_tdx_root(tmp_path / "primary", {"600000": bars("600000", 300)})
    secondary = make_tdx_root(tmp_path / "secondary", {"000001": bars("000001", 300)})
    service = make_import_service((primary, secondary))
    result = service.read_symbol("000001")
    assert result.source_root == secondary.resolve()
    assert len(result.bars) == 300
```

- [x] **Step 2: Run fallback tests and verify RED**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_tdx_local_import.py apps/api/tests/gongbu/test_full_market_history.py -q`

Expected: FAIL because reads use only one directory.

- [x] **Step 3: Implement ordered fallback without duplicate writes**

Use the ranked candidate list for reads. For each symbol, accept the first source whose latest bar is at least the requested target date; otherwise keep the newest verified source and expose the gap. Never merge conflicting rows silently: prefer the higher-ranked source for duplicate dates and record the rejected source in lineage.

- [x] **Step 4: Run fallback tests and verify GREEN**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_tdx_local_import.py apps/api/tests/gongbu/test_full_market_history.py -q`

Expected: fallback, duplicate precedence, stale-source and provenance tests pass.

### Task 4: Data Settings UI for candidate directories

**Files:**
- Modify: `apps/web/src/features/data-settings/types.ts`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/api.ts`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`

**Interfaces:**
- Renders a compact “通达信日线目录” panel with auto/manual mode, scan status, ranked cards, and active-source badge.
- Actions call the settings API; while scanning, retain the previous complete snapshot and show current scan progress.

- [x] **Step 1: Write failing UI tests**

```tsx
test("shows the recommended mock directory and manual selection action", async () => {
  render(<DataSettingsView {...propsWithTdxCandidates()} />);
  expect(await screen.findByText("D:\\new_tdx_mock")).toBeInTheDocument();
  expect(screen.getByText("推荐主源")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "设为主源" }));
  expect(selectDirectory).toHaveBeenCalledWith("D:/new_tdx_mock");
});
```

- [x] **Step 2: Run UI tests and verify RED**

Run: `pnpm --dir apps/web exec vitest run src/features/data-settings/DataSettingsView.test.tsx`

Expected: FAIL because the directory candidate panel and actions are absent.

- [x] **Step 3: Implement compact cards, status colors, and cached scan states**

Use Chinese labels, red/green stock semantics only for data direction, blue/cyan for source status, and an emphasized badge for the active source. Keep all cards in a responsive grid without adding a new menu level.

- [x] **Step 4: Run UI tests and production build**

Run: `pnpm --dir apps/web exec vitest run src/features/data-settings/DataSettingsView.test.tsx` and `pnpm --dir apps/web build`.

Expected: focused tests and TypeScript/Vite production build pass.

### Task 5: Integration verification and EXE delivery

**Files:**
- Modify: `apps/api/tests/routes/test_operations.py` if operations status needs discovery evidence.
- Modify: `docs/verification/2026-08-25-multi-tdx-directory-selection.md`

- [x] **Step 1: Run API and Web full suites**

Run: `\.venv\Scripts\python.exe -m pytest apps/api/tests -q` and `pnpm --dir apps/web exec vitest run --maxWorkers=2`.

Expected: zero failures; real data remains `partial` or `unavailable` where evidence is missing.

- [x] **Step 2: Build the portable EXE**

Run: `cmd /c powershell.exe -ExecutionPolicy Bypass -File scripts\build-portable.ps1`.

Expected: API/Web tests, Vite, PyInstaller, signed release manifest, and persistent directory preservation complete without touching a running release.

- [x] **Step 3: Run the actual EXE smoke test**

Run:

```powershell
$release = Get-ChildItem .\dist -Directory -Filter "XiaoQiBao-Portable*" |
    Where-Object { Test-Path (Join-Path $_.FullName "XiaoQiBao-Portable\xiaoqibao.exe") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
cmd /c powershell.exe -ExecutionPolicy Bypass -File scripts\run-portable-smoke.ps1 -ReleaseRootOverride (Join-Path $release "XiaoQiBao-Portable") -UseReleaseData -StartupKind cold
```

Expected: EXE window visible, API ready, 14/14 menu performance gates pass, no residual `xiaoqibao.exe` process.

- [x] **Step 4: Run source checks and record evidence**

Run `git diff --check`, UTF-8/garbled-text scans, and `tools/validate_vault.py` against the knowledge vault. Record the selected source path, scan statistics, tests, smoke timing, and EXE hash without writing credentials.
