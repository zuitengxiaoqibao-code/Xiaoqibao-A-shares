import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BacktestPanel } from "./BacktestPanel";
import type { BacktestResult } from "./types";

const result: BacktestResult = {
  symbol: "600000", strategy: "sma_cross", initial_cash: "100000",
  ending_equity: "76206.79", total_return: "-0.2379", max_drawdown: "0.2520",
  total_cost: "937.21", trades: Array.from({ length: 14 }, (_, index) => ({ side: index % 2 ? "sell" as const : "buy" as const, signal_date: "2025-01-01", trade_date: "2025-01-02", price: "10.00", shares: 100, gross_amount: "1000.00", fees: "0.30", stamp_duty: index % 2 ? "0.50" : "0" })),
  metrics: { annualized_return: "-0.1540", annualized_volatility: "0.1825", sharpe_ratio: "-0.8400", calmar_ratio: "-0.6111", win_rate: "0.4286", profit_loss_ratio: "1.2400", turnover_rate: "3.2500", closed_trade_count: 7, expected_value: "-320.50", max_consecutive_losses: 3 },
  segments: [
    { name: "train" as const, start_date: "2024-01-01", end_date: "2024-12-31", bar_count: 240, starting_equity: "100000", ending_equity: "110000", total_return: "0.1000", max_drawdown: "0.1200" },
    { name: "validation" as const, start_date: "2025-01-01", end_date: "2025-04-30", bar_count: 80, starting_equity: "110000", ending_equity: "107800", total_return: "-0.0200", max_drawdown: "0.0800" },
    { name: "out_of_sample" as const, start_date: "2025-05-01", end_date: "2025-08-31", bar_count: 80, starting_equity: "107800", ending_equity: "111034", total_return: "0.0300", max_drawdown: "0.0600" },
  ],
  rolling_windows: [
    { name: "early", start_date: "2024-01-01", end_date: "2024-08-01", bar_count: 150, starting_equity: "100000", ending_equity: "106000", total_return: "0.0600", max_drawdown: "0.0800", evaluation_status: "available" },
    { name: "middle", start_date: "2024-05-01", end_date: "2025-01-01", bar_count: 150, starting_equity: "104000", ending_equity: "101000", total_return: "-0.0288", max_drawdown: "0.1100", evaluation_status: "available" },
    { name: "recent", start_date: "2024-09-01", end_date: "2025-08-31", bar_count: 150, starting_equity: "101000", ending_equity: "111034", total_return: "0.0993", max_drawdown: "0.0600", evaluation_status: "available" },
  ],
  market_regimes: [
    { name: "bull" as const, bar_count: 120, total_return: "0.1200", closed_trade_count: 3, win_rate: "0.6667", expected_value: "820", profit_loss_ratio: "1.80", max_consecutive_losses: 1 },
    { name: "bear" as const, bar_count: 90, total_return: "-0.1800", closed_trade_count: 2, win_rate: "0", expected_value: "-910", profit_loss_ratio: null, max_consecutive_losses: 2 },
    { name: "sideways" as const, bar_count: 170, total_return: "0.0100", closed_trade_count: 2, win_rate: "0.5", expected_value: "25", profit_loss_ratio: "1.05", max_consecutive_losses: 1 },
  ],
  signal_decay: [
    { horizon: 1, sample_count: 7, average_return: "0.0080", hit_rate: "0.5714" },
    { horizon: 3, sample_count: 7, average_return: "0.0120", hit_rate: "0.5714" },
    { horizon: 5, sample_count: 7, average_return: "0.0040", hit_rate: "0.4286" },
    { horizon: 10, sample_count: 6, average_return: "-0.0060", hit_rate: "0.3333" },
    { horizon: 20, sample_count: 5, average_return: "-0.0180", hit_rate: "0.2" },
  ],
  evidence: { sample_status: "segmented", minimum_closed_trades: 5, closed_trade_count: 7, source_bar_count: 400, lookahead_check: "passed", segment_status: "ready", parameter_policy: "frozen_before_validation", out_of_sample_tuning: "prohibited", parameter_snapshot_hash: "a".repeat(64), survivorship_bias_check: "unresolved", suspension_handling: "zero_volume_untradable", limit_handling: "opening_limit_untradable", cost_policy: "commission_slippage_stamp_duty" },
  request_snapshot: { strategy: "sma_cross", fast_window: 5, slow_window: 20, lookback_window: 20, exit_window: 10, volume_window: 20, volume_ratio: .8, stop_loss_percent: .06, take_profit_percent: .18, initial_cash: 100000, commission_rate: .0003, slippage_rate: .0005, stamp_duty_rate: .0005 },
  equity_curve: [], warnings: ["benchmark_not_available"],
};

describe("BacktestPanel", () => {
  it("rejects bond and known index codes", () => {
    const runBacktest = vi.fn(() => Promise.resolve(result));
    render(<BacktestPanel symbol="" runBacktest={runBacktest} />);
    const input = screen.getByRole("textbox", { name: "回测 A 股代码" });
    fireEvent.change(input, { target: { value: "113065" } });
    expect(screen.getByRole("button", { name: "运行回测" })).toBeDisabled();
    fireEvent.change(input, { target: { value: "000300" } });
    expect(screen.getByRole("button", { name: "运行回测" })).toBeDisabled();
  });

  it("isolates out-of-order results and clears prior output when the input changes", async () => {
    let resolveOld!: (value: typeof result) => void;
    const old = new Promise<typeof result>((resolve) => { resolveOld = resolve; });
    const newer = { ...result, symbol: "000001", total_return: "0.1000" };
    const runBacktest = vi.fn().mockReturnValueOnce(old).mockResolvedValueOnce(newer);
    render(<BacktestPanel symbol="600000" runBacktest={runBacktest} />);
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));
    fireEvent.change(screen.getByRole("textbox", { name: "回测 A 股代码" }), { target: { value: "000001" } });
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));
    expect(await screen.findByText("回测标的 000001")).toBeInTheDocument();
    resolveOld(result);
    await Promise.resolve();
    expect(screen.getByText("回测标的 000001")).toBeInTheDocument();
    expect(screen.queryByText("回测标的 600000")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "回测 A 股代码" }), { target: { value: "600519" } });
    expect(screen.queryByText("回测标的 000001")).not.toBeInTheDocument();
  });
  it("defaults to the selected symbol without overwriting an explicit edit", async () => {
    const runBacktest = vi.fn(() => Promise.resolve(result));
    const view = render(<BacktestPanel symbol="600000" runBacktest={runBacktest} />);
    const input = screen.getByRole("textbox", { name: "回测 A 股代码" });
    expect(input).toHaveValue("600000");
    fireEvent.change(input, { target: { value: "000001" } });
    view.rerender(<BacktestPanel symbol="600519" runBacktest={runBacktest} />);
    expect(input).toHaveValue("000001");
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));
    expect(runBacktest).toHaveBeenCalledWith("000001", expect.objectContaining({ strategy: "sma_cross" }), expect.any(AbortSignal));
  });

  it("runs a selected strategy with editable parameters", async () => {
    const runBacktest = vi.fn(() => Promise.resolve({ ...result, strategy: "momentum_breakout" }));
    render(<BacktestPanel symbol="600000" runBacktest={runBacktest} />);

    fireEvent.click(screen.getByRole("button", { name: /动量突破/ }));
    fireEvent.change(screen.getByLabelText("突破周期"), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));

    expect(runBacktest).toHaveBeenCalledWith("600000", expect.objectContaining({ strategy: "momentum_breakout", lookback_window: 30 }), expect.any(AbortSignal));
    expect(await screen.findByText(/回测标的 600000/)).toBeInTheDocument();
  });

  it("shows losses, drawdown and costs without positive framing", async () => {
    render(<BacktestPanel symbol="600000" runBacktest={() => Promise.resolve(result)} />);

    expect(screen.getByText(/100 万元固定测算基准 · 不连接账户/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));

    expect(await screen.findByText("-23.79%")).toBeInTheDocument();
    expect(screen.getByText("25.20%")).toBeInTheDocument();
    expect(screen.getByText("937.21")).toBeInTheDocument();
    expect(screen.getByText("14 笔")).toBeInTheDocument();
    expect(screen.getByText("18.25%")).toBeInTheDocument();
    expect(screen.getByText("42.86%")).toBeInTheDocument();
    expect(screen.getByText("1.24")).toBeInTheDocument();
    expect(screen.getByText("325.00%")).toBeInTheDocument();
    expect(screen.getByText("-15.40%")).toBeInTheDocument();
    expect(screen.getByText("-0.84")).toBeInTheDocument();
    expect(screen.getByText("-0.61")).toBeInTheDocument();
    expect(screen.getByText("-320.50")).toBeInTheDocument();
    expect(screen.getByText("3 笔")).toBeInTheDocument();
    expect(screen.getByText("参数已冻结")).toBeInTheDocument();
    expect(screen.getByText("样本外禁止调参")).toBeInTheDocument();
    expect(screen.getByText("幸存者偏差未消除")).toBeInTheDocument();
    expect(screen.getByText("未提供同期基准，暂不能判断超额收益")).toBeInTheDocument();
    expect(screen.getByText("样本外")).toBeInTheDocument();
    expect(screen.getByText("样本外验证已完成")).toBeInTheDocument();
    expect(screen.getByText("前视检查通过")).toBeInTheDocument();
    expect(screen.getByText("3.00%")).toBeInTheDocument();
    expect(screen.getByText("下行阶段")).toBeInTheDocument();
    expect(screen.getByText("-18.00%")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "滚动稳定性" })).toBeInTheDocument();
    expect(screen.getByText("近期窗口")).toBeInTheDocument();
    expect(screen.getByText("9.93%")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "信号衰减" })).toBeInTheDocument();
    expect(screen.getByText("20 日")).toBeInTheDocument();
    expect(screen.getByText("-1.80%")).toBeInTheDocument();
    expect(screen.getByText("下行阶段").closest("div")).toHaveTextContent("EV -910.00");
    expect(screen.getByText("下行阶段").closest("div")).toHaveTextContent("连续亏损 2");
  });

  it("gates rolling stability labels when closed trades are below policy", async () => {
    const gated = {
      ...result,
      rolling_windows: result.rolling_windows?.map((window) => ({ ...window, evaluation_status: "gated" as const })),
      evidence: { ...result.evidence!, sample_status: "insufficient" as const, closed_trade_count: 2 },
    };
    render(<BacktestPanel symbol="600000" runBacktest={() => Promise.resolve(gated)} />);

    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));

    expect(await screen.findAllByText("门槛未通过")).toHaveLength(3);
    expect(screen.getAllByText("闭合交易少于 5 笔")).toHaveLength(3);
    expect(screen.getByText(/胜率、Sharpe、Calmar、盈亏比和 EV 暂不形成结论/)).toBeInTheDocument();
    expect(screen.getAllByText("样本不足").length).toBeGreaterThanOrEqual(5);
  });

  it("asks for history sync when API returns a conflict", async () => {
    render(<BacktestPanel symbol="600000" runBacktest={() => Promise.reject(new Error("请先同步历史日线"))} />);
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("请先同步历史日线");
  });
});
