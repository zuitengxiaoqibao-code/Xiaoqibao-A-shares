# 隔夜外盘风向标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在数据大屏接入真实的道琼斯、标普500、纳斯达克及八个美股风向标行情，并明确交易日期、盘中/收盘状态和数据源质量。

**Architecture:** 后端新增统一海外行情快照服务，批量请求腾讯财经接口并写入内存/磁盘短缓存；API 只返回一份完整快照，前端数据大屏通过共享请求展示指数和个股，单一来源异常不会清空上一份有效快照。数据缺失、陈旧和不可用保持真实状态，不生成占位价格。

**Tech Stack:** Python/FastAPI/httpx/Pydantic；React/TypeScript/CSS；Vitest；Vite；便携 PyInstaller EXE。

## Global Constraints

- EXE 是唯一用户交付入口，不能把 HTML 或 localhost 作为交付物。
- 海外行情必须来自真实接口；接口失败时显示中文原因，不使用随机或静态行情。
- 美股行情日期使用来源返回的交易日期，不使用本机日期替代。
- 保留用户 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 目录。
- 中文源文件使用 UTF-8 和 `apply_patch` 修改，完成后执行乱码扫描与 `git diff --check`。

---

### Task 1: 定义海外行情契约与数据源解析

**Files:**
- Create: `apps/api/src/qibao_api/contracts/overseas_market.py`
- Create: `apps/api/src/qibao_api/gongbu/overseas_market.py`
- Test: `apps/api/tests/gongbu/test_overseas_market.py`

**Interfaces:**
- Produces `OverseasInstrumentQuote`, `OverseasMarketSnapshot` and `OverseasMarketService.get_snapshot()`.
- `OverseasMarketSnapshot` contains `indices`, `mag7` (including AVGO after TSLA), `observed_at`, `trading_label`, `quality`, `source`, `reason`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_parses_three_indices_and_mag7_from_tencent_payload():
    snapshot = service.get_snapshot()
    assert [item.symbol for item in snapshot.indices] == ["DJIA", "SPX", "NDX"]
    assert [item.symbol for item in snapshot.mag7] == ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO"]
    assert snapshot.quality == "ready"

def test_failed_upstream_keeps_last_snapshot_as_stale():
    first = service.get_snapshot()
    transport.fail = True
    second = service.get_snapshot()
    assert second.indices == first.indices
    assert second.quality == "stale"
    assert second.reason
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest apps/api/tests/gongbu/test_overseas_market.py -q`
Expected: FAIL because the contract and service are not implemented.

- [ ] **Step 3: Implement the minimal parser and service**

Implement a fixed symbol registry matching the previous session: `100.DJIA`, `100.SPX`, `100.NDX`, `usAAPL`, `usMSFT`, `usNVDA`, `usGOOGL`, `usAMZN`, `usMETA`, `usTSLA`. Decode Tencent response as GBK, parse price/change/previous close and source timestamp, map trading status to `盘中` or `最近收盘`, cache the last valid snapshot, and return `stale` on transient failure.

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest apps/api/tests/gongbu/test_overseas_market.py -q`
Expected: PASS.

### Task 2: Register API route and shared refresh behavior

**Files:**
- Modify: `apps/api/src/qibao_api/main.py`
- Create or modify: `apps/api/src/qibao_api/routes/overseas_market.py`
- Test: `apps/api/tests/routes/test_overseas_market.py`

**Interfaces:**
- Produces `GET /api/v1/market/overseas` returning the Pydantic snapshot JSON.
- Uses one service instance per application lifespan; no per-card upstream requests.

- [ ] **Step 1: Write failing route tests**

```python
def test_overseas_route_returns_indices_and_mag7(client, ready_service):
    response = client.get("/api/v1/market/overseas")
    assert response.status_code == 200
    body = response.json()
    assert len(body["indices"]) == 3
    assert len(body["mag7"]) == 8
    assert body["trading_label"] in {"盘中", "最近收盘"}
```

- [ ] **Step 2: Run route tests to verify failure**

Run: `pytest apps/api/tests/routes/test_overseas_market.py -q`
Expected: FAIL with 404 or missing response fields.

- [ ] **Step 3: Register the route and lifespan service**

Mount the route under the existing API router, instantiate the service once, and expose a short cache window that is independent from A-share refresh cadence. Return `stale` data with its original source timestamp when refresh fails.

- [ ] **Step 4: Run route tests to verify pass**

Run: `pytest apps/api/tests/routes/test_overseas_market.py -q`
Expected: PASS.

### Task 3: Add data-screen overseas panel

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Modify: `apps/web/src/features/data-screen/dataScreen.css`
- Modify: `apps/web/src/features/data-screen/types.ts`
- Create: `apps/web/src/features/data-screen/overseasMarket.ts`
- Test: `apps/web/src/features/data-screen/DataScreenView.test.tsx`

**Interfaces:**
- Consumes `GET /api/v1/market/overseas` through the existing API client.
- Produces an accessible `region` named `隔夜外盘` with index and eight overseas-indicator cards.

- [ ] **Step 1: Write failing UI tests**

```tsx
it("shows overseas indices and the magnificent seven with source status", async () => {
  render(<DataScreenView loadOverseas={vi.fn(async () => overseasResponse)} />);
  expect(await screen.findByRole("region", { name: "隔夜外盘" })).toBeInTheDocument();
  expect(screen.getByText("道琼斯")).toBeInTheDocument();
  expect(screen.getByText("美股七姐妹")).toBeInTheDocument();
  expect(screen.getByText("英伟达")).toBeInTheDocument();
  expect(screen.getByText("最近收盘")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused UI test to verify failure**

Run: `pnpm --filter @qibao/web test -- DataScreenView.test.tsx --run`
Expected: FAIL because `隔夜外盘` is not rendered.

- [ ] **Step 3: Implement the panel and status presentation**

Add a compact two-row panel below the data-screen top market summary and before the main three-column content. Use red for positive change and green for negative change, keep the source date visible, show `盘中` or `最近收盘`, and render `数据暂不可用：原因` when no valid snapshot exists. Do not alter existing A-share chart logic or limit-up/limit-down placement.

- [ ] **Step 4: Add responsive and dense styling**

Use a 3-column index grid and 7-column Mag7 grid at wide widths, collapse to 2 columns on narrow windows, preserve no horizontal overflow, and reuse existing data-screen card tokens without adding a second nested scroll container.

- [ ] **Step 5: Run focused tests and verify pass**

Run: `pnpm --filter @qibao/web test -- DataScreenView.test.tsx --run`
Expected: PASS.

### Task 4: Integrate API client refresh and failure retention

**Files:**
- Modify: `apps/web/src/features/data-screen/api.ts`
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Test: `apps/web/src/features/data-screen/api.test.ts`

**Interfaces:**
- `loadOverseasMarket()` returns `OverseasMarketSnapshot`.
- Refresh failures preserve the last ready snapshot and expose `stale` status.

- [ ] **Step 1: Add failing client tests**

```ts
it("keeps the last overseas snapshot when refresh fails", async () => {
  const first = await loadOverseasMarket(fetchReady);
  const second = await loadOverseasMarket(fetchFailure, first);
  expect(second.indices).toEqual(first.indices);
  expect(second.quality).toBe("stale");
});
```

- [ ] **Step 2: Implement the shared loader**

Use the existing API client and request ledger, add a bounded refresh interval, and avoid starting a request for every rendered instrument card.

- [ ] **Step 3: Run client tests**

Run: `pnpm --filter @qibao/web test -- apps/web/src/features/data-screen/api.test.ts --run`
Expected: PASS.

### Task 5: Build, smoke-test and publish the EXE

**Files:**
- Modify: `docs/verification/2026-09-03-overseas-market-indicators.md`
- Build output: `dist/XiaoQiBao-Portable/`

- [ ] **Step 1: Run frontend full tests**

Run: `pnpm test:web -- --run`
Expected: all web test files pass.

- [ ] **Step 2: Run production build**

Run: `pnpm build`
Expected: Vite exits with code 0.

- [ ] **Step 3: Run encoding and diff checks**

Run: `git diff --check -- apps/api/src/qibao_api/contracts/overseas_market.py apps/api/src/qibao_api/gongbu/overseas_market.py apps/api/src/qibao_api/routes/overseas_market.py apps/web/src/features/data-screen`
Expected: no whitespace errors; scan changed Chinese files for three consecutive question marks, common mojibake signatures, and the Unicode replacement character `U+FFFD`.

- [ ] **Step 4: Rebuild portable EXE**

Run: `& .\\scripts\\build-portable.ps1 -SkipTests`
Expected: `Portable release: ...\\dist\\XiaoQiBao-Portable`.

- [ ] **Step 5: Run the actual EXE smoke test**

Run: `& .\\scripts\\run-portable-smoke.ps1 -StartupKind cold`
Expected: window visible, API ready, smoke passed, and no `xiaoqibao.exe` remains after exit.
