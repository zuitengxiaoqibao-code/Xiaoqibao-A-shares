import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QuantResearchIntelligencePanel } from "./QuantResearchIntelligencePanel";
import type { QuantResearchSnapshot, QuantResearchStatus } from "./types";


const moduleStatus = (status: QuantResearchStatus, message: string) => ({ status, message });

const snapshot: QuantResearchSnapshot = {
  status: "partial",
  as_of: "2026-08-21",
  observed_at: "2026-08-21T07:00:00Z",
  generated_at: "2026-08-21T07:00:00Z",
  snapshot_source: "cache",
  refresh_state: "ready",
  refresh_progress: 100,
  refresh_stage: "已加载最新研究快照，实时监控中",
  formula_version: "quant-research-intelligence-v1",
  factor_registry: {
    status: "ready",
    as_of: "2026-08-21T07:00:00Z",
    formula_version: "quant-factor-registry-v1",
    limitations: [],
    factors: [{
      factor_id: "return_5d", name: "5日涨跌幅", family: "momentum",
      direction: "positive", required_fields: ["close"], minimum_history: 6,
      formula_version: "a-share-factors-v1", owner: "system", lifecycle: "active",
      registered_at: "2026-08-21T07:00:00Z", retired_at: null, retirement_reason: null,
    }],
  },
  factor_health: [],
  risk_summaries: [{
    symbol: "600001", overall_status: "warn", blockers: [], formula_version: "quant-risk-gates-v1",
    checks: [
      { key: "evidence", label: "证据完整性", status: "pass", reason: "证据完整", metric_value: "90", threshold: "80", source_snapshot_ids: [] },
      { key: "financial_anomaly", label: "财务异常", status: "unavailable", reason: "财务字段不完整", metric_value: null, threshold: null, source_snapshot_ids: [] },
    ],
  }],
  opportunities: [
    {
      symbol: "600001", name: "样本股份", opportunity_type: "trend_continuation", opportunity_name: "趋势延续",
      market_regime: "情绪主升", status: "watch", strategy_score: "82.126", trigger_confirmed: false,
      reference_price: "10.12", core_evidence: ["策略综合分 82.126", "证据覆盖 90%", "等待盘中触发确认"],
      trigger_rules: ["回踩关键均线后重新转强"], invalidation_rules: ["收盘有效跌破20日均线"],
      risk_gate: { symbol: "600001", overall_status: "warn", blockers: [], formula_version: "quant-risk-gates-v1", checks: [] },
      shadow_sample_count: 3, calibrated_hit_rate_percent: null, average_return_percent: null,
      sources: ["tdx-local-daily"], source_snapshot_ids: ["snapshot-1"], limitations: ["同类成熟样本不足 20 条，不展示校准胜率"],
    },
    {
      symbol: "600002", name: "突破股份", opportunity_type: "volume_breakout", opportunity_name: "放量突破",
      market_regime: "情绪主升", status: "triggered", strategy_score: "88", trigger_confirmed: true,
      reference_price: "15", core_evidence: ["突破证据完整"], trigger_rules: ["放量突破"], invalidation_rules: ["跌回前高下方"],
      risk_gate: { symbol: "600002", overall_status: "pass", blockers: [], formula_version: "quant-risk-gates-v1", checks: [] },
      shadow_sample_count: 25, calibrated_hit_rate_percent: "64.25", average_return_percent: "3.18",
      sources: ["tdx-local-daily"], source_snapshot_ids: ["snapshot-2"], limitations: [],
    },
  ],
  shadow_cohorts: [], etf_exposures: [], hypotheses: [], source_snapshot_ids: ["snapshot-1"],
  module_statuses: {
    factor_registry: moduleStatus("ready", "七个现有价量因子已纳入生命周期治理"),
    factor_health: moduleStatus("insufficient", "点时横截面样本正在积累"),
    risk: moduleStatus("partial", "风险分项检查完成"),
    opportunities: moduleStatus("partial", "已生成证据绑定的机会卡"),
    shadow: moduleStatus("insufficient", "60日样本正在积累"),
    etf: moduleStatus("unavailable", "ETF 映射暂不可用"),
    hypotheses: moduleStatus("unavailable", "当前没有待验证的 AI 因子假设"),
  },
  limitations: [],
};


describe("QuantResearchIntelligencePanel", () => {
  it("shows module truth states, readable pitches and rounded values", async () => {
    render(<QuantResearchIntelligencePanel load={vi.fn(async () => snapshot)} />);

    expect(await screen.findByText("研究智能")).toBeInTheDocument();
    expect(screen.getByText("已加载最新研究快照，实时监控中")).toBeInTheDocument();
    expect(screen.getAllByText("ETF 映射暂不可用").length).toBeGreaterThan(0);
    expect(screen.getByText("82.13")).toBeInTheDocument();
    expect(screen.getByText("样本不足，不显示胜率")).toBeInTheDocument();
    expect(screen.getByText("64.25%")).toBeInTheDocument();
  });

  it("filters pitch cards by opportunity type without hiding module evidence", async () => {
    render(<QuantResearchIntelligencePanel load={vi.fn(async () => snapshot)} />);
    await screen.findByText("样本股份");

    fireEvent.click(screen.getByRole("button", { name: "放量突破" }));

    expect(screen.queryByText("样本股份")).not.toBeInTheDocument();
    expect(screen.getByText("突破股份")).toBeInTheDocument();
    expect(screen.getAllByText("点时横截面样本正在积累").length).toBeGreaterThan(0);
  });

  it("uses a clear Chinese failure state", async () => {
    render(<QuantResearchIntelligencePanel load={vi.fn(async () => { throw new Error("down"); })} />);

    expect(await screen.findByText("量化研究快照加载失败")).toBeInTheDocument();
    expect(screen.getByText("请检查本地数据状态后重试；其他量化模块不受影响。")).toBeInTheDocument();
  });
});
