# 量化研究智能升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不阻塞便携 EXE 启动和量化首屏的前提下，交付可追溯的因子健康、风险闸门、机会 Pitch、60 日验证、ETF 映射和 AI 假设验证工作流。

**Architecture:** 在现有 `qibao_api.a_shares` 内建立若干无副作用的确定性计算模块，由聚合服务读取当前量化策略与影子账本并生成 last-good 快照；React 只读取聚合快照并进行筛选展示。重计算留在后台，读取端点不触发同步全市场扫描。

**Tech Stack:** Python 3.12、Pydantic 2、FastAPI、SQLite、React 18、TypeScript、Vitest、现有便携 EXE 构建脚本。

## Global Constraints

- 只使用真实且有来源的 A 股数据；缺失项保持 `partial/insufficient/stale/unavailable/error`。
- AI 只能提出假设和解释，确定性引擎负责计算和审批。
- 综合分不是概率，胜率只能来自成熟影子样本。
- 页面读取不得同步扫描全市场；优先返回 last-good 快照。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。
- 用户验收入口仅为便携 EXE。
- 重建必须保留 `config/data/news/cache/logs/models/exports/backups`。

---

### Task 1: 研究契约与因子注册表

**Files:**
- Create: `apps/api/src/qibao_api/contracts/quant_research.py`
- Create: `apps/api/src/qibao_api/a_shares/factor_registry.py`
- Test: `apps/api/tests/a_shares/test_factor_registry.py`
- Test: `apps/api/tests/contracts/test_quant_research.py`

**Interfaces:**
- Produces: `FactorDefinition`, `FactorRegistrySnapshot`, `FactorRegistry.register()`、`get()`、`snapshot()`。
- Consumes: 当前 `FactorSnapshot` 的七个真实价量字段。

- [ ] **Step 1: 写注册表失败测试**

```python
def test_default_registry_contains_only_computable_factor_fields() -> None:
    snapshot = build_default_factor_registry().snapshot(as_of=NOW)
    assert {item.factor_id for item in snapshot.factors} == {
        "return_5d", "return_20d", "distance_ma20", "volume_ratio_5_20",
        "volatility_20d", "liquidity_amount_20d", "latest_close",
    }
    assert all(item.lifecycle == "active" for item in snapshot.factors)
```

- [ ] **Step 2: 运行并确认因模块缺失而失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_factor_registry.py -q`
Expected: FAIL，提示 `factor_registry` 不存在。

- [ ] **Step 3: 实现冻结契约、唯一注册和默认注册表**

```python
class FactorRegistry:
    def register(self, definition: FactorDefinition) -> None:
        if definition.factor_id in self._definitions:
            raise ValueError("factor id already registered")
        self._definitions[definition.factor_id] = definition

    def snapshot(self, *, as_of: datetime) -> FactorRegistrySnapshot:
        return FactorRegistrySnapshot(
            status="ready", as_of=as_of, factors=tuple(self._definitions.values()),
            formula_version="quant-factor-registry-v1",
        )
```

- [ ] **Step 4: 运行契约和注册表测试**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/contracts/test_quant_research.py apps/api/tests/a_shares/test_factor_registry.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/contracts/quant_research.py apps/api/src/qibao_api/a_shares/factor_registry.py apps/api/tests/contracts/test_quant_research.py apps/api/tests/a_shares/test_factor_registry.py
git commit -m "feat: add governed factor registry"
```

### Task 2: 因子健康计算

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/factor_health.py`
- Test: `apps/api/tests/a_shares/test_factor_health.py`

**Interfaces:**
- Consumes: `FactorObservation(factor_id, trade_date, symbol, value, forward_return)`。
- Produces: `evaluate_factor_health(definition, observations, generated_at)` 返回 `FactorHealth`。

- [ ] **Step 1: 写 RankIC、样本不足和冗余失败测试**

```python
def test_factor_health_uses_daily_spearman_rank_ic() -> None:
    result = evaluate_factor_health(DEFINITION, monotonic_observations(20, 30), NOW)
    assert result.status == "healthy"
    assert result.rank_ic_20 == Decimal("1.0000")
    assert result.valid_day_count == 20

def test_factor_health_does_not_invent_icir_for_short_history() -> None:
    result = evaluate_factor_health(DEFINITION, monotonic_observations(5, 30), NOW)
    assert result.status == "insufficient"
    assert result.icir is None
```

- [ ] **Step 2: 运行并确认失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_factor_health.py -q`
Expected: FAIL，提示健康计算接口不存在。

- [ ] **Step 3: 实现无第三方统计依赖的秩、Pearson 和健康裁决**

```python
def spearman(values: Sequence[Decimal], returns: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2 or len(set(values)) < 2 or len(set(returns)) < 2:
        return None
    return pearson(average_ranks(values), average_ranks(returns))
```

单日横截面少于 30 只不进入 IC；少于 20 个有效日状态为 `insufficient`；最近有效日期超出阈值为 `stale`。

- [ ] **Step 4: 运行健康测试和 Ruff**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_factor_health.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/a_shares/factor_health.py apps/api/tests/a_shares/test_factor_health.py apps/api/src/qibao_api/contracts/quant_research.py
git commit -m "feat: calculate factor health truthfully"
```

### Task 3: 风险闸门与机会注册表

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_risk_gates.py`
- Create: `apps/api/src/qibao_api/a_shares/opportunity_registry.py`
- Test: `apps/api/tests/a_shares/test_quant_risk_gates.py`
- Test: `apps/api/tests/a_shares/test_opportunity_registry.py`

**Interfaces:**
- Consumes: `QuantStrategyCandidate` 和可选财务/可交易性证据。
- Produces: `evaluate_risk_gates()` 与 `build_default_opportunity_registry()`。

- [ ] **Step 1: 写 block/unavailable 和七类唯一注册失败测试**

```python
def test_missing_financial_fields_are_unavailable_not_pass() -> None:
    result = evaluate_risk_gates(candidate(), financial_fields=None)
    assert gate(result, "financial_anomaly").status == "unavailable"

def test_default_opportunities_have_unique_type_specific_invalidations() -> None:
    items = build_default_opportunity_registry().definitions()
    assert len(items) == 7
    assert len({item.opportunity_id for item in items}) == 7
    assert all(item.invalidation_rules for item in items)
```

- [ ] **Step 2: 运行并确认失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_risk_gates.py apps/api/tests/a_shares/test_opportunity_registry.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现五道独立闸门和七类配置**

```python
def overall_gate_status(checks: Sequence[RiskGateCheck]) -> str:
    if any(item.status == "block" for item in checks):
        return "block"
    if any(item.status in {"warn", "unavailable"} for item in checks):
        return "warn"
    return "pass"
```

- [ ] **Step 4: 运行聚焦测试**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_risk_gates.py apps/api/tests/a_shares/test_opportunity_registry.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/a_shares/quant_risk_gates.py apps/api/src/qibao_api/a_shares/opportunity_registry.py apps/api/tests/a_shares/test_quant_risk_gates.py apps/api/tests/a_shares/test_opportunity_registry.py apps/api/src/qibao_api/contracts/quant_research.py
git commit -m "feat: add quant risk gates and opportunities"
```

### Task 4: 可追溯 Pitch 与聚合快照

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_research_intelligence.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_research_snapshot.py`
- Test: `apps/api/tests/a_shares/test_quant_research_intelligence.py`
- Test: `apps/api/tests/a_shares/test_quant_research_snapshot.py`

**Interfaces:**
- Consumes: `QuantStrategyDashboard`、因子注册/健康、风险闸门、机会定义、影子统计。
- Produces: `QuantResearchSnapshot` 和 `QuantResearchSnapshotStore.load/save`。

- [ ] **Step 1: 写样本不足禁止胜率和局部失败隔离测试**

```python
def test_pitch_never_turns_strategy_score_into_probability() -> None:
    result = build_research_snapshot(strategy_dashboard(), shadow_analytics(sample_count=3))
    assert result.opportunities[0].calibrated_hit_rate_percent is None
    assert "成熟样本不足" in result.opportunities[0].limitations

def test_snapshot_store_keeps_last_good_when_refresh_fails(tmp_path) -> None:
    store = QuantResearchSnapshotStore(tmp_path / "quant-research.json")
    store.save(READY)
    assert store.load() == READY
```

- [ ] **Step 2: 运行并确认失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_research_intelligence.py apps/api/tests/a_shares/test_quant_research_snapshot.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现纯函数聚合和原子 JSON 快照**

```python
class QuantResearchIntelligenceService:
    def current(self, now: datetime) -> QuantResearchSnapshot:
        cached = self.snapshot_store.load()
        if cached is not None:
            self.refresh_executor.submit(self.refresh, now)
            return cached
        return self.empty_snapshot(now, "研究快照正在后台建立")
```

冷启动无快照时返回结构完整的 `insufficient`，不在 GET 请求内启动全市场扫描。

- [ ] **Step 4: 运行聚焦测试**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_research_intelligence.py apps/api/tests/a_shares/test_quant_research_snapshot.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/a_shares/quant_research_intelligence.py apps/api/src/qibao_api/a_shares/quant_research_snapshot.py apps/api/tests/a_shares/test_quant_research_intelligence.py apps/api/tests/a_shares/test_quant_research_snapshot.py
git commit -m "feat: build traceable quant research snapshot"
```

### Task 5: 60 日影子验证与来源分组

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/quant_shadow.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_shadow_ledger.py`
- Modify: `apps/api/src/qibao_api/routes/quant_strategy.py`
- Test: `apps/api/tests/a_shares/test_quant_shadow_ledger.py`
- Test: `apps/api/tests/routes/test_quant_strategy.py`

**Interfaces:**
- Produces: `HORIZONS=(1,3,5,10,20,60)`、`decision_source`、`opportunity_type` 和 cohort analytics。

- [ ] **Step 1: 写旧库迁移、60 日 pending/ready 与来源筛选失败测试**

```python
def test_existing_database_is_migrated_with_60_day_pending_outcome(tmp_path) -> None:
    store = legacy_store(tmp_path)
    record = store.get(LEGACY_ID)
    assert record.decision_source == "quant_strategy"
    assert [item.horizon for item in record.outcomes] == [1, 3, 5, 10, 20, 60]
```

- [ ] **Step 2: 运行并确认失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_shadow_ledger.py apps/api/tests/routes/test_quant_strategy.py -q`
Expected: FAIL。

- [ ] **Step 3: 增量迁移字段和结果，不改写冻结 JSON**

```python
if "decision_source" not in columns:
    connection.execute(
        "ALTER TABLE quant_shadow_decisions ADD COLUMN decision_source TEXT NOT NULL DEFAULT 'quant_strategy'"
    )
connection.execute(
    "INSERT OR IGNORE INTO quant_shadow_outcomes(decision_id,horizon,status,invalidation_state) "
    "SELECT decision_id,60,'pending','unavailable' FROM quant_shadow_decisions"
)
```

- [ ] **Step 4: 运行账本、校准和路由回归**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_quant_shadow_ledger.py apps/api/tests/a_shares/test_quant_calibration.py apps/api/tests/routes/test_quant_strategy.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/contracts/quant_shadow.py apps/api/src/qibao_api/a_shares/quant_shadow_ledger.py apps/api/src/qibao_api/routes/quant_strategy.py apps/api/tests/a_shares/test_quant_shadow_ledger.py apps/api/tests/routes/test_quant_strategy.py
git commit -m "feat: track sixty day quant outcomes"
```

### Task 6: ETF 暴露与 AI 可证伪假设

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/etf_exposure.py`
- Create: `apps/api/src/qibao_api/a_shares/factor_hypotheses.py`
- Test: `apps/api/tests/a_shares/test_etf_exposure.py`
- Test: `apps/api/tests/a_shares/test_factor_hypotheses.py`

**Interfaces:**
- Produces: `map_etf_exposures()`、`FactorHypothesisStore.append()` 和 `validate_hypothesis_contract()`。

- [ ] **Step 1: 写 ETF 最小样本和 AI 无权自批通过测试**

```python
def test_etf_correlation_requires_sixty_common_trade_days() -> None:
    result = map_etf_exposures(candidate_returns(59), ETF_DIRECTORY)
    assert result.status == "insufficient"
    assert result.exposures == ()

def test_ai_hypothesis_cannot_be_created_as_accepted() -> None:
    with pytest.raises(ValueError, match="deterministic validation"):
        FactorHypothesisCreate(status="accepted", **VALID_FIELDS)
```

- [ ] **Step 2: 运行并确认失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_etf_exposure.py apps/api/tests/a_shares/test_factor_hypotheses.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现真实相关性门槛和追加式假设记录**

ETF 结果必须具有代码、名称、共同样本数、流动性和来源；缺目录时返回 `unavailable`。假设创建仅允许 `draft`，验证结果包含 PIT、walk-forward、费用和 FDR 检查状态。

- [ ] **Step 4: 运行聚焦测试**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/a_shares/test_etf_exposure.py apps/api/tests/a_shares/test_factor_hypotheses.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/a_shares/etf_exposure.py apps/api/src/qibao_api/a_shares/factor_hypotheses.py apps/api/tests/a_shares/test_etf_exposure.py apps/api/tests/a_shares/test_factor_hypotheses.py apps/api/src/qibao_api/contracts/quant_research.py
git commit -m "feat: add etf exposure and factor hypotheses"
```

### Task 7: API 注入和非阻塞读取

**Files:**
- Create: `apps/api/src/qibao_api/routes/quant_research.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/routes/test_quant_research.py`
- Test: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: `GET /api/v1/a-shares/quant-research`。

- [ ] **Step 1: 写快照读取、中文错误和启动不扫描测试**

```python
def test_quant_research_route_returns_cached_snapshot(client) -> None:
    response = client.get("/api/v1/a-shares/quant-research")
    assert response.status_code == 200
    assert response.json()["formula_version"] == "quant-research-intelligence-v1"
```

- [ ] **Step 2: 运行并确认 404 失败**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/routes/test_quant_research.py -q`
Expected: FAIL，状态码 404。

- [ ] **Step 3: 注入轻量服务、注册路由和后台刷新任务**

GET 路由只调用 `service.current(now)`；初始化只打开快照文件和现有 SQLite，不计算 RankIC 或 ETF 相关性。

- [ ] **Step 4: 运行路由与冷启动回归**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/routes/test_quant_research.py apps/api/tests/desktop/test_cold_imports.py apps/api/tests/libu_compliance/test_main_lifespan.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/api/src/qibao_api/routes/quant_research.py apps/api/src/qibao_api/dependencies.py apps/api/src/qibao_api/main.py apps/api/tests/routes/test_quant_research.py apps/api/tests/libu_compliance/test_main_lifespan.py
git commit -m "feat: expose cached quant research api"
```

### Task 8: 量化研究智能界面

**Files:**
- Create: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.tsx`
- Create: `apps/web/src/features/quant-analysis/QuantResearchIntelligencePanel.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/types.ts`
- Modify: `apps/web/src/features/quant-analysis/api.ts`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/quant-analysis.css`
- Modify: `apps/web/src/app/App.tsx`

**Interfaces:**
- Consumes: `QuantResearchSnapshot` 和 `loadQuantResearch()`。
- Produces: 因子健康、风险闸门、Pitch、60 日验证、ETF 和 AI 假设六区界面。

- [ ] **Step 1: 写缓存、局部失败、筛选和两位小数失败测试**

```tsx
it("keeps useful modules visible when ETF evidence is unavailable", async () => {
  render(<QuantResearchIntelligencePanel loadSnapshot={() => Promise.resolve(PARTIAL)} />);
  expect(await screen.findByText("因子健康")).toBeInTheDocument();
  expect(screen.getByText("ETF 映射暂不可用")).toBeInTheDocument();
  expect(screen.getByText("已加载最新研究快照，实时监控中")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行并确认组件缺失失败**

Run: `pnpm --filter @qibao/web test -- QuantResearchIntelligencePanel.test.tsx`
Expected: FAIL。

- [ ] **Step 3: 实现无嵌套卡片的响应式研究面板**

使用紧凑指标条、状态标签、风险闸门行和 Pitch 列表；点击机会类型筛选候选。状态文字与颜色同时存在，A 股涨跌保持红涨绿跌。读取过程保留旧快照，失败展示中文模块原因。

- [ ] **Step 4: 运行组件、量化页和生产构建**

Run: `pnpm --filter @qibao/web test -- QuantResearchIntelligencePanel.test.tsx QuantAnalysisDashboard.test.tsx`
Expected: PASS。

Run: `pnpm build`
Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add apps/web/src/features/quant-analysis apps/web/src/app/App.tsx
git commit -m "feat: add quant research intelligence panel"
```

### Task 9: 全量验证、便携 EXE 与记忆更新

**Files:**
- Modify: `docs/verification/2026-08-21-quant-research-intelligence.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

**Interfaces:**
- Produces: 可复现验证记录和最终 EXE。

- [ ] **Step 1: 运行 API 全量测试**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q`
Expected: PASS。

- [ ] **Step 2: 运行静态检查和 Web 全量测试**

Run: `apps/api/.venv/Scripts/ruff.exe check apps/api`
Expected: PASS。

Run: `pnpm test:web`
Expected: PASS。

Run: `pnpm build`
Expected: PASS。

- [ ] **Step 3: UTF-8、乱码与差异检查**

Run: `rg -n "ï¿½|Ã.|Â.|â€”|â€œ|â€|\?\?\?" apps/api/src apps/web/src docs/superpowers/specs/2026-08-21-quant-research-intelligence-design.md docs/superpowers/plans/2026-08-21-quant-research-intelligence.md`
Expected: 无新增乱码命中。

Run: `git diff --check`
Expected: PASS。

- [ ] **Step 4: 重建并验证真实 EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`
Expected: 构建成功且八个持久目录保留。

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`
Expected: EXE 窗口、API、关键量化接口和发布质量门禁通过。

- [ ] **Step 5: 写入验证记录与脱敏项目记忆并提交**

```powershell
git add docs/verification/2026-08-21-quant-research-intelligence.md
git commit -m "docs: verify quant research intelligence release"
```
