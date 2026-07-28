# Kronos Signal Consensus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在量化分析页实现可复现的八信号等权投票、A 股硬风控、波动率缩放仓位参考和对应的样本外回测。

**Architecture:** 新建独立 `quant_consensus` 领域，由八个信号评估器生成离散票值，纯函数引擎执行 `R(t) = Rmax * (1/J) * sum(s_j(t))`，风险缩放器只在投票之后限制参考仓位。服务层冻结输入与结果快照，API 和 React 页面只展示后端事实；AI 解释与机械计算隔离。

**Tech Stack:** Python 3.12、FastAPI、Pydantic 2、SQLite、pytest、React 19、TypeScript 5.8、ECharts 5.6、Vitest、PyInstaller onedir。

## Global Constraints

- 固定八个信号家族等权投票，策略版本为 `consensus-v1`。
- 信号只能返回 `-1`、`0`、`+1`；缺失证据返回 `0` 且状态必须为 `unavailable`。
- Kronos 只是一票，不能直接生成买卖或绕过硬风控。
- A 股只做多；不生成期货、融券、杠杆或自动下单指令。
- 默认单票最大参考仓位 `10%`，信号覆盖率低于 `75%` 时参考仓位必须为 `0`。
- 回测必须避免未来数据泄漏，并计入 T+1、100 股整数手、费用、滑点、涨跌停和停牌无法成交。
- 真实缺失数据必须明确展示，不得用随机值、估算值或动画冒充实时数据。
- 保留现有 `/api/v1/a-shares/first-limit-up/quant-forecast` 路由，避免已有调用失效。
- 不恢复模拟资金账户；回测名义本金只用于归一化净值和交易成本计算。
- 修改中文文件后必须运行乱码扫描、聚焦测试、完整测试和生产构建。

---

### Task 1: Define the consensus contract and pure vote formula

**Files:**
- Create: `apps/api/src/qibao_api/contracts/quant_consensus.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/__init__.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/policy.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/engine.py`
- Test: `apps/api/tests/contracts/test_quant_consensus.py`
- Test: `apps/api/tests/a_shares/quant_consensus/test_engine.py`

**Interfaces:**
- Produces: `SignalVote`, `ConsensusTally`, `ConsensusValidation`, `QuantConsensusResponse`, `ConsensusPolicy` and `ConsensusVoteEngine.calculate(votes)`.
- `SignalVote.vote` is `Literal[-1, 0, 1]`; `SignalVote.status` is `ready | neutral | unavailable`.
- `ConsensusVoteEngine` always divides by `policy.signal_count == 8`, including unavailable votes as zero.

- [ ] **Step 1: Write failing contract tests**

```python
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.quant_consensus import SignalVote


def test_signal_vote_rejects_values_outside_discrete_ballot() -> None:
    with pytest.raises(ValidationError):
        SignalVote(
            signal_id="trend",
            family="trend",
            vote=2,
            status="ready",
            reason_code="trend_up",
            evidence={},
            source_snapshot_ids=("bars-1",),
            observed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        )


def test_unavailable_vote_must_be_zero() -> None:
    with pytest.raises(ValidationError):
        SignalVote(
            signal_id="kronos_path",
            family="kronos_path",
            vote=1,
            status="unavailable",
            reason_code="kronos_disabled",
            evidence={},
            source_snapshot_ids=(),
            observed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        )
```

- [ ] **Step 2: Run the contract tests and confirm the missing module failure**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/contracts/test_quant_consensus.py -q`

Expected: FAIL with `ModuleNotFoundError: qibao_api.contracts.quant_consensus`.

- [ ] **Step 3: Implement the immutable Pydantic contracts and fixed policy**

Create `SignalVote` with fields `signal_id`, `family`, `vote`, `status`, `reason_code`, `evidence`, `source_snapshot_ids`, `observed_at`; add a model validator enforcing `unavailable => vote == 0`. Define `ConsensusTally` with `long_count`, `short_count`, `neutral_count`, `unavailable_count`, `available_count`, `coverage_percent`, `consensus`, and `vote_risk_percent`. Define `ConsensusValidation` with `status: validated | insufficient | failed`, `oos_closed_trade_count`, optional `oos_ev`, optional `oos_max_drawdown_percent`, and `policy_version`. Define `QuantConsensusResponse` with the complete API fields from the design spec.

`policy.py` must expose exactly:

```python
from dataclasses import dataclass
from decimal import Decimal

SIGNAL_IDS = (
    "kronos_path", "trend", "momentum", "relative_strength",
    "volume_price", "first_limit_structure", "market_sentiment", "fund_flow",
)


@dataclass(frozen=True)
class ConsensusPolicy:
    version: str = "consensus-v1"
    signal_count: int = 8
    max_position_percent: Decimal = Decimal("10")
    minimum_coverage_percent: Decimal = Decimal("75")
    target_volatility_percent: Decimal = Decimal("20")
    volatility_floor_percent: Decimal = Decimal("10")
```

- [ ] **Step 4: Write failing formula tests**

```python
from datetime import datetime, timezone
from decimal import Decimal

from qibao_api.a_shares.quant_consensus.engine import ConsensusVoteEngine
from qibao_api.a_shares.quant_consensus.policy import ConsensusPolicy, SIGNAL_IDS
from qibao_api.contracts.quant_consensus import SignalVote


def votes(*values: int, unavailable: set[int] | None = None) -> tuple[SignalVote, ...]:
    missing = unavailable or set()
    observed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    return tuple(
        SignalVote(
            signal_id=signal_id,
            family=signal_id,
            vote=value,
            status="unavailable" if index in missing else ("neutral" if value == 0 else "ready"),
            reason_code="fixture",
            evidence={},
            source_snapshot_ids=() if index in missing else (f"source-{index}",),
            observed_at=observed_at,
        )
        for index, (signal_id, value) in enumerate(zip(SIGNAL_IDS, values, strict=True))
    )


def test_four_long_two_short_two_neutral_votes_produce_twenty_five_percent_consensus():
    result = ConsensusVoteEngine(ConsensusPolicy()).calculate(
        votes(1, 1, 1, 1, -1, -1, 0, 0)
    )
    assert result.consensus == Decimal("0.2500")
    assert result.vote_risk_percent == Decimal("2.5000")
    assert result.long_count == 4
    assert result.short_count == 2


def test_unavailable_vote_remains_in_fixed_denominator_and_reduces_coverage():
    ballot = votes(1, 1, 1, 1, 1, 1, 0, 0, unavailable={6, 7})
    result = ConsensusVoteEngine(ConsensusPolicy()).calculate(ballot)
    assert result.consensus == Decimal("0.7500")
    assert result.coverage_percent == Decimal("75.00")
    assert result.unavailable_count == 2
```

- [ ] **Step 5: Implement and verify the pure engine**

The engine must reject duplicate or unknown signal IDs, require exactly the eight configured IDs, calculate with `Decimal`, and quantize consensus/risk to four decimal places. Run:

`cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/contracts/test_quant_consensus.py tests/a_shares/quant_consensus/test_engine.py -q`

Expected: PASS.

- [ ] **Step 6: Commit this independently reviewable unit**

```powershell
git add apps/api/src/qibao_api/contracts/quant_consensus.py apps/api/src/qibao_api/a_shares/quant_consensus apps/api/tests/contracts/test_quant_consensus.py apps/api/tests/a_shares/quant_consensus/test_engine.py
git commit -m "feat: add deterministic quant consensus formula"
```

### Task 2: Implement the eight independent signal evaluators

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/inputs.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/kronos_path.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/trend.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/momentum.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/relative_strength.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/volume_price.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/first_limit_structure.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/market_sentiment.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/signals/fund_flow.py`
- Test: `apps/api/tests/a_shares/quant_consensus/test_signals.py`

**Interfaces:**
- Consumes: existing `DailyBar`, `KronosForecastResponse`, `FirstLimitUpCandidate`, `MarketSentimentSnapshot`, and `FundFlowSnapshot`.
- Produces: one `SignalVote` per evaluator through `evaluate(inputs: QuantSignalInputs) -> SignalVote`.
- `QuantSignalInputs` is immutable and contains `symbol`, `as_of`, `observed_at`, stock bars, CSI 300 bars, optional Kronos/candidate/sentiment/fund-flow snapshots, and source IDs.

- [ ] **Step 1: Write table-driven failing tests for every boundary**

Tests must cover each row of the design table, especially exact thresholds `2%`, `45%`, `60%`, `5%`, volume ratios `1.2`/`3.0`, PE `0`/`50`, sentiment `40`/`60`/`80`, and missing evidence. Use one explicit assertion per evaluator:

```python
def test_kronos_path_votes_long_only_when_return_downside_and_dispersion_agree():
    vote = KronosPathSignal().evaluate(inputs(kronos=forecast(
        median="2.00", downside="45.00", dispersion="20.00"
    )))
    assert (vote.vote, vote.status, vote.reason_code) == (1, "ready", "kronos_bullish")


def test_missing_kronos_is_zero_but_not_neutral_evidence():
    vote = KronosPathSignal().evaluate(inputs(kronos=None))
    assert (vote.vote, vote.status) == (0, "unavailable")


def test_first_limit_up_day_never_casts_a_long_vote():
    vote = FirstLimitStructureSignal().evaluate(inputs(candidate=candidate(stage="limit_up_day")))
    assert vote.vote == 0
    assert vote.reason_code == "limit_up_day_no_buy"
```

- [ ] **Step 2: Run the focused signal tests and confirm all evaluators are absent**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus/test_signals.py -q`

Expected: FAIL on missing evaluator modules.

- [ ] **Step 3: Implement one evaluator per file with no network calls**

Each evaluator is a pure function over `QuantSignalInputs`. It must put the exact raw values used for the vote into `evidence`, preserve source snapshot IDs, and return a reason code rather than Chinese prose. `relative_strength.py` must return unavailable when either 20-day series is incomplete. `volume_price.py` must add `volume_spike_above_3x` as evidence but return neutral for a positive move above 3x.

- [ ] **Step 4: Prove signal-family independence in a registry test**

Add a registry tuple in `signals/__init__.py` and assert all eight `signal_id` and `family` values are unique and match `SIGNAL_IDS`. This prevents adding MACD as a ninth trend vote without an explicit policy version change.

- [ ] **Step 5: Run tests and commit**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus/test_signals.py -q`

Expected: PASS.

```powershell
git add apps/api/src/qibao_api/a_shares/quant_consensus/inputs.py apps/api/src/qibao_api/a_shares/quant_consensus/signals apps/api/tests/a_shares/quant_consensus/test_signals.py
git commit -m "feat: add eight auditable quant signal votes"
```

### Task 3: Add hard risk gates and volatility-scaled long-only position reference

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/risk_scaling.py`
- Test: `apps/api/tests/a_shares/quant_consensus/test_risk_scaling.py`

**Interfaces:**
- Consumes: `ConsensusTally`, realized 20-day annualized volatility, tradeability state, first-limit-up candidate, data freshness, and `ConsensusValidation`.
- Produces: `PositionReference(reference_position_percent, volatility_scale, hard_blocks, warnings)` through `PositionRiskScaler.calculate(*, tally, realized_volatility_percent, hard_blocks=())`.

- [ ] **Step 1: Write failing risk tests**

```python
from decimal import Decimal

import pytest

from qibao_api.a_shares.quant_consensus.policy import ConsensusPolicy
from qibao_api.a_shares.quant_consensus.risk_scaling import PositionRiskScaler
from qibao_api.contracts.quant_consensus import ConsensusTally


def scaler() -> PositionRiskScaler:
    return PositionRiskScaler(ConsensusPolicy())


def tally(*, consensus: str, coverage: str) -> ConsensusTally:
    value = Decimal(consensus)
    available = int(Decimal(coverage) * Decimal("8") / Decimal("100"))
    return ConsensusTally(
        long_count=available if value > 0 else 0,
        short_count=available if value < 0 else 0,
        neutral_count=available if value == 0 else 0,
        unavailable_count=8 - available,
        available_count=available,
        coverage_percent=Decimal(coverage),
        consensus=value,
        vote_risk_percent=value * Decimal("10"),
    )


def test_full_agreement_uses_full_single_stock_budget_not_full_capital():
    result = scaler().calculate(
        tally=tally(consensus="1", coverage="100"),
        realized_volatility_percent=Decimal("20"),
    )
    assert result.reference_position_percent == Decimal("10.00")


def test_negative_consensus_never_creates_short_position():
    result = scaler().calculate(
        tally=tally(consensus="-1", coverage="100"),
        realized_volatility_percent=Decimal("20"),
    )
    assert result.reference_position_percent == Decimal("0.00")


@pytest.mark.parametrize("block", [
    "limit_up_day_no_buy", "not_tradeable", "stale_quote", "pe_not_allowed",
    "history_insufficient", "oos_not_validated",
])
def test_every_hard_block_forces_zero_position(block):
    result = scaler().calculate(
        tally=tally(consensus="1", coverage="100"),
        realized_volatility_percent=Decimal("20"),
        hard_blocks=(block,),
    )
    assert result.reference_position_percent == Decimal("0.00")


def test_forty_percent_volatility_halves_the_vote_budget():
    result = scaler().calculate(
        tally=tally(consensus="1", coverage="100"),
        realized_volatility_percent=Decimal("40"),
    )
    assert result.volatility_scale == Decimal("0.5000")
    assert result.reference_position_percent == Decimal("5.00")
```

- [ ] **Step 2: Run the tests and confirm the missing scaler failure**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus/test_risk_scaling.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement the formula without hidden weights**

`risk_scaling.py` must implement only:

```python
volatility_scale = min(
    Decimal("1"),
    policy.target_volatility_percent
    / max(realized_volatility_percent, policy.volatility_floor_percent),
)
reference = max(Decimal("0"), tally.vote_risk_percent) * volatility_scale
reference = min(reference, policy.max_position_percent)
if tally.coverage_percent < policy.minimum_coverage_percent or hard_blocks:
    reference = Decimal("0")
```

Do not introduce Kelly sizing, AI confidence multipliers or per-signal weights in `consensus-v1`.

- [ ] **Step 4: Run tests and commit**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus/test_risk_scaling.py -q`

Expected: PASS.

```powershell
git add apps/api/src/qibao_api/a_shares/quant_consensus/risk_scaling.py apps/api/tests/a_shares/quant_consensus/test_risk_scaling.py
git commit -m "feat: scale consensus with A-share risk gates"
```

### Task 4: Build and freeze consensus snapshots from existing evidence

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/input_builder.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/repository.py`
- Create: `apps/api/src/qibao_api/a_shares/quant_consensus/service.py`
- Test: `apps/api/tests/a_shares/quant_consensus/test_repository.py`
- Test: `apps/api/tests/a_shares/quant_consensus/test_service.py`

**Interfaces:**
- Consumes: `BarRepository`, local CSI 300 bars, `KronosForecastService`, `FirstLimitUpService`, `MarketSentimentRepository`, `FundFlowRepository`, and trading calendar.
- Produces: `QuantConsensusService.analyze(symbol: str, as_of: date) -> QuantConsensusResponse`.
- Persists append-only snapshots in `data/quant-consensus.sqlite3` keyed by content hash and policy version.

- [ ] **Step 1: Write failing service tests with in-memory fakes**

Cover: all evidence ready; Kronos unavailable while seven other votes survive; stale market data; identical input produces identical `input_snapshot_hash`; a second call returns the frozen snapshot; and any hard block preserves the original tally while setting position to zero.

```python
async def test_kronos_failure_removes_only_one_available_vote():
    response = await service(kronos_status="unavailable").analyze(
        "600519", as_of=date(2026, 7, 28)
    )
    assert response.tally.unavailable_count == 1
    assert response.tally.available_count == 7
    assert len(response.votes) == 8
    assert next(v for v in response.votes if v.signal_id == "kronos_path").vote == 0
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus/test_repository.py tests/a_shares/quant_consensus/test_service.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement local-first orchestration**

The builder must read local daily bars first, never perform per-signal duplicate reads, and pass one frozen input object to all evaluators. Network-backed repositories may contribute only their latest already stored snapshot; the GET analysis path must not wait on Eastmoney. Kronos runs through its existing lazy service and failure is isolated.

- [ ] **Step 4: Implement append-only storage and integrity verification**

Store canonical JSON, SHA-256 input hash, SHA-256 result hash, policy version and generated timestamp. Add SQLite triggers rejecting UPDATE and DELETE, following the existing fund-flow repository pattern. On read, recompute the result hash and raise `QuantConsensusIntegrityError` on mismatch.

- [ ] **Step 5: Run focused tests and commit**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/a_shares/quant_consensus -q`

Expected: PASS.

```powershell
git add apps/api/src/qibao_api/a_shares/quant_consensus apps/api/tests/a_shares/quant_consensus
git commit -m "feat: build and freeze quant consensus snapshots"
```

### Task 5: Expose the consensus API without breaking the Kronos route

**Files:**
- Create: `apps/api/src/qibao_api/routes/quant_analysis.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/routes/test_quant_analysis.py`
- Modify: `apps/api/tests/libu_compliance/test_main_lifespan.py`

**Interfaces:**
- Produces: `GET /api/v1/a-shares/quant-analysis/{symbol}/consensus?as_of=YYYY-MM-DD`.
- Preserves: `GET /api/v1/a-shares/first-limit-up/quant-forecast` unchanged.

- [ ] **Step 1: Write failing route tests**

```python
def test_consensus_route_returns_the_service_snapshot(client, response, service):
    application.dependency_overrides[get_quant_consensus_service] = lambda: service
    result = client.get(
        "/api/v1/a-shares/quant-analysis/600519/consensus",
        params={"as_of": "2026-07-28"},
    )
    assert result.status_code == 200
    assert result.json()["policy_version"] == "consensus-v1"
    service.analyze.assert_awaited_once()


def test_future_cutoff_is_rejected(client):
    result = client.get(
        "/api/v1/a-shares/quant-analysis/600519/consensus",
        params={"as_of": "2026-07-29"},
    )
    assert result.status_code == 422
```

- [ ] **Step 2: Run route tests and confirm 404/missing dependency**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/routes/test_quant_analysis.py -q`

Expected: FAIL.

- [ ] **Step 3: Wire service lifecycle and route**

Initialize one repository and service in `lifespan`, attach them to `application.state`, close the repository in `finally`, add `get_quant_consensus_service`, and include `quant_analysis_router`. Do not trigger Kronos loading or network refresh during application startup.

- [ ] **Step 4: Run route and lifespan tests, then commit**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/routes/test_quant_analysis.py tests/routes/test_kronos_forecast.py tests/libu_compliance/test_main_lifespan.py -q`

Expected: PASS.

```powershell
git add apps/api/src/qibao_api/routes/quant_analysis.py apps/api/src/qibao_api/dependencies.py apps/api/src/qibao_api/main.py apps/api/tests/routes/test_quant_analysis.py apps/api/tests/libu_compliance/test_main_lifespan.py
git commit -m "feat: expose quant consensus evidence API"
```

### Task 6: Replace the placeholder position row with a professional consensus console

**Files:**
- Create: `apps/web/src/features/quant-analysis/consensusTypes.ts`
- Create: `apps/web/src/features/quant-analysis/consensusApi.ts`
- Create: `apps/web/src/features/quant-analysis/VoteConsensusPanel.tsx`
- Create: `apps/web/src/features/quant-analysis/VoteLedger.tsx`
- Create: `apps/web/src/features/quant-analysis/PositionReferencePanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/metrics.ts`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/quant-analysis/consensusApi.test.ts`
- Test: `apps/web/src/features/quant-analysis/VoteConsensusPanel.test.tsx`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.test.tsx`

**Interfaces:**
- Consumes: `QuantConsensusResponse` from Task 5.
- Produces: a full-width `共识投票台`, eight-row auditable ledger, and mechanical position derivation.

- [ ] **Step 1: Write API and component failure-state tests**

```tsx
it("shows the exact ballot and explains the ten-percent risk budget", () => {
  render(<VoteConsensusPanel response={readyConsensus()} />);
  expect(screen.getByText("5 票赞成")).toBeInTheDocument();
  expect(screen.getByText("1 票反对")).toBeInTheDocument();
  expect(screen.getByText("参考仓位 4.00%")).toBeInTheDocument();
  expect(screen.getByText(/不等于全部资金满仓/)).toBeInTheDocument();
});

it("keeps the vote visible when a hard block zeros the position", () => {
  render(<VoteConsensusPanel response={blockedConsensus("limit_up_day_no_buy")} />);
  expect(screen.getByText("涨停当日禁止买入")).toBeInTheDocument();
  expect(screen.getByText("参考仓位 0.00%")).toBeInTheDocument();
  expect(screen.getByText("5 票赞成")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused Web tests and confirm missing components**

Run: `pnpm --dir apps/web test -- src/features/quant-analysis/consensusApi.test.ts src/features/quant-analysis/VoteConsensusPanel.test.tsx`

Expected: FAIL.

- [ ] **Step 3: Implement typed API and display components**

The frontend must never recalculate votes or position. It formats server decimals, maps reason codes to beginner-friendly Chinese, and shows source time/snapshot IDs in expandable rows. Remove the hardcoded `position: "--"` entry from `signalMetrics`; keep VOL、SCORE、胜率、赔率、风险、EV as context metrics and let the new panel own position.

- [ ] **Step 4: Integrate loading and failure isolation**

Changing the selected stock must abort the prior consensus request and load the new one. Consensus failure must not blank TICK、因子、回测或 Kronos panels. Use the existing gold/cyan/magenta palette, Orbitron headings, JetBrains Mono data, mobile single-column layout, focus-visible states and `prefers-reduced-motion`.

- [ ] **Step 5: Run focused tests and build, then commit**

Run: `pnpm --dir apps/web test -- src/features/quant-analysis`

Run: `pnpm --dir apps/web build`

Expected: all tests PASS and Vite build succeeds.

```powershell
git add apps/web/src/features/quant-analysis apps/web/src/app/App.tsx apps/web/src/app/theme.css
git commit -m "feat: show auditable signal consensus dashboard"
```

### Task 7: Add a dedicated consensus-vote backtest and validation gate

**Files:**
- Create: `apps/api/src/qibao_api/contracts/consensus_backtest.py`
- Create: `apps/api/src/qibao_api/zhongshu/consensus_backtest.py`
- Modify: `apps/api/src/qibao_api/routes/quant_analysis.py`
- Test: `apps/api/tests/zhongshu/test_consensus_backtest.py`
- Modify: `apps/api/tests/routes/test_quant_analysis.py`
- Create: `apps/web/src/features/quant-analysis/ConsensusBacktestPanel.tsx`
- Modify: `apps/web/src/features/quant-analysis/consensusTypes.ts`
- Modify: `apps/web/src/features/quant-analysis/consensusApi.ts`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Test: `apps/web/src/features/quant-analysis/ConsensusBacktestPanel.test.tsx`

**Interfaces:**
- Produces: `POST /api/v1/a-shares/quant-analysis/{symbol}/backtests` with strategy fixed to `consensus_vote_v1`.
- Produces: `ConsensusBacktestResult` with net-value curve, benchmark curve, Alpha, maximum drawdown, volatility, win rate, odds, EV, turnover, costs, unfilled counts, time segments and validation status.

- [ ] **Step 1: Write no-lookahead and A-share execution tests**

```python
def test_close_vote_executes_no_earlier_than_next_tradeable_open():
    result = engine.run(request(), bars(), frozen_votes())
    first = result.trades[0]
    assert first.signal_date == date(2026, 1, 5)
    assert first.trade_date == date(2026, 1, 6)


def test_same_day_sell_is_rejected_by_t_plus_one():
    result = engine.run(request(), bars_with_same_day_reversal(), frozen_votes())
    assert "t_plus_one_sell_blocked" in result.execution_warnings


def test_limit_up_buy_and_limit_down_sell_are_recorded_as_unfilled():
    result = engine.run(request(), limit_locked_bars(), frozen_votes())
    assert result.unfilled_buy_count == 1
    assert result.unfilled_sell_count == 1


def test_oos_with_fewer_than_twenty_closed_trades_is_not_validated():
    result = engine.run(request(), bars(), frozen_votes())
    assert result.validation.status == "insufficient"
```

- [ ] **Step 2: Run tests and verify the new engine is absent**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/zhongshu/test_consensus_backtest.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement variable target-position execution**

Use each frozen daily consensus as the next session target percentage. Round buys and sells to 100-share lots, track acquisition date for T+1, reject locked-limit and suspended sessions, and include commission, sell stamp duty and slippage as separate fields. Do not reuse the `sma_cross` signal generator.

- [ ] **Step 4: Implement chronological validation**

Use 60% train, 20% validation, 20% out-of-sample splits. The policy thresholds remain fixed for this version; the split is for reporting and gating, not runtime optimization. Set validation to `validated` only when OOS has at least 20 closed trades, EV > 0, and max drawdown <= 25%. Calculate Alpha against locally stored CSI 300 bars over the identical OOS date range.

- [ ] **Step 5: Expose and render the actual strategy results**

Replace the quant page's use of `sma_cross` metrics with `consensus_vote_v1` results. Show “样本不足” instead of green success when the validation gate fails. Keep the existing general backtest route and `BacktestPanel` unchanged for other pages.

- [ ] **Step 6: Run focused API/Web tests and commit**

Run: `cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest tests/zhongshu/test_consensus_backtest.py tests/routes/test_quant_analysis.py -q`

Run: `pnpm --dir apps/web test -- src/features/quant-analysis`

Expected: PASS.

```powershell
git add apps/api/src/qibao_api/contracts/consensus_backtest.py apps/api/src/qibao_api/zhongshu/consensus_backtest.py apps/api/src/qibao_api/routes/quant_analysis.py apps/api/tests/zhongshu/test_consensus_backtest.py apps/api/tests/routes/test_quant_analysis.py apps/web/src/features/quant-analysis
git commit -m "feat: backtest consensus voting with A-share rules"
```

### Task 8: Complete regression, encoding, performance and portable EXE verification

**Files:**
- Modify: `README.md` only if the existing user edits can be preserved line-for-line while adding the consensus formula and data requirements.
- Modify: `docs/roadmap.md` only around the quant-consensus milestone.

**Interfaces:**
- Verifies all outputs from Tasks 1-7 and the portable desktop artifact.

- [ ] **Step 1: Run Python formatting and the complete isolated backend suite**

```powershell
cd D:\Users\90090\Documents\金融财经\.worktrees\a-share-daily-research
.\.venv\Scripts\python.exe -m ruff check apps\api\src apps\api\tests
$env:QIBAO_DATA_DIR = Join-Path $env:TEMP ("qibao-test-" + [guid]::NewGuid().ToString("N"))
.\.venv\Scripts\python.exe -m pytest apps\api\tests -q
```

Expected: Ruff PASS and all backend tests PASS.

- [ ] **Step 2: Run complete frontend tests and production build**

```powershell
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Expected: all Vitest files PASS and Vite build succeeds.

- [ ] **Step 3: Scan touched Chinese files for mojibake and accidental replacement characters**

Run the repository's existing mojibake scan if present. Otherwise use `rg` against the exact touched paths for Unicode replacement characters and repeated question marks, then manually inspect every match. No automated rewrite is allowed.

- [ ] **Step 4: Verify deterministic math and API latency**

Call the same consensus endpoint twice for one frozen `symbol/as_of` and assert identical `input_snapshot_hash`, votes, consensus and reference position. With Kronos snapshot already cached, record 20 local calls; the median non-model aggregation time must stay below 100 ms. Report Kronos inference separately because model/device latency is not millisecond-class.

- [ ] **Step 5: Rebuild and smoke-test the portable directory**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run-portable-smoke.ps1
```

Expected: `Portable smoke passed` and `dist/XiaoQiBao-Portable/xiaoqibao.exe` exists with its embedded icon.

- [ ] **Step 6: Review the final diff and commit documentation separately**

```powershell
git diff --check
git status --short
git add docs/roadmap.md
git commit -m "docs: document quant consensus evidence model"
```

Do not stage unrelated user changes. If `README.md` cannot be isolated safely, leave it unstaged and report that explicitly.
