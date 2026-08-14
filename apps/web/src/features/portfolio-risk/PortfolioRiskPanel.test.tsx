import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PortfolioRiskPanel } from "./PortfolioRiskPanel";


describe("PortfolioRiskPanel", () => {
  it("loads the locally persisted portfolio and removes it through the local store", async () => {
    const response = {
      status: "partial" as const,
      as_of: "2026-08-11",
      observed_at: "2026-08-11T16:00:00+08:00",
      total_market_value: null,
      total_cost: null,
      total_pnl: null,
      total_pnl_percent: null,
      hhi: null,
      average_correlation: null,
      market_regime: null,
      market_position_cap_percent: null,
      positions: [{ symbol: "600519", shares: "100", cost_price: "1500", current_price: null, market_value: null, pnl: null, pnl_percent: null, weight_percent: null, industry: null, status: "unavailable" as const, limitations: ["日线待补"] }],
      industries: [],
      high_correlation_pairs: [],
      stress_scenarios: [],
      warnings: ["日线待补"],
      sources: [],
    };
    const load = vi.fn(async () => response);
    const remove = vi.fn(async () => ({ ...response, positions: [] }));

    render(<PortfolioRiskPanel load={load} removePosition={remove} />);

    expect(await screen.findByDisplayValue("600519")).toBeInTheDocument();
    expect(screen.getByText("本地持仓已载入")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "删除持仓 1" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("600519"));
    expect(screen.queryByDisplayValue("600519")).not.toBeInTheDocument();
  });

  it("requires manual holdings and renders concentration, correlation and stress evidence", async () => {
    const analyze = vi.fn(async () => ({
      status: "ready" as const,
      as_of: "2026-08-11",
      observed_at: "2026-08-11T16:00:00+08:00",
      total_market_value: "3200.00",
      total_cost: "2450.00",
      total_pnl: "750.00",
      total_pnl_percent: "30.61",
      hhi: "5000.00",
      average_correlation: "0.9900",
      market_regime: "轮动震荡",
      market_position_cap_percent: "50.00",
      positions: [{ symbol: "600001", shares: "100", cost_price: "12", current_price: "16", market_value: "1600", pnl: "400", pnl_percent: "33.33", weight_percent: "50", industry: "银行", status: "ready" as const, limitations: [] }],
      industries: [{ industry: "银行", market_value: "3200", weight_percent: "100", symbols: ["600001", "600002"] }],
      high_correlation_pairs: [{ left_symbol: "600001", right_symbol: "600002", correlation: "0.99", overlap_days: 60 }],
      stress_scenarios: [{ key: "market_down_2" as const, label: "全市场下跌 2%", shock_percent: "-2", estimated_loss: "-64", status: "ready" as const, detail: "统一冲击" }],
      warnings: ["最大行业权重超过 35%"],
      sources: ["tdx-local-daily"],
    }));
    render(<PortfolioRiskPanel analyze={analyze} />);

    expect(screen.getByText("请先录入真实持仓")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "添加持仓" }));
    fireEvent.change(screen.getByLabelText("股票代码 1"), { target: { value: "600001" } });
    fireEvent.change(screen.getByLabelText("持股数量 1"), { target: { value: "100" } });
    fireEvent.change(screen.getByLabelText("成本价 1"), { target: { value: "12" } });
    fireEvent.click(screen.getByRole("button", { name: "计算组合风险" }));

    await waitFor(() => expect(analyze).toHaveBeenCalledWith({ positions: [{ symbol: "600001", shares: "100", cost_price: "12" }] }));
    expect(await screen.findByText("组合市值")).toBeInTheDocument();
    expect(screen.getByText("银行 100.00%")).toBeInTheDocument();
    expect(screen.getByText("600001 / 600002")).toBeInTheDocument();
    expect(screen.getByText("全市场下跌 2%" )).toBeInTheDocument();
  });
});
