# A 股市场情绪评分与仪表盘实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以全市场真实行情和已核验热点生成可审计的 A 股情绪分数，并在“今日研判”中展示随分档变化的生产级仪表盘。

**Architecture:** 新增独立的市场情绪契约、纯评分器、腾讯全市场批量来源和 append-only SQLite 仓储。阶段服务在盘中/盘后冻结快照，API 返回当前、昨收基线和日内轨迹；React 仪表盘只展示冻结结果，AI 不参与打分。

**Tech Stack:** Python 3.12、Pydantic 2、SQLite、httpx、FastAPI、React 19、TypeScript 5、Vitest、pytest、Ruff。

## Global Constraints

- 只属于 A 股域；可转债不得读取情绪快照。
- 权重固定为市场宽度 `35%`、涨跌停生态 `25%`、成交活跃度 `20%`、热点持续度 `20%`。
- 没有市场宽度或总覆盖率低于 `70%` 时 `score=null`，不得补 `50`。
- `70-99%` 为 `partial`，`100%` 为 `ready`；过期状态通过独立 `freshness` 字段表达。
- AI 只能解释冻结结果，不能修改分数、分档、组件、数字或风险。
- 中文文件只用 `apply_patch` 修改，并运行严格 UTF-8 与乱码扫描。
- 保留现有 dirty worktree；未经用户明确要求不 stage、commit、push、reset 或回滚。

---

### Task 1: 冻结契约与确定性评分器

**Files:**
- Create: `apps/api/src/qibao_api/contracts/market_sentiment.py`
- Create: `apps/api/src/qibao_api/a_shares/market_sentiment.py`
- Create: `apps/api/tests/a_shares/test_market_sentiment.py`

**Interfaces:**
- Consumes: `MarketBreadthObservation`、`LiquidityBaseline | None`、`HotspotSentimentInput | None`。
- Produces: `MarketSentimentEvaluator.evaluate(...) -> MarketSentimentSnapshot`，公式版本 `a-share-sentiment-v1`。

- [x] **Step 1: 写评分边界和质量门禁失败测试**

覆盖：全市场上涨/下跌极值、`19/20/39/40/59/60/79/80` 分档边界、市场宽度缺失、覆盖率 `69/70/100`、热点缺失、连板缺失、过热风险、相同输入稳定 ID。

```python
def test_score_is_absent_below_required_coverage() -> None:
    snapshot = evaluator().evaluate(
        observation=breadth(quote_coverage=Decimal("1")),
        liquidity_baseline=None,
        hotspot=None,
        trading_date=date(2026, 7, 18),
        phase="intraday",
        generated_at=NOW,
    )
    assert snapshot.coverage_percent < Decimal("70")
    assert snapshot.score is None
    assert snapshot.band == "unavailable"
```

- [x] **Step 2: 运行聚焦测试并确认 RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_market_sentiment.py -q`

Expected: collection fails because the new contract/evaluator modules do not exist.

- [x] **Step 3: 实现冻结模型和版本化纯函数**

模型至少包含：

```python
class SentimentComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: Literal["breadth", "limit_ecology", "liquidity", "hotspot"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    weight: Decimal = Field(gt=0, le=100)
    coverage_percent: Decimal = Field(ge=0, le=100)
    metrics: dict[str, Decimal | int | str | None]
    evidence_ids: tuple[str, ...]

class MarketSentimentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    snapshot_id: str
    previous_snapshot_id: str | None = None
    trading_date: date
    phase: Literal["intraday", "postclose"]
    quality: Literal["ready", "partial", "unavailable"]
    freshness: Literal["current", "stale"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    band: Literal["panic", "cold", "neutral", "active", "overheated", "unavailable"]
    coverage_percent: Decimal = Field(ge=0, le=100)
    components: tuple[SentimentComponent, ...]
    drivers: tuple[str, ...]
    risks: tuple[str, ...]
    beginner_guidance: str
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    source_snapshot_ids: tuple[str, ...]
    formula_version: str
```

公式实现：

```python
breadth_score = clamp(
    advance_ratio_percent * Decimal("0.70")
    + clamp(Decimal("50") + median_change_percent * Decimal("12.5"))
    * Decimal("0.30")
)
limit_score = weighted_available_mean({
    "balance": (limit_balance_score, Decimal("0.55")),
    "seal": (seal_success_percent, Decimal("0.30")),
    "streak": (streak_score_or_none, Decimal("0.15")),
})
liquidity_score = clamp(
    Decimal("50") + (current_amount / baseline_amount - Decimal("1")) * Decimal("100")
)
hotspot_score = (
    theme_score * Decimal("0.25")
    + symbol_score * Decimal("0.35")
    + persistence_score * Decimal("0.25")
    + concentration_score * Decimal("0.15")
)
```

总分使用 `weight * component.coverage_percent` 计算有效权重并归一化；内容寻址 ID 包含全部组件、质量、截止时间和公式版本。

- [x] **Step 4: 运行评分测试并确认 GREEN**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_market_sentiment.py -q`

Expected: all tests pass.

---

### Task 2: 腾讯全市场批量观测与 A 股目录隔离

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tencent_market_sentiment.py`
- Create: `apps/api/tests/gongbu/test_tencent_market_sentiment.py`
- Modify: `apps/api/src/qibao_api/a_shares/instrument_directory.py`
- Modify: `apps/api/tests/a_shares/test_instrument_directory.py`

**Interfaces:**
- Consumes: `AShareInstrumentDirectory.active_symbols() -> tuple[str, ...]` 和共享 `httpx.Client`。
- Produces: `TencentMarketSentimentSource.fetch(*, cutoff: datetime) -> MarketBreadthObservation` 及压缩 `RawSentimentBatch`。

- [x] **Step 1: 写批次解析与全市场聚合失败测试**

覆盖严格 GBK、代码匹配、指数/ETF/转债排除、80 只固定批次、缺失定向重试一次、未来时间拒绝、部分批次覆盖率、上涨/下跌/平盘、涨停/跌停/炸板、涨跌幅中位数、成交额求和、原文哈希和 observer 异常隔离。

```python
def test_aggregates_only_active_a_share_quotes() -> None:
    result = source(payloads=(
        quote("600000", pct="10.00", price="11.00", high="11.00", up="11.00"),
        quote("000001", pct="-10.00", price="9.00", low="9.00", down="9.00"),
        quote("300750", pct="2.00", price="20.00", high="22.00", up="22.00"),
    )).fetch(cutoff=NOW)
    assert result.valid_count == 3
    assert result.limit_up_count == 1
    assert result.limit_down_count == 1
    assert result.broken_limit_up_count == 1
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_tencent_market_sentiment.py apps/api/tests/a_shares/test_instrument_directory.py -q`

Expected: missing source module and `active_symbols` failures.

- [x] **Step 3: 实现目录读取、严格解析、批次与聚合**

每行至少校验 53 个 `~` 字段并读取索引 `2/3/4/30/32/33/34/37/47/48`。请求代码必须与响应代码一致；价格、昨收、涨跌停价必须为正，成交额不得为负。请求以 80 只为一批，批次中缺失/无效代码只定向重试一次。聚合覆盖率为 `valid_count / requested_count * 100`，低覆盖只返回真实有效统计，不扩充分母。

- [x] **Step 4: 运行来源测试并确认 GREEN**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/gongbu/test_tencent_market_sentiment.py apps/api/tests/a_shares/test_instrument_directory.py -q`

Expected: all tests pass.

---

### Task 3: Append-only 仓储、原始批次保留与阶段服务

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/market_sentiment_repository.py`
- Create: `apps/api/tests/a_shares/test_market_sentiment_repository.py`
- Create: `apps/api/tests/a_shares/test_market_sentiment_service.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_sentiment.py`

**Interfaces:**
- Produces: `MarketSentimentRepository.append(snapshot, raw_batches)`、`latest(...)`、`trajectory(...)`、`previous_postclose(...)`、`liquidity_baseline(...)`、`purge_expired_raw_batches(...)`。
- Produces: `MarketSentimentService.refresh(now)` 和 `MarketSentimentService.current(now) -> MarketSentimentResponse`。

- [x] **Step 1: 写仓储完整性和阶段语义失败测试**

覆盖追加写、相同内容幂等、同阶段变化追加、禁止 update/delete、哈希篡改、截止时间、二十日同阶段成交基线、三十日原始 BLOB 清理、盘前昨收基线、盘中当前、盘后定稿、热点只读截止时间和旧快照不冒充当前。

```python
def test_premarket_uses_previous_postclose_as_labeled_baseline(tmp_path) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    repository.append(postclose_snapshot(date(2026, 7, 17), score="64"), ())
    response = service(repository=repository).current(PREMARKET_NOW)
    assert response.current is None
    assert response.previous_close.score == Decimal("64")
    assert response.display_mode == "previous_close_baseline"
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_market_sentiment_repository.py apps/api/tests/a_shares/test_market_sentiment_service.py -q`

Expected: repository/service APIs are absent.

- [x] **Step 3: 实现 SQLite 哈希链和阶段服务**

快照表保存规范 JSON、内容哈希和 `previous_snapshot_id`，触发器拒绝更新和删除。原始批次表保存 `zlib.compress(raw_bytes)`、SHA-256、创建/过期时间，允许按过期时间清理。服务只在盘中或盘后抓取实时行情；盘前响应只引用上一交易日盘后定稿。热点输入只读取 `occurred_at/normalized_at <= cutoff` 的 `verified market_hotspot` 事件。

- [x] **Step 4: 运行仓储和服务测试并确认 GREEN**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_market_sentiment_repository.py apps/api/tests/a_shares/test_market_sentiment_service.py -q`

Expected: all tests pass.

---

### Task 4: API、生产装配、来源健康与调度

**Files:**
- Create: `apps/api/src/qibao_api/routes/market_sentiment.py`
- Create: `apps/api/tests/routes/test_market_sentiment.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/shangshu/scheduler.py`
- Modify: `apps/api/tests/shangshu/test_scheduler.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`
- Modify: `apps/api/src/qibao_api/contracts/source_health.py`

**Interfaces:**
- Produces: current/date/refresh endpoints under `/api/v1/a-shares/market-sentiment`。
- Consumes: existing Tencent authorization and optional verified Tonghuashun hotspot evidence.
- Scheduler accepts `market_sentiment_service=None` and writes isolated `:sentiment` operation jobs.

- [x] **Step 1: 写路由、生命周期和调度失败测试**

覆盖当前/历史响应、非交易日、盘前手动刷新、授权失败、来源失败 503 映射、服务单例与关闭、盘中/盘后决策前刷新、重启幂等、情绪失败不阻断决策、来源尝试写入 source-health。

- [x] **Step 2: 运行聚焦测试并确认 RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/routes/test_market_sentiment.py apps/api/tests/shangshu/test_scheduler.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`

Expected: route/dependency/service wiring failures.

- [x] **Step 3: 实现路由和生产装配**

路由错误只返回：`market_sentiment_unavailable`、`market_sentiment_wrong_phase`、`market_sentiment_not_trading_day`、`market_sentiment_source_not_authorized`。生产 lifespan 复用共享 HTTP 客户端、证券目录、新闻仓储、交易日历和 operations observer，并关闭情绪仓储。调度对盘中固定时点和盘后任务先运行独立情绪 job；失败记录后继续原决策流程。

- [x] **Step 4: 运行聚焦测试并确认 GREEN**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/routes/test_market_sentiment.py apps/api/tests/shangshu/test_scheduler.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`

Expected: all tests pass.

---

### Task 5: 分数驱动的今日研判仪表盘

**Files:**
- Create: `apps/web/src/features/market-sentiment/types.ts`
- Create: `apps/web/src/features/market-sentiment/api.ts`
- Create: `apps/web/src/features/market-sentiment/MarketSentimentDashboard.tsx`
- Create: `apps/web/src/features/market-sentiment/MarketSentimentDashboard.test.tsx`
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`

**Interfaces:**
- Consumes: `MarketSentimentResponse` and optional refresh command.
- Produces: accessible score gauge, four component rows, drivers/risks/guidance and phase trajectory.

- [x] **Step 1: 写五档和降级状态组件失败测试**

覆盖五个分档、过热风险优先、活跃驱动优先、中性等待条件、`partial` 覆盖率、`unavailable` 不显示数字、盘前昨收基线、过期标签、刷新失败保留旧历史、可访问名称及不出现可转债文案。

```tsx
expect(screen.getByRole("img", { name: "A 股市场情绪 84 分，过热" })).toBeInTheDocument();
expect(screen.getByText("覆盖率 80% · 部分可用")).toBeInTheDocument();
expect(screen.getByText("追高和炸板风险升高")).toBeInTheDocument();
```

- [x] **Step 2: 运行组件测试并确认 RED**

Run: `pnpm --filter @qibao/web exec vitest run src/features/market-sentiment/MarketSentimentDashboard.test.tsx src/features/dashboard/Dashboard.test.tsx`

Expected: new feature modules and dashboard region are absent.

- [x] **Step 3: 实现仪表盘和响应式状态**

仪表固定尺寸，使用 CSS 变量 `--sentiment-accent` 和 `conic-gradient` 表示分数；文字和 Lucide 图标同时表达状态。恐慌/低迷/过热先渲染风险，中性先渲染等待条件，活跃先渲染驱动。四个组件使用固定轨道，不因标签长度改变布局。390px 下单列、触控按钮至少 44px、无嵌套卡片和页面级横向滚动。

- [x] **Step 4: 运行组件测试并确认 GREEN**

Run: `pnpm --filter @qibao/web exec vitest run src/features/market-sentiment/MarketSentimentDashboard.test.tsx src/features/dashboard/Dashboard.test.tsx`

Expected: all tests pass.

---

### Task 6: 完整验证、真实数据验收与路线图

**Files:**
- Modify: `docs/roadmap.md`
- Modify: `docs/superpowers/plans/2026-07-18-a-share-market-sentiment.md`

- [x] **Step 1: 运行 API 全量与 Ruff**

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

Expected: zero failures and zero Ruff errors.

- [x] **Step 2: 运行 Web 全量与生产构建**

```powershell
pnpm test:web
pnpm build
```

Expected: zero test failures and successful TypeScript/Vite build.

- [x] **Step 3: 运行编码与差异门禁**

严格 UTF-8 解码所有 tracked/untracked 文本；对 `apps`、`README.md`、本规格、计划和路线图扫描替换字符、常见乱码和连续问号；运行 `git diff --check`。

Expected: zero decode errors, zero scoped mojibake matches, no whitespace errors.

- [x] **Step 4: 正式服务和浏览器验收**

重启 `8000/5173`，真实刷新一次当前允许阶段的 A 股情绪快照，核对请求数、有效股票数、覆盖率、四组件、公式版本、时间和来源哈希。桌面与 390x844 验收五档视觉、部分/不可用、文字遮挡、页面溢出和控制台 error/warn；保留“今日研判”页面供用户查看。

验收记录（2026-07-18）：完整目录 5976 只（深 2994、沪 2400、北 582）；腾讯有效行情 5519 只，行情覆盖率 92.35%；已核验热点 34 只、101 个题材；情绪 28.74 分、低迷、总组件覆盖率 71.95%、`partial`，公式 `a-share-sentiment-v1`，快照 `sentiment-8678cd93f09824c389ede729`。成交基线缺失时未补值。桌面 1265x720 和移动 390x844 无横向溢出、无文字裁切、无控制台 error/warn；移动端仪表盘文字不低于 12px，刷新按钮为 44x44。

- [x] **Step 5: 更新记录并复核范围**

在路线图记录真实评分、质量、覆盖率和数据来源；勾选本计划完成项。检查 `git status` 和 `git diff`，只保留本功能改动及用户已有 dirty 改动；不提交、不推送。
