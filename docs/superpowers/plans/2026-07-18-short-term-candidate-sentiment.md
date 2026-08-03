# 短线候选个股综合情绪实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 A 股短线候选增加可审计的批量个股综合情绪，并仅在所选股票右侧行动卡中显示分数、原因、风险与证据。

**Architecture:** 后端以冻结候选快照为边界，分别读取新闻解释、题材热点和资金流，使用版本化纯函数生成追加式批量情绪快照。前端只在短线候选页签请求批量结果，保留原量价排序，并把所选候选的完整情绪快照传给右侧行动卡。

**Tech Stack:** Python 3.12、FastAPI、Pydantic 2、SQLite、pytest、React 19、TypeScript 5、Vitest、Testing Library、现有 CSS 设计令牌。

## Global Constraints

- 个股情绪不改变候选分、候选排序、行动结论、置信度或风险门禁。
- 权重固定为新闻 `40%`、热点 `30%`、资金 `30%`；覆盖率低于 `60%` 不出总分。
- 新闻方向只读取已冻结、带引用、非降级且置信度不低于 `0.65` 的解释。
- 不复制全市场情绪，不混入波段候选、自选股或可转债。
- 缺失数据不填默认中性值；不可用时不得显示数字。
- 候选、搜索、自选和右侧股票加载不能被情绪失败阻断。
- 中文文件只用 `apply_patch` 修改；完成后执行严格 UTF-8 与乱码扫描。
- 保留 dirty worktree；不 stage、commit 或 push。

---

### Task 1: 情绪契约与纯评分器

**Files:**
- Create: `apps/api/src/qibao_api/contracts/candidate_sentiment.py`
- Create: `apps/api/src/qibao_api/a_shares/candidate_sentiment.py`
- Create: `apps/api/tests/contracts/test_candidate_sentiment.py`
- Create: `apps/api/tests/a_shares/test_candidate_sentiment.py`

**Interfaces:**
- Produces: `CandidateSentimentComponent`, `CandidateSentimentSnapshot`, `CandidateSentimentBatch`。
- Produces: `CandidateSentimentEvaluator.evaluate(board, evidence, cutoff)`。
- Consumes later: service、repository 和 route 直接使用以上冻结类型。

- [x] **Step 1: 写契约失败测试**

覆盖：缺失分数必须对应 `unavailable`、完整质量必须覆盖率 `100`、观察时间不得晚于生成时间、A 股代码和 `0-100` 分数边界。

```python
def test_unavailable_score_and_band_must_agree() -> None:
    with pytest.raises(ValidationError, match="missing score"):
        CandidateSentimentSnapshot(
            **snapshot_values(), score=None, band="neutral", quality="unavailable"
        )
```

- [x] **Step 2: 运行契约测试并确认 RED**

Run: `uv run pytest apps/api/tests/contracts/test_candidate_sentiment.py -q`

Expected: import failure because `candidate_sentiment` contract does not exist.

- [x] **Step 3: 实现冻结契约**

```python
class CandidateSentimentComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: Literal["news", "hotspot", "fund_flow"]
    status: Literal["ready", "unavailable"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    weight: Decimal = Field(gt=0, le=100)
    summary: str = Field(min_length=1)
    observed_at: AwareDatetime | None = None
    evidence_ids: tuple[str, ...] = ()

class CandidateSentimentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    snapshot_id: str | None = None
    candidate_snapshot_id: str
    candidate_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbol: str = Field(pattern=r"^\d{6}$")
    quality: Literal["ready", "partial", "unavailable"]
    freshness: Literal["current", "stale"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    band: Literal[
        "strongly_bearish", "cautious", "neutral", "positive",
        "overheated", "unavailable",
    ]
    coverage_percent: Decimal = Field(ge=0, le=100)
    components: tuple[CandidateSentimentComponent, ...]
    primary_reason: str
    primary_risk: str
    beginner_guidance: str
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    source_snapshot_ids: tuple[str, ...]
    formula_version: Literal["candidate-sentiment-v1"] = "candidate-sentiment-v1"
```

- [x] **Step 4: 写评分失败测试**

覆盖：`40/30/30` 权重、新闻置信度门禁、三交易日窗口、热点未上榜 `40`、热点延续与过热风险、资金流归一化、`60%` 覆盖率门禁、五档边界和原候选顺序。

```python
def test_partial_score_uses_available_weight_without_changing_candidate_order() -> None:
    batch = evaluator.evaluate(
        board=board(("600000", "000001")),
        evidence={
            "600000": evidence(hotspot_score=Decimal("65"), fund_score=Decimal("80")),
            "000001": evidence(hotspot_score=Decimal("40"), fund_score=Decimal("20")),
        },
        cutoff=CUTOFF,
    )
    assert [item.symbol for item in batch.items] == ["600000", "000001"]
    assert batch.items[0].coverage_percent == Decimal("60")
    assert batch.items[0].quality == "partial"
```

- [x] **Step 5: 运行评分测试并确认 RED**

Run: `uv run pytest apps/api/tests/a_shares/test_candidate_sentiment.py -q`

Expected: import or missing evaluator failure.

- [x] **Step 6: 实现纯评分器**

实现内部 `CandidateSentimentEvidence`，新闻基础分 `75/50/25`，热点 `40/65/80-90`，资金分：

```python
ratio = clamp(main_net_5d / (liquidity_amount_20d * Decimal("5")), Decimal("-0.2"), Decimal("0.2"))
fund_score = clamp(Decimal("50") + ratio * Decimal("150") + intraday_adjustment, Decimal("0"), Decimal("100"))
```

按可用权重归一化，覆盖率不足 `60` 时 `score=None`；使用 `0/20/40/60/80` 边界映射五档。过热时 `primary_risk` 必须明确追涨或拥挤风险。

- [x] **Step 7: 运行 Task 1 测试并确认 GREEN**

Run: `uv run pytest apps/api/tests/contracts/test_candidate_sentiment.py apps/api/tests/a_shares/test_candidate_sentiment.py -q`

Expected: all tests pass.

---

### Task 2: 追加式情绪仓储

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/candidate_sentiment_repository.py`
- Create: `apps/api/tests/a_shares/test_candidate_sentiment_repository.py`

**Interfaces:**
- Consumes: `CandidateSentimentBatch`。
- Produces: `append(batch, input_payload) -> CandidateSentimentBatch`。
- Produces: `latest(candidate_input_hash, cutoff=None) -> CandidateSentimentBatch | None`。
- Produces: `verify_all() -> int`。

- [x] **Step 1: 写仓储失败测试**

覆盖追加写、相同输入幂等、输入变化追加、按候选哈希与截止时间读取、禁止更新删除、payload 与输入哈希篡改检测、关闭后重开。

```python
def test_repository_reuses_identical_input_and_appends_changed_input(tmp_path) -> None:
    repository = CandidateSentimentRepository(tmp_path / "candidate-sentiment.sqlite3")
    first = repository.append(batch(), {"candidate": "a", "sources": ["one"]})
    same = repository.append(batch(), {"candidate": "a", "sources": ["one"]})
    changed = repository.append(batch(), {"candidate": "a", "sources": ["two"]})
    assert same.snapshot_id == first.snapshot_id
    assert changed.snapshot_id != first.snapshot_id
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `uv run pytest apps/api/tests/a_shares/test_candidate_sentiment_repository.py -q`

Expected: repository module missing.

- [x] **Step 3: 实现仓储**

创建 `candidate_sentiment_batches` 表：`sequence`、`snapshot_id`、`candidate_snapshot_id`、`candidate_input_hash`、`input_hash`、`input_payload`、`canonical_hash`、`payload`、`generated_at`。为 update/delete 创建拒绝触发器；读取时重新计算 HMAC-safe SHA-256 比较并用 Pydantic 重新验证。

- [x] **Step 4: 运行测试并确认 GREEN**

Run: `uv run pytest apps/api/tests/a_shares/test_candidate_sentiment_repository.py -q`

Expected: all tests pass.

---

### Task 3: 批量服务、刷新与来源降级

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/candidate_sentiment_service.py`
- Create: `apps/api/tests/a_shares/test_candidate_sentiment_service.py`
- Modify: `apps/api/src/qibao_api/gongbu/news_repository.py`
- Modify: `apps/api/tests/gongbu/test_news_ingestion.py`

**Interfaces:**
- Produces: `CandidateSentimentService.current(candidate_snapshot_id, cutoff)`。
- Produces: `await CandidateSentimentService.refresh(candidate_snapshot_id, cutoff)`。
- Uses bounded concurrency of `4` for per-symbol news/fund sync.

- [x] **Step 1: 写服务失败测试**

覆盖候选快照校验、最多 20 只且仅 `short_term`、截止时间、最新有效解释选择、新闻/热点/资金逐项失败、单股失败隔离、刷新有界并发、15 分钟新鲜结果复用。

```python
@pytest.mark.asyncio
async def test_refresh_keeps_other_symbols_when_one_source_fails() -> None:
    service = service_with(
        news_sync=per_symbol({"600000": OSError("offline")}),
        fund_sync=per_symbol({"600000": fund("600000"), "000001": fund("000001")}),
    )
    batch = await service.refresh(CANDIDATE_SNAPSHOT_ID, CUTOFF)
    assert [item.symbol for item in batch.items] == ["600000", "000001"]
    assert batch.items[0].quality in {"partial", "unavailable"}
    assert batch.items[1].score is not None
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `uv run pytest apps/api/tests/a_shares/test_candidate_sentiment_service.py -q`

Expected: service module missing.

- [x] **Step 3: 增加新闻解释截止时间读取**

在 `NewsRepository` 增加：

```python
def interpretations_for_events(
    self, event_ids: tuple[str, ...], *, cutoff: datetime | None = None,
) -> list[AIInterpretation]:
    ...
```

只返回指定事件、`generated_at <= cutoff` 的已校验解释；同一事件由 service 选择最后一条。添加仓储完整性与截止时间测试。

- [x] **Step 4: 实现 service current**

读取并校验 `AShareResearchRepository.get_candidate_board`；只使用短线候选。组装三类证据，调用纯评分器并追加仓储。没有已确认来源同步时，空事件不当作中性；只有存在冻结证据的分项可以参与。

- [x] **Step 5: 实现 service refresh**

热点全局同步一次；新闻和资金按股票使用 `asyncio.Semaphore(4)` 有界并发。每个分项单独捕获 `SourceAuthorizationError`、`OSError`、`httpx.HTTPError`、`ValueError` 和仓储完整性错误，写入不可用摘要。刷新完成后重新读取冻结仓储并评分；15 分钟内相同候选输入哈希直接复用。

- [x] **Step 6: 运行测试并确认 GREEN**

Run: `uv run pytest apps/api/tests/a_shares/test_candidate_sentiment_service.py apps/api/tests/gongbu/test_news_ingestion.py -q`

Expected: all tests pass.

---

### Task 4: FastAPI 路由和运行时接线

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/api/tests/routes/test_research.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: `POST /api/v1/a-shares/candidate-sentiment/batch`。
- Produces: `POST /api/v1/a-shares/candidate-sentiment/batch/refresh`。
- Request: `{ "candidate_snapshot_id": "a-share-candidates-..." }`。

- [x] **Step 1: 写路由失败测试**

覆盖 current、refresh、未知快照 `404`、损坏仓储 `503`、友好错误不泄露内部异常，以及单源失败仍返回 `200` 部分结果。

```python
def test_candidate_sentiment_batch_returns_items_in_candidate_order(client) -> None:
    response = client.post(
        "/api/v1/a-shares/candidate-sentiment/batch",
        json={"candidate_snapshot_id": CANDIDATE_SNAPSHOT_ID},
    )
    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()["items"]] == ["600000", "000001"]
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `uv run pytest apps/api/tests/routes/test_research.py -q`

Expected: route returns 404.

- [x] **Step 3: 实现依赖与路由**

新增 `get_candidate_sentiment_service`。在 `lifespan` 中创建情绪仓储、评分器和服务，注入 research/news/hotspot/fund repositories 与 sync services，并在 finally 中关闭仓储。

路由只映射预期领域错误：未知候选快照 `404 candidate_snapshot_not_found`，完整性/仓储异常 `503 candidate_sentiment_store_error`，输入冲突 `422 candidate_sentiment_input_invalid`。

- [x] **Step 4: 运行路由和 lifespan 测试并确认 GREEN**

Run: `uv run pytest apps/api/tests/routes/test_research.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`

Expected: all tests pass.

---

### Task 5: Web 类型、API 与 Dashboard 状态链路

**Files:**
- Create: `apps/web/src/features/candidate-sentiment/types.ts`
- Create: `apps/web/src/features/candidate-sentiment/api.ts`
- Create: `apps/web/src/features/candidate-sentiment/api.test.ts`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`

**Interfaces:**
- Produces: `loadCandidateSentiment(candidateSnapshotId)`。
- Produces: `refreshCandidateSentiment(candidateSnapshotId)`。
- Produces: Dashboard map `Record<string, CandidateSentimentSnapshot>`。

- [x] **Step 1: 写 API 与链路失败测试**

断言 current/refresh 使用 POST JSON、友好解析 API 错误；Dashboard 把 loaders 传给 StockSelector，并把所选短线候选的情绪传给 StockDecisionCockpit。

```typescript
expect(fetch).toHaveBeenCalledWith(
  "/api/v1/a-shares/candidate-sentiment/batch",
  expect.objectContaining({ method: "POST", body: JSON.stringify({ candidate_snapshot_id: "candidate-1" }) }),
);
```

- [x] **Step 2: 运行测试并确认 RED**

Run: `pnpm --filter @qibao/web exec vitest run src/features/candidate-sentiment/api.test.ts src/features/dashboard/Dashboard.test.tsx`

Expected: missing modules/props.

- [x] **Step 3: 实现类型、API 和状态传递**

类型严格镜像 Pydantic 契约。Dashboard 接收两个 loader，以候选输入哈希替换批量 map；没有匹配所选代码时给 cockpit 传 `null`。A 股观察以外页面不保留旧批量。

- [x] **Step 4: 运行测试并确认 GREEN**

Run: `pnpm --filter @qibao/web exec vitest run src/features/candidate-sentiment/api.test.ts src/features/dashboard/Dashboard.test.tsx`

Expected: all tests pass.

---

### Task 6: 短线候选批量情绪状态链路

**Files:**
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockSelector.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Extends StockSelector props with `loadCandidateSentiments`, `refreshCandidateSentiments`, `onCandidateSentiments`。
- Candidate row only renders code, name and candidate score; it does not consume or render a sentiment snapshot. The callback forwards the selected-page batch to Dashboard and the right-side cockpit.

- [x] **Step 1: 写左侧不渲染失败测试**

覆盖情绪批量仍加载、候选顺序不变、候选行不出现情绪区域，以及右侧面板继续接收批量结果。

- [x] **Step 2: 写 StockSelector 懒加载与竞态失败测试**

断言只在短线页签请求；相同输入哈希不重复；波段和自选不请求；候选顺序不变；缺失/陈旧自动刷新一次；旧快照迟到响应不覆盖新快照；批量失败只有一个错误条且候选仍可选择。

- [x] **Step 3: 运行测试并确认 RED**

Run: `pnpm --filter @qibao/web exec vitest run src/features/stock-cockpit/StockSelector.test.tsx`

Expected: missing component/props.

- [x] **Step 4: 实现批量状态机且保持候选行简洁**

使用 request generation 与 effect cleanup 隔离旧响应。候选行只保留代码、名称、候选分和必要的自选操作，不渲染情绪快照或量价摘要；批量失败使用一个 `RefreshCw` 图标加文字按钮的状态条。

- [x] **Step 5: 运行测试并确认 GREEN**

Run: `pnpm --filter @qibao/web exec vitest run src/features/stock-cockpit/StockSelector.test.tsx`

Expected: all tests pass.

---

### Task 7: 右侧个股情绪证据分区

**Files:**
- Create: `apps/web/src/features/candidate-sentiment/CandidateSentimentPanel.tsx`
- Create: `apps/web/src/features/candidate-sentiment/CandidateSentimentPanel.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`
- Modify: `apps/web/src/app/theme.css`

**Interfaces:**
- Extends StockDecisionCockpit with optional `candidateSentiment?: CandidateSentimentSnapshot | null`。
- Renders one unframed section after the action conclusion and before detailed stock data.

- [x] **Step 1: 写面板失败测试**

断言总分/不可用、三个固定分项、数据时间、证据编号、主要原因、风险、新手建议和“不改变候选排序与行动结论”。没有短线候选情绪时不渲染空面板。

- [x] **Step 2: 运行测试并确认 RED**

Run: `pnpm --filter @qibao/web exec vitest run src/features/candidate-sentiment/CandidateSentimentPanel.test.tsx src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: missing panel/prop.

- [x] **Step 3: 实现面板与响应式样式**

使用三列桌面网格、单列移动布局；不在卡片中嵌套卡片。分数、五档和覆盖率尺寸稳定，辅助文字至少 `12px`，证据编号可换行，颜色同时带文字标签。

- [x] **Step 4: 运行测试并确认 GREEN**

Run: `pnpm --filter @qibao/web exec vitest run src/features/candidate-sentiment/CandidateSentimentPanel.test.tsx src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: all tests pass.

---

### Task 8: 完整验证与真实页面检查

**Files:**
- Modify: `docs/superpowers/plans/2026-07-18-short-term-candidate-sentiment.md`

- [x] **Step 1: 运行 API 全量测试**

Run: `uv run pytest apps/api/tests -q`

Expected: zero failures.

- [x] **Step 2: 运行 Ruff**

Run: `uv run ruff check apps/api/src apps/api/tests`

Expected: zero errors.

- [x] **Step 3: 运行 Web 全量测试和构建**

Run: `pnpm test:web`

Run: `pnpm build`

Expected: zero failures and successful Vite production build.

- [x] **Step 4: 运行编码和差异门禁**

严格 UTF-8 解码全部修改过的 Python、TypeScript、CSS 和 Markdown；扫描替换字符、常见乱码、连续问号和尾随空格；运行 `git diff --check`。

Expected: zero encoding, mojibake and whitespace failures.

- [x] **Step 5: 运行实际页面检查**

在 `http://localhost:5173/a-shares` 打开短线候选，确认左侧不显示情绪区，点击候选后右侧显示批量情绪面板，并覆盖不可用、重试和候选选择。在默认桌面视口与 `390x844` 检查无控制台错误、页面级横向溢出、文字遮挡或小于 `12px` 的辅助文字。

- [x] **Step 6: 更新计划复选框并保留 worktree**

确认所有 `^- [ ]` 实施步骤均完成。保留 `codex/a-share-daily-research` worktree，不暂存、不提交、不推送。
