import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BacktestResult } from "../backtest/types";
import type { FirstLimitUpBoard, FirstLimitUpCandidate } from "../first-limit-up/types";
import type { KronosForecastResponse, QuantStrategyDashboard } from "./types";
import { QuantAnalysisDashboard } from "./QuantAnalysisDashboard";
import type { InstrumentSearchResponse } from "../stock-cockpit/types";
import type { StockTimelineResponse } from "../stock-timeline/types";

vi.mock("./QuantChart", () => ({
  QuantChart: ({ ariaLabel }: { ariaLabel: string }) => <div role="img" aria-label={ariaLabel} />,
}));

function candidate(symbol: string, name: string): FirstLimitUpCandidate {
  return {
    symbol, name, as_of: "2026-07-24", limit_up_date: "2026-07-24",
    limit_up_close: "11", current_close: "10", pe_ttm: "22", limit_rate: "0.1",
    weekly_distance_to_low: "0.1", monthly_distance_to_low: "0.12",
    weekly_bottom: true, monthly_bottom: true, pullback_pct: "0.09",
    consolidation_days: 6, selection_status: "qualified", stage: "pullback_window",
    action: "staged_entry_reference", score: "72.5", reasons: [], risk_flags: [],
    sources: ["本地日线"], entry_reference: {
      buy_steps_pct: ["-0.02"], sell_steps_pct: ["0.03"], note: "仅观察",
    },
  };
}

const board: FirstLimitUpBoard = {
  asset: "a_share", status: "ready", as_of: "2026-07-24",
  universe_count: 5980, history_eligible_count: 5980, scan_coverage_count: 5980, coverage_complete: true,
  rule_version: "first-limit-up-v1", scanned_count: 2, qualified_count: 2,
  pullback_window_count: 2, no_buy_count: 0, today: [],
  pool: [candidate("600001", "样本一"), candidate("000001", "样本二")],
  priority_symbol: "600001", missing_data: [], sources: ["本地日线"],
};

const emptyBoard: FirstLimitUpBoard = {
  asset: "a_share", status: "empty", as_of: "2026-07-24",
  universe_count: 5980, history_eligible_count: 0, scan_coverage_count: 0, coverage_complete: false,
  rule_version: "first-limit-up-v1", scanned_count: 0, qualified_count: 0,
  pullback_window_count: 0, no_buy_count: 0, today: [], pool: [],
  priority_symbol: null, missing_data: [], sources: ["本地日线"],
};

const strategyDashboard: QuantStrategyDashboard = {
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
    suitable_strategies: ["0轴低吸模型"], avoid_strategies: ["后排追涨"],
    reasons: ["情绪分达到阈值"], missing_factors: ["net_positive_ratio"],
    rule_matched: true, quality: "partial", formula_version: "a-share-short-regime-v2.0",
  },
  strategy_models: [],
  candidates: [],
  discipline: "只做真实触发确认。",
  missing_data: ["net_positive_ratio"],
  warnings: [],
  sources: ["tdx-local-realtime", "tdx-local-daily"],
};

function backtest(symbol: string, closedTradeCount = 12): BacktestResult {
  return {
    symbol, strategy: "sma_cross", initial_cash: "1000000", ending_equity: "1120000",
    total_return: "0.12", max_drawdown: "0.08", total_cost: "200",
    metrics: {
      annualized_return: "0.10", annualized_volatility: "0.22",
      sharpe_ratio: "0.45", calmar_ratio: "1.25",
      win_rate: "0.58", profit_loss_ratio: "1.6",
      turnover_rate: "0.4", closed_trade_count: closedTradeCount,
    },
    segments: [], market_regimes: [], trades: [], warnings: [],
    equity_curve: [
      { trade_date: "2026-07-23", equity: "1000000" },
      { trade_date: "2026-07-24", equity: "1120000" },
    ],
  };
}

function ticks(symbol: string) {
  return [{
    symbol, price: "10.80", change: "0.80", change_percent: "8.00", volume: "120000",
    source: "fixture", observed_at: "2026-07-24T14:55:00+08:00",
    fetched_at: "2026-07-24T14:55:01+08:00", quality: "ready" as const,
    source_snapshot_id: `tick-${symbol}`,
  }];
}

function timeline(symbol: string): StockTimelineResponse {
  return {
    symbol, as_of: "2026-07-24", cutoff: "2026-07-24T15:00:00+08:00", status: "ready",
    bars: [
      { symbol, trade_date: "2026-07-23", open: "9.8", high: "10.2", low: "9.6", close: "10", volume: 100, amount: "1000", source: "local-daily-bars" },
      { symbol, trade_date: "2026-07-24", open: "10", high: "11", low: "9.9", close: "10.8", volume: 160, amount: "1728", source: "local-daily-bars" },
    ],
    events: [], sources: ["local-daily-bars"], warnings: [],
  };
}

function unavailableForecast(symbol: string): KronosForecastResponse {
  return {
    status: "unavailable",
    symbol,
    as_of: "2026-07-24",
    observed_through: null,
    model: "Kronos-mini",
    frequency: "1d",
    lookback_bars: 250,
    horizon_bars: 20,
    sample_count: 0,
    summary: null,
    points: [],
    reasons: ["kronos_disabled"],
    sources: [],
    warnings: [],
  };
}

describe("QuantAnalysisDashboard", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("prefers the previously selected global stock over the first-limit-up priority", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="000001"
    />);

    expect(await screen.findByText("000001", { selector: ".quant-selected-symbol" })).toBeInTheDocument();
    expect(await screen.findByText("样本二", { selector: ".quant-selected-name" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "量化分析股票" })).toHaveValue("000001");
  });

  it("resolves the name of a restored stock outside the first-limit-up pool", async () => {
    const search = vi.fn(async (query: string): Promise<InstrumentSearchResponse> => ({
      query,
      items: [{
        symbol: "600519", name: "贵州茅台", exchange: "sh",
        observed_at: "2026-08-06T10:00:00+08:00", quote_quality: "ready",
      }],
      server_time: "2026-08-06T10:00:00+08:00",
      source_status: "ready",
    }));
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="600519"
      searchInstruments={search}
    />);

    await waitFor(() => expect(search).toHaveBeenCalledWith("600519"));
    expect(await screen.findByText("贵州茅台", { selector: ".quant-selected-name" })).toBeInTheDocument();
    expect(screen.getByText("自定义标的")).toBeInTheDocument();
  });

  it("searches by stock name and switches to any verified A-share", async () => {
    const search = vi.fn(async (query: string): Promise<InstrumentSearchResponse> => ({
      query,
      items: [{
        symbol: "600519", name: "贵州茅台", exchange: "sh",
        observed_at: "2026-08-06T10:00:00+08:00", quote_quality: "ready",
      }],
      server_time: "2026-08-06T10:00:00+08:00",
      source_status: "ready",
    }));
    const onSelectSymbol = vi.fn();
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      searchInstruments={search}
      onSelectSymbol={onSelectSymbol}
    />);

    fireEvent.change(screen.getByRole("searchbox", { name: "查询量化分析标的" }), {
      target: { value: "贵州茅台" },
    });
    await waitFor(() => expect(search).toHaveBeenCalledWith("贵州茅台"));
    fireEvent.click(await screen.findByRole("option", { name: /600519.*贵州茅台/ }));

    expect(onSelectSymbol).toHaveBeenCalledWith("600519");
    expect(await screen.findByText("600519", { selector: ".quant-selected-symbol" })).toBeInTheDocument();
    expect(screen.getByText("贵州茅台", { selector: ".quant-selected-name" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "量化因子雷达" }))
      .toHaveTextContent("未进入首次涨停候选池");
  });

  it("refuses backtest and Kronos evidence returned for another stock", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async () => ({ ...backtest("000001"), total_return: "9.99" })}
      loadKronosForecast={async () => unavailableForecast("000001")}
      selectedSymbol="600001"
    />);

    const backtestPanel = await screen.findByRole("region", { name: "回测风险收益" });
    await waitFor(() => expect(backtestPanel).toHaveTextContent("等待历史回测"));
    expect(backtestPanel).not.toHaveTextContent("999.0%");
    const kronosPanel = screen.getByRole("region", { name: "Kronos 价格路径预测" });
    await waitFor(() => expect(kronosPanel).toHaveTextContent("等待预测状态"), { timeout: 2_000 });
    expect(kronosPanel).not.toHaveTextContent("Kronos 模型未启用");
  });

  it("uses the shared terminal page shell", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
    />);

    expect(screen.getByRole("main", { name: "首次涨停量化分析" }))
      .toHaveClass("terminal-page", "quant-analysis-page");
    expect(await screen.findByRole("heading", { name: "量化分析仪表盘" })).toBeInTheDocument();
  });

  it("keeps the custom target search beside the selected target details", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="002008"
    />);

    const control = await screen.findByRole("region", { name: "当前量化分析标的" });
    const layout = control.querySelector(".quant-instrument-layout");
    expect(layout).toHaveClass("split");
    expect(layout?.children).toHaveLength(2);
    expect(layout?.children[0]).toHaveTextContent("自定义标的");
    expect(layout?.children[1]).toHaveTextContent("首次涨停候选快速切换");
  });

  it("keeps instrument identity, search, and candidate switch in independent rows", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="603228"
    />);

    const control = await screen.findByRole("region", { name: "当前量化分析标的" });
    expect(control.querySelector(".quant-instrument-heading")).toHaveTextContent("分析标的");
    expect(control.querySelector(".quant-selected-row")).toHaveTextContent("603228");
    expect(control.querySelector(".quant-search-row input")).toBeInTheDocument();
    expect(control.querySelector(".quant-candidate-row select")).toBeInTheDocument();
    expect(control.querySelectorAll(".quant-instrument-layout > *")).toHaveLength(2);
  });

  it("makes the selected target state and candidate switch context explicit", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="002008"
    />);

    const control = await screen.findByRole("region", { name: "当前量化分析标的" });
    expect(control.querySelector(".quant-instrument-state")).toHaveTextContent("标的已锁定");
    expect(control.querySelector(".quant-candidate-context")).toHaveTextContent("首次涨停候选");
    expect(control.querySelector(".quant-rule-snapshot")).toHaveTextContent("规则快照");
  });

  it("keeps compact target labels in stacked rows at narrow widths", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      selectedSymbol="600419"
    />);

    const control = await screen.findByRole("region", { name: "当前量化分析标的" });
    expect(control.querySelector(".quant-instrument-heading")).toHaveClass("stacked");
    expect(control.querySelector(".quant-candidate-context")).toHaveClass("stacked");
  });

  it("adds a detailed TDX-style event K-line workspace when the local timeline is available", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      loadTimeline={async (symbol) => timeline(symbol)}
    />);

    expect(await screen.findByRole("region", { name: "通达信式研究总览" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "个股新闻与热点事件 K 线" })).toHaveTextContent("事件 K 线");
    expect(screen.getByRole("region", { name: "通达信式研究总览" })).toHaveTextContent("PE(TTM)");
  });

  it("loads the short-term strategy workbench independently below the Kronos forecast", async () => {
    const loadQuantStrategy = vi.fn(async () => strategyDashboard);
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      loadKronosForecast={async (symbol) => unavailableForecast(symbol)}
      loadQuantStrategy={loadQuantStrategy}
    />);

    await waitFor(() => expect(loadQuantStrategy).toHaveBeenCalledWith(12));
    expect(await screen.findByText(/候选扫描：刚刚采集/)).toBeInTheDocument();
    expect(await screen.findByText(/触发证据：刚刚采集/)).toBeInTheDocument();
    const strategyHeading = await screen.findByRole("heading", { name: "短线风格与策略" });
    const kronosPanel = screen.getByRole("region", { name: "Kronos 价格路径预测" });
    expect(kronosPanel.compareDocumentPosition(strategyHeading))
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(screen.getByRole("region", { name: "高频 TICK 分时" })).toBeInTheDocument();
  });

  it("keeps the last ready strategy snapshot without restarting candidate scans on a timer", async () => {
    vi.useFakeTimers();
    try {
      const pendingDashboard: QuantStrategyDashboard = {
        ...strategyDashboard,
        status: "unavailable",
        generated_at: "2026-07-31T14:00:05+08:00",
        candidate_scan_at: null,
        candidate_scan_age_seconds: null,
        candidate_scan_state: "pending",
        candidate_scan_phase: "computing_factors",
        candidate_scan_processed: 1200,
        candidate_scan_total: 5980,
        trigger_evidence_at: null,
        trigger_evidence_age_seconds: null,
        metrics: {
          ...strategyDashboard.metrics,
          up_ratio: null,
          strong_close_ratio: null,
          factor_coverage_percent: "0",
        },
        regime: {
          ...strategyDashboard.regime,
          regime: null,
          emotion_score: null,
          coverage_percent: "0",
          suitable_strategies: [],
          avoid_strategies: [],
          quality: "unavailable",
        },
        strategy_models: [],
        candidates: [],
        missing_data: ["candidate_scan_pending"],
        sources: [],
      };
      const loadQuantStrategy = vi.fn()
        .mockResolvedValueOnce(strategyDashboard)
        .mockResolvedValueOnce(pendingDashboard);

      render(<QuantAnalysisDashboard
        loadBoard={async () => board}
        loadTicks={async (symbol) => ticks(symbol)}
        runBacktest={async (symbol) => backtest(symbol)}
        loadQuantStrategy={loadQuantStrategy}
      />);

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      await act(async () => { await vi.advanceTimersByTimeAsync(250); });
      expect(screen.getByRole("region", { name: "市场风格评分" })).toHaveTextContent("76.0");

      await act(async () => { await vi.advanceTimersByTimeAsync(5_000); });

      expect(loadQuantStrategy).toHaveBeenCalledTimes(1);

      await act(async () => { await vi.advanceTimersByTimeAsync(25_000); });

      expect(loadQuantStrategy).toHaveBeenCalledTimes(1);
      expect(screen.getByRole("region", { name: "市场风格评分" })).toHaveTextContent("76.0");
      expect(screen.queryByRole("progressbar", { name: "候选扫描后台预热" })).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the four quadrants available when strategy loading fails", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      loadQuantStrategy={async () => { throw new Error("strategy down"); }}
    />);

    expect(await screen.findByText("短线策略数据暂不可用")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "回测风险收益" })).toBeInTheDocument();
  });

  it("refreshes an empty first-limit-up cache before showing the dashboard", async () => {
    const refreshBoard = vi.fn(async () => board);
    render(<QuantAnalysisDashboard
      loadBoard={async () => emptyBoard}
      refreshBoard={refreshBoard}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
    />);

    await waitFor(() => expect(refreshBoard).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("combobox", { name: "量化分析股票" })).toHaveValue("600001");
  });

  it("reloads archived ticks and backtest evidence when the candidate changes", async () => {
    const loadTicks = vi.fn(async (symbol: string) => ticks(symbol));
    const runBacktest = vi.fn(async (symbol: string, _signal?: AbortSignal) => backtest(symbol));
    render(<QuantAnalysisDashboard loadBoard={async () => board} loadTicks={loadTicks} runBacktest={runBacktest} />);

    await waitFor(() => expect(loadTicks).toHaveBeenCalledWith("600001"));
    await waitFor(() => expect(runBacktest).toHaveBeenCalledWith("600001", expect.any(AbortSignal)));

    fireEvent.change(screen.getByRole("combobox", { name: "量化分析股票" }), { target: { value: "000001" } });

    await waitFor(() => expect(loadTicks).toHaveBeenCalledWith("000001"));
    await waitFor(() => expect(runBacktest).toHaveBeenCalledWith("000001", expect.any(AbortSignal)));
    expect(await screen.findByRole("img", { name: "样本二盘中价格和成交量" })).toBeInTheDocument();
  });

  it("keeps missing tick evidence honest and never renders synthetic numeric output", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async () => []}
      runBacktest={async (symbol) => backtest(symbol, 0)}
    />);

    expect(await screen.findByText("暂无已归档盘中 TICK")).toBeInTheDocument();
    const signalEngine = screen.getByRole("region", { name: "信号引擎" });
    expect(within(signalEngine).getByText("胜率").closest(".quant-signal-row")).toHaveTextContent("--");
    expect(within(signalEngine).getByText("赔率").closest(".quant-signal-row")).toHaveTextContent("--");
    expect(within(signalEngine).getByText("EV").closest(".quant-signal-row")).toHaveTextContent("--");
    expect(document.body).not.toHaveTextContent(/NaN|Infinity/);
  });

  it("renders unavailable values instead of NaN when a live quote is malformed", async () => {
    const malformedBoard = {
      ...board,
      pool: [{ ...candidate("600001", "样本一"), pullback_pct: "not-a-number" }],
    } as FirstLimitUpBoard;
    render(<QuantAnalysisDashboard
      loadBoard={async () => malformedBoard}
      loadTicks={async (symbol) => [{ ...ticks(symbol)[0], price: "bad", change_percent: "bad" }]}
      runBacktest={async (symbol) => backtest(symbol, 0)}
    />);

    expect(await screen.findByText("数据不可用", { selector: ".quant-price-overlay span" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "信号引擎" })).toHaveTextContent("72.5");
    expect(document.body).not.toHaveTextContent(/NaN|Infinity/);
  });

  it("isolates tick and backtest failures so rule evidence remains available", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async () => { throw new Error("tick down"); }}
      runBacktest={async () => { throw new Error("backtest down"); }}
    />);

    expect(await screen.findByText("盘中 TICK 归档暂不可用")).toBeInTheDocument();
    expect(await screen.findByText("历史回测暂不可用")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "量化因子雷达" })).toHaveTextContent("证据覆盖");
    expect(screen.getByRole("region", { name: "信号引擎" })).toHaveTextContent("72.5");
  });

  it("does not render invalid backtest totals as zero percentages", async () => {
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async () => ({ ...backtest("600001"), total_return: null, max_drawdown: "not-a-number" } as unknown as BacktestResult)}
    />);
    const panel = await screen.findByRole("region", { name: "回测风险收益" });
    await waitFor(() => expect(panel).toHaveTextContent("总收益"));
    expect(panel).toHaveTextContent("--");
    expect(panel).not.toHaveTextContent("0.0%");
  });

  it("loads the Kronos evidence panel independently for the selected candidate", async () => {
    const loadKronosForecast = vi.fn(async (symbol: string) => unavailableForecast(symbol));
    render(<QuantAnalysisDashboard
      loadBoard={async () => board}
      loadTicks={async (symbol) => ticks(symbol)}
      runBacktest={async (symbol) => backtest(symbol)}
      loadKronosForecast={loadKronosForecast}
    />);

    await waitFor(() => expect(loadKronosForecast).toHaveBeenCalledWith("600001", "2026-07-24", 20), { timeout: 2_000 });
    expect(screen.getByRole("region", { name: "Kronos 价格路径预测" })).toHaveTextContent("模型未启用");

    fireEvent.change(screen.getByRole("combobox", { name: "量化分析股票" }), { target: { value: "000001" } });
    await waitFor(() => expect(loadKronosForecast).toHaveBeenCalledWith("000001", "2026-07-24", 20), { timeout: 2_000 });
  });

  it("loads each data layer once and avoids duplicate timer-driven requests", async () => {
    vi.useFakeTimers();
    const loadBoard = vi.fn(async () => board);
    const loadTicks = vi.fn(async (symbol: string) => ticks(symbol));
    const loadQuantStrategy = vi.fn(async () => strategyDashboard);
    const runBacktest = vi.fn(async (symbol: string, _signal?: AbortSignal) => backtest(symbol));
    const view = render(<QuantAnalysisDashboard
      loadBoard={loadBoard}
      loadTicks={loadTicks}
      runBacktest={runBacktest}
      loadQuantStrategy={loadQuantStrategy}
    />);
    try {
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(loadBoard).toHaveBeenCalledTimes(1);
      expect(loadQuantStrategy).not.toHaveBeenCalled();
      expect(runBacktest).not.toHaveBeenCalled();
      expect(loadTicks).toHaveBeenCalledWith("600001");
      expect(screen.getByRole("region", { name: "量化实时数据状态" }))
        .toHaveTextContent("TICK 实时总线");

      await act(async () => { await vi.advanceTimersByTimeAsync(250); });
      expect(loadQuantStrategy).toHaveBeenCalledTimes(1);
      expect(runBacktest).not.toHaveBeenCalled();

      await act(async () => { await vi.advanceTimersByTimeAsync(350); });
      expect(runBacktest).toHaveBeenCalledWith("600001", expect.any(AbortSignal));

      await act(async () => { await vi.advanceTimersByTimeAsync(400); });
      expect(loadTicks).toHaveBeenCalledTimes(1);

      await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
      expect(loadQuantStrategy).toHaveBeenCalledTimes(1);
      expect(loadTicks).toHaveBeenCalledTimes(1);

      await act(async () => { await vi.advanceTimersByTimeAsync(26000); });
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(loadQuantStrategy).toHaveBeenCalledTimes(1);
      expect(loadBoard).toHaveBeenCalledTimes(1);
    } finally {
      view.unmount();
      vi.useRealTimers();
    }
  });
});
