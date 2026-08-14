import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WatchlistRiskPanel } from "./WatchlistRiskPanel";

describe("WatchlistRiskPanel", () => {
  it("labels selected stocks as an observation basket instead of holdings", async () => {
    render(<WatchlistRiskPanel symbols={["600519"]} load={async () => ({
      mode: "observation_basket", status: "partial", as_of: "2026-08-14", observed_at: "2026-08-14T08:00:00Z",
      valid_count: 1, total_count: 1, coverage_percent: "100", items: [{ symbol: "600519", name: "贵州茅台", industry: "白酒", sectors: ["消费"], volatility_20d_percent: "2.50", return_sample_count: 20, status: "ready", limitations: [] }], industries: [{ label: "白酒", symbol_count: 1, observation_weight_percent: "100", symbols: ["600519"] }], themes: [], high_correlation_pairs: [], warnings: [], sources: ["tdx-local"],
    })} />);
    expect(await screen.findByRole("region", { name: "观察篮子风险" })).toHaveTextContent("观察篮子");
    expect(screen.getByText(/不代表真实持仓/)).toBeInTheDocument();
  });
});
