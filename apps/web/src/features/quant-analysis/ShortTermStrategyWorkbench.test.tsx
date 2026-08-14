import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { QuantStrategyDashboard } from "./types";
import { ShortTermStrategyWorkbench } from "./ShortTermStrategyWorkbench";

vi.mock("./QuantChart", () => ({
  QuantChart: ({ ariaLabel }: { ariaLabel: string }) => <div role="img" aria-label={ariaLabel} />,
}));

const dashboard: QuantStrategyDashboard = {
  status: "partial",
  as_of: "2026-07-31",
  observed_at: "2026-07-31T14:00:00+08:00",
  generated_at: "2026-07-31T14:00:00+08:00",
  market_observed_at: "2026-07-31T14:00:00+08:00",
  data_age_seconds: 0,
  refresh_mode: "live",
  next_refresh_at: "2026-07-31T14:00:05+08:00",
  candidate_scan_at: "2026-07-31T14:00:00+08:00",
  candidate_scan_age_seconds: 0,
  candidate_scan_cached: false,
  candidate_scan_state: "ready",
  candidate_scan_started_at: "2026-07-31T14:00:00+08:00",
  candidate_scan_error: null,
  candidate_scan_phase: "ready",
  candidate_scan_processed: null,
  candidate_scan_total: null,
  trigger_evidence_at: "2026-07-31T14:00:00+08:00",
  trigger_evidence_age_seconds: 0,
  trigger_evidence_cached: false,
  formula_version: "a-share-short-strategy-v2.0",
  metrics: {
    up_ratio: "66", zt_ratio: "1.4", dt_ratio: "0.1", median_ret: "1.2",
    amt_heat: "1.15", strong_close_ratio: "72", weak_close_ratio: "12",
    limit_fail_ratio: "18", panic_ratio: "2", amp_ratio: "18",
    net_positive_ratio: null, large_amount_strong_close_ratio: "70",
    factor_coverage_percent: "90.91",
  },
  regime: {
    regime: "情绪主升", emotion_score: "76", risk_score: "22", heat_score: "68",
    rotation_score: "35", coverage_percent: "85", market_coef: "1",
    suitable_strategies: ["0轴低吸模型", "分歧转一致模型"],
    avoid_strategies: ["后排追涨"], reasons: ["情绪分达到阈值"],
    missing_factors: ["net_positive_ratio"], rule_matched: true, quality: "partial",
    formula_version: "a-share-short-regime-v2.0",
  },
  strategy_models: [
    { name: "0轴低吸模型", applicable_regimes: ["情绪主升", "轮动震荡"], selected: true, defensive: false },
    { name: "恐慌低吸模型", applicable_regimes: ["冰点修复", "高位退潮"], selected: false, defensive: false },
    { name: "权重容量低吸模型", applicable_regimes: ["指数权重进攻"], selected: false, defensive: false },
    { name: "分歧转一致模型", applicable_regimes: ["情绪主升"], selected: true, defensive: false },
    { name: "反核修复模型", applicable_regimes: ["冰点修复"], selected: false, defensive: false },
    { name: "空仓防守模型", applicable_regimes: ["高位退潮", "缩量混沌"], selected: false, defensive: true },
  ],
  candidate_funnel: {
    stages: [
      { key: "universe", label: "全市场股票", count: 5000 },
      { key: "history_ready", label: "日线历史完整", count: 4700 },
      { key: "factor_ready", label: "因子计算完成", count: 4650 },
      { key: "liquidity_ready", label: "流动性达标", count: 4200 },
      { key: "ranked", label: "策略排名入选", count: 12 },
      { key: "trigger_confirmed", label: "盘中触发确认", count: 2 },
      { key: "final_candidates", label: "最终候选", count: 1 },
    ],
    exclusion_reasons: { insufficient_history: 300, insufficient_liquidity: 450 },
    completeness: "partial",
    blockers: ["incomplete_daily_history"],
  },
  field_evidence: [{
    field_path: "candidates.600001.strategy_score", value: "82.4", source: "tdx-local-daily / tdx-local-realtime",
    source_field: null, status: "derived", trade_date: "2026-07-31", observed_at: "2026-07-31T14:00:00+08:00",
    coverage_percent: "82", derived: true, formula: "a-share-short-strategy-v2.0", evidence_ids: [], limitations: [],
  }],
  candidates: [{
    symbol: "600001", name: "样本股份", model: "0轴低吸模型",
    strategy_score: "82.4", regime_match: "1", stock_score: "0.9",
    trigger_score: "0", rr_score: "0", risk_penalty: "4.9",
    status: "pending_trigger", trigger_confirmed: false, position: "0",
    planned_position: "0", evidence_coverage_percent: "82",
    vote_consensus: "0.20", vote_position: "0",
    signal_votes: [
      { signal: "市场风格", vote: 1, evidence_value: "1" },
      { signal: "个股质量", vote: 1, evidence_value: "0.9" },
      { signal: "盘中触发", vote: -1, evidence_value: "0" },
      { signal: "盈亏比", vote: -1, evidence_value: "0" },
      { signal: "风险约束", vote: 1, evidence_value: "0.84" },
    ],
    buy_triggers: ["涨跌幅位于 -1.5% 至 +2%", "3分钟涨幅转正"],
    invalidation_rules: ["跌破盘中均价且3分钟不能收回"], risk_flags: [],
    missing_evidence: ["three_minute_return", "net_large_flow"],
    alert_gate: {
      eligible: false,
      checks: [
        { key: "strategy_score", label: "策略分门槛", passed: true, detail: "82.40 / 80" },
        { key: "trigger_confirmed", label: "盘中触发确认", passed: false, detail: "尚未确认" },
        { key: "evidence_coverage", label: "证据覆盖", passed: false, detail: "82.00% / 90%" },
      ],
      blockers: ["盘中触发未确认", "证据覆盖低于90%"],
    },
    factor_as_of: "2026-07-31", sources: ["tdx-local-daily", "tdx-local-realtime"],
  }],
  discipline: "情绪主升：只做核心强股的分歧确认，不追后排和一致加速。",
  missing_data: ["net_positive_ratio"], warnings: [],
  sources: ["tdx-local-realtime", "tdx-local-daily"],
};

describe("ShortTermStrategyWorkbench", () => {
  it("shows the regime, four scores, eleven metrics and tagged recommendations", () => {
    render(<ShortTermStrategyWorkbench dashboard={dashboard} loading={false} error="" />);

    expect(screen.getByRole("heading", { name: "短线风格与策略" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "市场风格 情绪主升" })).toBeInTheDocument();
    const scores = screen.getByRole("region", { name: "市场风格评分" });
    for (const label of ["情绪分", "风险分", "热度分", "轮动分"]) {
      expect(within(scores).getByText(label)).toBeInTheDocument();
    }
    const metrics = screen.getByRole("region", { name: "全市场实时指标" });
    for (const label of [
      "上涨率", "涨停率", "跌停率", "中位涨幅", "成交热度", "强收比例",
      "弱收比例", "炸板弱收率", "恐慌率", "高波动率", "资金净流入率",
    ]) expect(within(metrics).getByText(label)).toBeInTheDocument();
    const candidate = screen.getByRole("article", { name: "600001 样本股份" });
    expect(candidate).toHaveTextContent("82.4");
    expect(candidate).toHaveTextContent("等待确认");
    expect(candidate).toHaveTextContent("0轴低吸模型");
    expect(candidate).toHaveTextContent("触发后仓位上限 0.0%");
    expect(candidate).toHaveTextContent("3分钟涨幅转正");
    expect(within(candidate).getByLabelText("信号投票仓位引擎")).toHaveTextContent("信号一致度 0.20");
    expect(within(candidate).getByLabelText("信号投票仓位引擎")).toHaveTextContent("R(t) = Rmax");
    const evidence = screen.getByRole("region", { name: "量化证据摘要" });
    expect(evidence).toHaveTextContent("全市场样本");
    expect(within(evidence).getByText("5,000")).toBeInTheDocument();
    expect(within(evidence).getByText("市场覆盖")).toBeInTheDocument();
    expect(within(evidence).getByText("因子覆盖")).toBeInTheDocument();
    expect(within(evidence).getByText("85%")).toBeInTheDocument();
    const alertGate = within(candidate).getByLabelText("严格提醒门槛");
    expect(alertGate).toHaveTextContent("盘中触发确认尚未确认");
    expect(alertGate).toHaveTextContent("证据覆盖82.00% / 90%");
    const modelPool = screen.getByRole("region", { name: "六模型策略池" });
    for (const model of dashboard.strategy_models) {
      expect(within(modelPool).getByText(model.name)).toBeInTheDocument();
    }
    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项推算");
  });

  it("keeps a defensive regime useful without inventing candidates", () => {
    const defensive = {
      ...dashboard,
      regime: { ...dashboard.regime, regime: "高位退潮" as const, market_coef: "0.2" },
      candidates: [],
      discipline: "高位退潮：默认空仓防守，只卖不买。",
    };
    render(<ShortTermStrategyWorkbench dashboard={defensive} loading={false} error="" />);

    expect(screen.getByText("当前不强行推荐股票")).toBeInTheDocument();
    expect(screen.getAllByText("高位退潮：默认空仓防守，只卖不买。")).toHaveLength(2);
  });

  it("shows an isolated error state", () => {
    render(<ShortTermStrategyWorkbench dashboard={null} loading={false} error="短线策略数据暂不可用" />);
    expect(screen.getByText("短线策略数据暂不可用")).toBeInTheDocument();
  });

  it("marks unavailable score bars explicitly", () => {
    const incomplete = {
      ...dashboard,
      regime: { ...dashboard.regime, emotion_score: null },
    } as unknown as QuantStrategyDashboard;
    render(<ShortTermStrategyWorkbench dashboard={incomplete} loading={false} error="" />);
    expect(screen.getByText("情绪分").closest("div")).toHaveAttribute("data-state", "unavailable");
  });
});
