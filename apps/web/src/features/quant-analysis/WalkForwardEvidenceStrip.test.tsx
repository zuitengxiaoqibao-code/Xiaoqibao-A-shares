import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WalkForwardEvidenceStrip } from "./WalkForwardEvidenceStrip";
import type { WalkForwardReport } from "./types";


const ready: WalkForwardReport = {
  symbol: "600519",
  status: "ready",
  generated_at: "2026-08-15T08:00:00Z",
  source: "local-tdx",
  window_count: 4,
  windows: [],
  closed_trade_count: 12,
  minimum_closed_trades: 5,
  win_rate: "0.5833",
  profit_loss_ratio: "1.72",
  max_drawdown: "0.124",
  sharpe_ratio: "1.18",
  average_test_return: "0.041",
  strategy_score: "76.25",
  score_formula: "oos-v1",
  factor_decay: [],
  parameter_policy: "frozen_before_validation",
  out_of_sample_tuning: "prohibited",
  parameter_snapshot_hash: "a".repeat(64),
  limitations: ["survivorship_bias_unresolved"],
};


describe("WalkForwardEvidenceStrip", () => {
  it("shows only out-of-sample conclusion metrics for a ready report", () => {
    render(<WalkForwardEvidenceStrip report={ready} loading={false} error="" />);

    const panel = screen.getByRole("region", { name: "样本外滚动验证" });
    expect(panel).toHaveTextContent("4 个");
    expect(panel).toHaveTextContent("12 / 5 笔");
    expect(panel).toHaveTextContent("58.3%");
    expect(panel).toHaveTextContent("1.18");
    expect(panel).toHaveTextContent("12.4%");
    expect(panel).toHaveTextContent("76.25");
  });

  it("does not turn a partial report into a score", () => {
    render(<WalkForwardEvidenceStrip
      report={{
        ...ready,
        status: "partial",
        closed_trade_count: 2,
        win_rate: null,
        sharpe_ratio: null,
        strategy_score: null,
        limitations: ["closed_trade_sample_below_minimum"],
      }}
      loading={false}
      error=""
    />);

    const panel = screen.getByRole("region", { name: "样本外滚动验证" });
    expect(panel).toHaveTextContent("样本不足");
    expect(panel).toHaveTextContent("--");
  });
});
