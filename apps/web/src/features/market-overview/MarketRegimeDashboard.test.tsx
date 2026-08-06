import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketRegimeDashboard } from "./MarketRegimeDashboard";
import type { OverviewRegimeAssessment, OverviewRegimeMetrics } from "./types";

const metrics: OverviewRegimeMetrics = {
  up_ratio: "66", zt_ratio: "1.4", dt_ratio: "0.1", median_ret: "1.2",
  amt_heat: "1.15", strong_close_ratio: "72", weak_close_ratio: "12",
  limit_fail_ratio: "18", panic_ratio: "2", amp_ratio: "18",
  net_positive_ratio: null, large_amount_strong_close_ratio: "70",
  factor_coverage_percent: "90.91",
};

const regime: OverviewRegimeAssessment = {
  regime: "情绪主升", emotion_score: "74.79", risk_score: "9.33",
  heat_score: "55", rotation_score: "18", coverage_percent: "85",
  market_coef: "1", suitable_strategies: ["0轴低吸模型", "分歧转一致模型"],
  avoid_strategies: ["后排追涨"], reasons: ["情绪分达到70且风险分低于45"],
  missing_factors: ["net_positive_ratio"], quality: "partial",
  rule_matched: true,
  formula_version: "a-share-short-regime-v2.0",
};

describe("MarketRegimeDashboard", () => {
  it("shows the audited factor model without inventing unavailable fund flow", () => {
    render(<MarketRegimeDashboard metrics={metrics} regime={regime} />);

    expect(screen.getByRole("region", { name: "A 股市场风格识别工作台" })).toHaveTextContent("情绪主升");
    expect(screen.getByText("A 股全市场实时因子")).toBeInTheDocument();
    expect(screen.getByText("0轴低吸模型")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /资金净流入率/ })).toHaveTextContent("暂无可信数据");
    expect(screen.getByText("85% 因子权重可用")).toBeInTheDocument();
    expect(screen.getByText("a-share-short-regime-v2.0")).toBeInTheDocument();
  });

  it("marks missing score and position values as unavailable instead of empty zero bars", () => {
    const incompleteRegime = { ...regime, emotion_score: null, market_coef: null, coverage_percent: null } as unknown as OverviewRegimeAssessment;
    render(<MarketRegimeDashboard metrics={metrics} regime={incompleteRegime} />);
    expect(screen.getByText("暂无可信数据")).toBeInTheDocument();
    expect(screen.getByText("--", { selector: ".regime-hero strong" })).toBeInTheDocument();
    expect(screen.getByText("情绪分").closest("article")).toHaveAttribute("data-state", "unavailable");
  });
});
