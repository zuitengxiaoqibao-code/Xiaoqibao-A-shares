import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SelectedInstrumentProvider } from "../instrument-selection/SelectedInstrumentProvider";
import { candidateSentimentForSymbol, Dashboard, preparationForSymbol, RouteLoadingFallback } from "./Dashboard";
import type { CandidateSentimentBatch } from "../candidate-sentiment/types";
import type { FirstLimitUpBoard } from "../first-limit-up/types";
import type { MarketOverviewResponse } from "../market-overview/types";
import type { StockCockpitSnapshot } from "../stock-cockpit/types";
import type { QuantStrategyDashboard } from "../quant-analysis/types";

const card = {
  asset: "a_share" as const, symbol: "600000", action: "observe" as const, quality: "fresh" as const,
  change_percent: "1.2", invalid_reasons: [], evidence: [],
};
const emptyPhase = { phase_status: "empty" as const, quality: "empty" as const, aggregate_version: null, ai_status: "not_requested" as const, advice: [], evidence: [] };
const emptyDecision = {
  server_time: "2026-07-15T10:00:00+08:00", trading_date: "2026-07-15",
  current_phase: "premarket" as const, market_session: "open" as const,
  phases: { premarket: emptyPhase, intraday: emptyPhase, postclose: emptyPhase },
  polling: { focus_interval_seconds: 60, universe_interval_seconds: 240, stale_after_seconds: 180, next_check_seconds: 60 },
};
const marketSentiment = {
  trading_date: "2026-07-15", phase: "intraday" as const, display_mode: "current" as const,
  current: {
    snapshot_id: "sentiment-dashboard", previous_snapshot_id: null, trading_date: "2026-07-15",
    phase: "intraday" as const, quality: "partial" as const, freshness: "current" as const,
    score: "64", band: "active" as const, coverage_percent: "80", components: [],
    drivers: ["上涨股票覆盖扩大"], risks: ["部分组件数据不可用"], beginner_guidance: "等待确认。",
    observed_at: "2026-07-15T10:30:00+08:00", generated_at: "2026-07-15T10:30:05+08:00",
    source_snapshot_ids: ["source-1"], formula_version: "a-share-sentiment-v1",
  },
  previous_close: null, trajectory: [],
};
const firstLimitUpBoard: FirstLimitUpBoard = {
  asset: "a_share", status: "ready", as_of: "2026-07-24", rule_version: "first-limit-up-v1",
  universe_count: 5980, history_eligible_count: 5980, scan_coverage_count: 5980, coverage_complete: true,
  scanned_count: 1, qualified_count: 1, pullback_window_count: 0, no_buy_count: 1,
  priority_symbol: "600001", missing_data: [], sources: ["本地日线"],
  today: [{
    symbol: "600001", name: "首板样本", as_of: "2026-07-24", limit_up_date: "2026-07-24",
    limit_up_close: "11", current_close: "11", pe_ttm: "22", limit_rate: "0.1",
    weekly_distance_to_low: "0.1", monthly_distance_to_low: "0.1", weekly_bottom: true,
    monthly_bottom: true, pullback_pct: "0", consolidation_days: 0,
    selection_status: "qualified", stage: "limit_up_day", action: "no_buy", score: "68.4",
    reasons: [], risk_flags: ["limit_up_day_no_buy"], sources: ["本地日线"],
    entry_reference: { buy_steps_pct: ["-0.02"], sell_steps_pct: ["0.03"], note: "仅观察" },
  }],
  pool: [],
};
const quantBacktest = {
  symbol: "600001", strategy: "sma_cross", initial_cash: "1000000",
  ending_equity: "1120000", total_return: "0.12", max_drawdown: "0.08", total_cost: "200",
  metrics: { annualized_return: "0.10", annualized_volatility: "0.22", sharpe_ratio: "0.45", calmar_ratio: "1.25", win_rate: "0.58", profit_loss_ratio: "1.6", turnover_rate: "0.4", closed_trade_count: 12 },
  segments: [], market_regimes: [], trades: [],
  equity_curve: [
    { trade_date: "2026-07-23", equity: "1000000", cash: "1000000", shares: 0, market_value: "0" },
    { trade_date: "2026-07-24", equity: "1120000", cash: "1120000", shares: 0, market_value: "0" },
  ],
  warnings: [],
};

describe("route loading", () => {
  it("uses a quiet busy state without the blocking workbench message", () => {
    render(<RouteLoadingFallback />);

    const status = screen.getByRole("status", { name: "页面准备状态" });
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).not.toHaveTextContent("加载工作台");
  });
});

const quantStrategy: QuantStrategyDashboard = {
  status: "partial", as_of: "2026-07-31", observed_at: "2026-07-31T14:00:00+08:00",
  generated_at: "2026-07-31T14:00:00+08:00", market_observed_at: "2026-07-31T14:00:00+08:00",
  data_age_seconds: 0, refresh_mode: "live", next_refresh_at: "2026-07-31T14:00:05+08:00",
  candidate_scan_at: "2026-07-31T14:00:00+08:00", candidate_scan_age_seconds: 0, candidate_scan_cached: false,
  candidate_scan_state: "ready", candidate_scan_started_at: "2026-07-31T14:00:00+08:00", candidate_scan_error: null,
  candidate_scan_phase: "ready", candidate_scan_processed: null, candidate_scan_total: null,
  trigger_evidence_at: "2026-07-31T14:00:00+08:00", trigger_evidence_age_seconds: 0, trigger_evidence_cached: false,
  formula_version: "a-share-short-strategy-v2.0",
  metrics: {
    up_ratio: "66", zt_ratio: "1.4", dt_ratio: "0.1", median_ret: "1.2",
    amt_heat: "1.15", strong_close_ratio: "72", weak_close_ratio: "12",
    limit_fail_ratio: "18", panic_ratio: "2", amp_ratio: "18",
    net_positive_ratio: null, large_amount_strong_close_ratio: "70", factor_coverage_percent: "90.91",
  },
  regime: {
    regime: "情绪主升", emotion_score: "76", risk_score: "22", heat_score: "68",
    rotation_score: "35", coverage_percent: "85", market_coef: "1",
    suitable_strategies: ["0轴低吸模型"], avoid_strategies: ["后排追涨"], reasons: [],
    missing_factors: ["net_positive_ratio"], rule_matched: true, quality: "partial",
    formula_version: "a-share-short-regime-v2.0",
  },
  strategy_models: [],
  candidates: [], discipline: "只做真实触发确认。", missing_data: [], warnings: [], sources: ["fixture"],
};

const marketOverview: MarketOverviewResponse = {
  status: "partial", as_of: "2026-07-29", observed_at: "2026-07-29T10:30:00+08:00",
  sentiment: { score: "76", band: "活跃", coverage_percent: "88", quality: "partial", observed_at: "2026-07-29T10:30:00+08:00" },
  breadth: { rising_count: 4439, falling_count: 699, flat_count: 10, valid_count: 5148 },
  limit_ecology: { limit_up_count: 78, limit_down_count: 6, broken_limit_up_count: 40, seal_rate_percent: "66.1" },
  liquidity: { total_amount_yi: "15862.96", baseline_amount_yi: "19444.39", relative_amount: "0.82" },
  market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-07-29T10:30:00+08:00", quote_count: 5191, universe_count: 5207 },
  indices: [], minute_series: [], anomalies: [], live_feed: [], sectors: [], sector_stocks: {}, market_stocks: [],
  warnings: ["指数分钟线暂不可用"], sources: ["本地情绪库"],
};

const dashboardCockpit: StockCockpitSnapshot = {
  symbol: "600000", as_of: "2026-08-03", cutoff: "2026-08-03T10:30:00+08:00",
  overall_quality: "ready" as const,
  instrument: { symbol: "600000", name: "浦发银行", exchange: "sh", observed_at: "2026-08-03T10:30:00+08:00", quote_quality: "ready" as const },
  preparation: undefined, candidate_membership: [],
  assessment: { assessment_id: "dashboard-assessment", symbol: "600000", action: "wait" as const, conclusion: "等待更多证据。", confidence: "0.5", supporting_evidence: [], contrary_evidence: [], risks: [], invalidation_conditions: [], generated_at: "2026-08-03T10:30:00+08:00" },
  ai_status: "unconfigured" as const, ai_explanation: null, current_advice: [],
  sections: { market: { status: "ready" as const, source: "fixture", observed_at: "2026-08-03T10:30:00+08:00", snapshot_id: "market-600000", reason: null, payload: { metrics: { latest_price: "10.25", change_percent: "1.2" } } } },
  phases: { premarket: { advice: [], change_stream: [] }, intraday: { advice: [], change_stream: [] }, postclose: { advice: [], change_stream: [] } },
};

function decisionAdvice(symbol: string, conclusion: string) {
  return {
    advice_id: `advice-${symbol}`, snapshot_id: "snapshot-intraday", asset: "a_share" as const,
    symbol, horizon: "intraday" as const, observation_state: "watching", action: "observe" as const,
    conclusion, confidence: "0.72",
    supporting_evidence: [{
      evidence_id: `evidence-${symbol}`, source: "tencent", snapshot_id: `quote-${symbol}`,
      summary: `${symbol} 行情已验证`, observed_at: "2026-07-15T10:29:00+08:00",
    }],
    contrary_evidence: [], risks: ["短线波动可能放大"], invalidation_conditions: ["量价条件失效"],
    plain_language_explanation: "先观察确认，不追涨。", quantitative_result: {}, ai_interpretation_id: null,
    risk_decision_id: null, previous_advice_id: null, changed_fields: [], strategy_version: "decision-v1",
    created_at: "2026-07-15T10:30:00+08:00",
  };
}

function marketDecision() {
  const advice = [decisionAdvice("600000", "等待放量确认"), decisionAdvice("000001", "趋势仍需观察")];
  return {
    ...emptyDecision,
    current_phase: "intraday" as const,
    phases: {
      ...emptyDecision.phases,
      intraday: {
        ...emptyPhase, phase_status: "ready" as const, quality: "ready" as const,
        aggregate_version: "snapshot-intraday", advice,
        evidence: advice.flatMap((item) => item.supporting_evidence),
      },
    },
  };
}

describe("Dashboard beginner shell", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    window.localStorage.clear();
  });

  it("opens the A-share information overview as the default homepage", async () => {
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadMarketOverview={() => Promise.resolve(marketOverview)}
    />);

    expect(window.location.pathname).toBe("/");
    expect(await screen.findByRole("heading", { name: "信息总览" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "信息总览" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps today decision available on its own stable route", async () => {
    render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadMarketOverview={() => Promise.resolve(marketOverview)}
      loadDecisionCurrent={() => Promise.resolve(emptyDecision)}
      loadMarketSentiment={() => Promise.resolve(marketSentiment)}
    /></SelectedInstrumentProvider>);

    fireEvent.click(screen.getByRole("button", { name: "今日研判" }));

    expect(window.location.pathname).toBe("/today-decision");
    expect(await screen.findByRole("region", { name: "A 股监控首页" })).toBeInTheDocument();
  });

  it("shows one complete menu without navigation modes", () => {
    render(<Dashboard loadSnapshot={() => Promise.resolve(card)} />);
    const navigation = screen.getByRole("navigation", { name: "主要功能" });
    expect(navigation.querySelectorAll("button")).toHaveLength(11);
    expect(screen.queryByRole("button", { name: "新手模式" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "专家模式" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "信息总览" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "今日研判" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "首次涨停" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "公司研究" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "量化分析" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "数据设置" })).toBeInTheDocument();
    expect(screen.queryByText(/中书省|吏部|户部|东厂|礼部|兵部|尚书省|刑部|工部/)).not.toBeInTheDocument();
    expect(screen.queryByText(/模拟账户|模拟委托|模拟操作计划|API 密钥/)).not.toBeInTheDocument();
  });

  it("opens information overview on its stable route", async () => {
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadMarketOverview={() => Promise.resolve(marketOverview)}
    />);

    fireEvent.click(screen.getByRole("button", { name: "信息总览" }));

    expect(window.location.pathname).toBe("/market-overview");
    expect(await screen.findByRole("heading", { name: "信息总览" })).toBeInTheDocument();
  });

  it("opens first limit-up on its stable route", async () => {
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadFirstLimitUp={() => Promise.resolve(firstLimitUpBoard)}
      refreshFirstLimitUp={() => Promise.resolve(firstLimitUpBoard)}
    />);

    fireEvent.click(screen.getByRole("button", { name: "首次涨停" }));
    expect(window.location.pathname).toBe("/first-limit-up");
    expect(await screen.findByRole("heading", { name: "首次涨停" })).toBeInTheDocument();
  });

  it("opens the quant-analysis child page on its stable route", async () => {
    render(<Dashboard loadSnapshot={() => Promise.resolve(card)} />);

    fireEvent.click(screen.getByRole("button", { name: "量化分析" }));

    expect(window.location.pathname).toBe("/first-limit-up/quant-analysis");
    expect(await screen.findByRole("heading", { name: "量化分析仪表盘" })).toBeInTheDocument();
  });

  it("renders the four quant-analysis quadrants from archived ticks and backtest evidence", async () => {
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadFirstLimitUp={() => Promise.resolve(firstLimitUpBoard)}
      loadQuantTicks={() => Promise.resolve([{
        symbol: "600001", price: "11.00", change: "1.00", change_percent: "10.00",
        volume: "120000", source: "fixture", observed_at: "2026-07-24T14:55:00+08:00",
        fetched_at: "2026-07-24T14:55:01+08:00", quality: "ready", source_snapshot_id: "tick-1",
      }])}
      runBacktest={() => Promise.resolve(quantBacktest)}
    />);

    fireEvent.click(screen.getByRole("button", { name: "量化分析" }));

    expect(await screen.findByRole("region", { name: "高频 TICK 分时" })).toBeInTheDocument();
    const signalEngine = screen.getByRole("region", { name: "信号引擎" });
    for (const label of ["VOL", "SCORE", "胜率", "赔率", "风险", "仓位", "EV"]) {
      expect(signalEngine).toHaveTextContent(label);
    }
    await waitFor(() => expect(signalEngine).toHaveTextContent("58.0%"));
    expect(screen.getByRole("region", { name: "量化因子雷达" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "回测风险收益" })).toBeInTheDocument();
  });

  it("keeps the selected stock and wires stock-name search into quant analysis", async () => {
    window.history.replaceState({}, "", "/a-shares?symbol=000001");
    const searchAShareInstruments = vi.fn(async (query: string) => ({
      query,
      items: [{
        symbol: "600519", name: "贵州茅台", exchange: "sh" as const,
        observed_at: "2026-08-06T10:00:00+08:00", quote_quality: "ready" as const,
      }],
      server_time: "2026-08-06T10:00:00+08:00",
      source_status: "ready" as const,
    }));
    render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadFirstLimitUp={() => Promise.resolve(firstLimitUpBoard)}
      loadQuantTicks={() => Promise.resolve([])}
      runBacktest={(symbol) => Promise.resolve({ ...quantBacktest, symbol })}
      searchAShareInstruments={searchAShareInstruments}
    /></SelectedInstrumentProvider>);

    fireEvent.click(screen.getByRole("button", { name: "量化分析" }));

    expect(await screen.findByText("000001", { selector: ".quant-selected-symbol" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "查询量化分析标的" }), {
      target: { value: "贵州茅台" },
    });
    await waitFor(() => expect(searchAShareInstruments).toHaveBeenCalledWith("贵州茅台"));
    await screen.findByRole("option", { name: /600519.*贵州茅台/ });
    fireEvent.click(screen.getByRole("option", { name: /600519.*贵州茅台/ }));

    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600519");
  });

  it("wires the short-term strategy loader through the quant-analysis route", async () => {
    const loadQuantStrategy = vi.fn(async () => quantStrategy);
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadFirstLimitUp={() => Promise.resolve(firstLimitUpBoard)}
      loadQuantTicks={() => Promise.resolve([])}
      runBacktest={() => Promise.resolve(quantBacktest)}
      loadQuantStrategy={loadQuantStrategy}
    />);

    fireEvent.click(screen.getByRole("button", { name: "量化分析" }));

    await waitFor(() => expect(loadQuantStrategy).toHaveBeenCalledWith(12));
    expect(await screen.findByRole("heading", { name: "短线风格与策略" })).toBeInTheDocument();
  });

  it("opens beginner risk and settings pages with stable routes", async () => {
    render(<Dashboard loadSnapshot={() => Promise.resolve(card)} loadRisk={() => Promise.resolve({ rule_version: "v1", limits: {} })} />);
    fireEvent.click(screen.getByRole("button", { name: "风险提醒" }));
    expect(await screen.findByRole("heading", { name: "当前风险状态" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/risk");
    fireEvent.click(screen.getByRole("button", { name: "数据设置" }));
    expect(screen.getByRole("heading", { name: "数据源与 AI" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/settings");
  });

  it("keeps AI secrets and removed paper products out of every reachable beginner route", async () => {
    const transportSecret = "transport-only-secret-9347";
    const loadAISettings = vi.fn(async () => ({
      configured: true, base_url: "https://api.example/v1", model: "local-model",
      api_key_hint: "****9347",
    }));
    const saveAISettings = vi.fn(async (payload: { base_url: string; model: string; api_key: string }) => {
      expect(payload.api_key).toBe(transportSecret);
      return { configured: true, base_url: payload.base_url, model: payload.model, api_key_hint: "****9347" };
    });
    const { container } = render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadRisk={() => Promise.resolve({ rule_version: "v1", limits: {} })}
      loadAShareCandidates={() => Promise.resolve({ asset: "a_share", snapshot_id: null, input_snapshot_hash: null, universe_status: "empty", as_of: "2026-07-15", factor_version: "v1", short_term: [], swing: [], exclusions: [] })}
      searchAShareInstruments={() => Promise.resolve({ query: "", items: [], server_time: "2026-07-15T09:30:00+08:00", source_status: "ready" })}
      loadNewsIntelligence={() => Promise.resolve({ events: [], interpretations: [], corrections: [], briefings: [], quality: { article_count: 0, cluster_count: 0, event_count: 0, interpretation_count: 0, correction_count: 0, citation_coverage: "1", duplicate_rate: "0", invalid_json_rate: "0", provider_error_rate: "0", human_correction_rate: "0" } })}
      syncNews={() => Promise.resolve({ fetched: 0 })} createNewsCorrection={() => Promise.resolve()}
      loadDecisionCurrent={() => Promise.resolve(emptyDecision)}
      loadAISettings={loadAISettings}
      saveAISettings={saveAISettings}
      deleteAISettings={async () => ({ configured: false, base_url: null, model: null, api_key_hint: null })}
    /></SelectedInstrumentProvider>);

    for (const name of ["今日研判", "个股观察", "首次涨停", "量化分析", "新闻热点", "风险提醒", "历史复盘", "数据设置"]) {
      fireEvent.click(screen.getByRole("button", { name }));
      if (name === "数据设置") await waitFor(() => expect(loadAISettings).toHaveBeenCalled());
      expect(container.innerHTML).not.toMatch(/模拟账户|模拟委托|模拟操作计划|纸面账户|纸面订单/);
    }

    expect(screen.getByText(/密钥已保存/)).toHaveTextContent("****9347");
    const keyInput = screen.getByLabelText("API 密钥") as HTMLInputElement;
    fireEvent.change(keyInput, { target: { value: transportSecret } });
    fireEvent.click(screen.getByRole("button", { name: "保存 AI 配置" }));
    await waitFor(() => expect(saveAISettings).toHaveBeenCalledTimes(1));
    expect(keyInput.value).toBe("");
    expect(keyInput.getAttribute("value") ?? "").toBe("");
    expect(container.innerHTML).not.toContain(transportSecret);
    for (const input of container.querySelectorAll("input")) {
      expect(input.value).not.toContain(transportSecret);
      for (const attribute of input.getAttributeNames()) {
        expect(input.getAttribute(attribute) ?? "").not.toContain(transportSecret);
      }
    }
  });

  it("opens A-share observation without legacy research internals", async () => {
    render(<SelectedInstrumentProvider><Dashboard loadSnapshot={() => Promise.resolve(card)}
      loadAShareCandidates={() => Promise.resolve({ asset: "a_share", snapshot_id: null, input_snapshot_hash: null, universe_status: "empty", as_of: "2026-07-15", factor_version: "secret-factor", short_term: [], swing: [], exclusions: [] })}
      searchAShareInstruments={() => Promise.resolve({ query: "", items: [], server_time: "2026-07-15T09:30:00+08:00", source_status: "ready" })} /></SelectedInstrumentProvider>);
    fireEvent.click(screen.getByRole("button", { name: "个股观察" }));
    expect(await screen.findByRole("heading", { name: "选择观察股票" })).toBeInTheDocument();
    expect(screen.queryByText(/secret-factor|snapshot|中书省|工部|候选生成|诊断/)).not.toBeInTheDocument();
  });

  it("switches from the observed stock to company research with the same symbol", async () => {
    window.history.replaceState({}, "", "/a-shares?symbol=600000");
    render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadStockCockpit={() => Promise.resolve(dashboardCockpit)}
      loadCompanyResearch={() => new Promise(() => undefined)}
      searchAShareInstruments={() => Promise.resolve({ query: "", items: [], server_time: "2026-08-03T10:30:00+08:00", source_status: "ready" })}
    /></SelectedInstrumentProvider>);

    fireEvent.click(await screen.findByRole("button", { name: "进入公司研究" }));

    expect(window.location.pathname).toBe("/company-research");
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600000");
    expect(await screen.findByRole("heading", { name: "公司研究" })).toBeInTheDocument();
  });

  it("keeps market sentiment out of the A-share selector", async () => {
    const loadMarketSentiment = vi.fn(() => Promise.resolve(marketSentiment));
    render(<SelectedInstrumentProvider><Dashboard loadSnapshot={() => Promise.resolve(card)}
      loadAShareCandidates={() => Promise.resolve({ asset: "a_share", snapshot_id: null, input_snapshot_hash: null, universe_status: "empty", as_of: "2026-07-15", factor_version: "v1", short_term: [], swing: [], exclusions: [] })}
      searchAShareInstruments={() => Promise.resolve({ query: "", items: [], server_time: "2026-07-15T09:30:00+08:00", source_status: "ready" })}
      loadMarketSentiment={loadMarketSentiment} /></SelectedInstrumentProvider>);

    fireEvent.click(screen.getByRole("button", { name: "个股观察" }));
    expect(await screen.findByRole("heading", { name: "选择观察股票" })).toBeInTheDocument();
    expect(loadMarketSentiment).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    expect(screen.queryByRole("region", { name: "自选股市场环境" })).not.toBeInTheDocument();
    expect(loadMarketSentiment).not.toHaveBeenCalled();
  });

  it("uses 今日研判 as the market-wide three-phase overview instead of another stock cockpit", async () => {
    window.history.replaceState({}, "", "/today-decision");
    const loadCockpit = vi.fn();
    const { container } = render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadDecisionCurrent={() => Promise.resolve(marketDecision())}
      loadAShareCandidates={() => Promise.resolve({ asset: "a_share", snapshot_id: null, input_snapshot_hash: null, universe_status: "empty", as_of: "2026-07-15", factor_version: "v1", short_term: [], swing: [], exclusions: [] })}
      searchAShareInstruments={() => Promise.resolve({ query: "", items: [], server_time: "2026-07-15T09:30:00+08:00", source_status: "ready" })}
      loadStockCockpit={loadCockpit}
    /></SelectedInstrumentProvider>);

    expect(await screen.findByRole("heading", { name: "今日判断与三阶段跟踪" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "盘前研判" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "盘中监测" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "盘后复盘" })).toBeInTheDocument();
    expect(screen.getByText("600000 · 等待放量确认")).toBeInTheDocument();
    expect(screen.getByText("000001 · 趋势仍需观察")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "选择观察股票" })).not.toBeInTheDocument();
    expect(loadCockpit).not.toHaveBeenCalled();
    expect(container.querySelector("main main")).toBeNull();
    expect(container.querySelectorAll("main")).toHaveLength(1);
  });

  it("places A-share market sentiment above the three-phase workbench", async () => {
    window.history.replaceState({}, "", "/today-decision");
    const { container } = render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadDecisionCurrent={() => Promise.resolve(emptyDecision)}
      loadMarketSentiment={() => Promise.resolve(marketSentiment)}
    /></SelectedInstrumentProvider>);

    const sentiment = await screen.findByRole("region", { name: "A 股市场情绪" });
    const workbench = await screen.findByRole("heading", { name: "今日判断与三阶段跟踪" });
    expect(sentiment.compareDocumentPosition(workbench) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(container.textContent).not.toMatch(/可转债市场情绪|转债情绪/);
  });

  it("filters 今日研判 only after the user explicitly chooses the selected A share", async () => {
    window.history.replaceState({}, "", "/today-decision?symbol=600000");
    render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadDecisionCurrent={() => Promise.resolve(marketDecision())}
    /></SelectedInstrumentProvider>);

    expect(await screen.findByText("000001 · 趋势仍需观察")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "只看 600000" }));
    expect(screen.getByText("600000 · 等待放量确认")).toBeInTheDocument();
    expect(screen.queryByText("000001 · 趋势仍需观察")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "全市场" }));
    expect(screen.getByText("000001 · 趋势仍需观察")).toBeInTheDocument();
  });

  it("keeps the selected A share while opening news", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><Dashboard loadSnapshot={() => Promise.resolve(card)}
      loadNewsIntelligence={() => Promise.resolve({ events: [], interpretations: [], corrections: [], briefings: [], quality: { article_count: 0, cluster_count: 0, event_count: 0, interpretation_count: 0, correction_count: 0, citation_coverage: "1", duplicate_rate: "0", invalid_json_rate: "0", provider_error_rate: "0", human_correction_rate: "0" } })}
      syncNews={() => Promise.resolve({ fetched: 0 })} createNewsCorrection={() => Promise.resolve()} /></SelectedInstrumentProvider>);
    fireEvent.click(screen.getByRole("button", { name: "新闻热点" }));
    expect(await screen.findByText("当前标的 600000")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/news-intelligence");
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600000");
  });

  it("opens real strategy backtesting from historical review for the selected A share", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    const runBacktest = vi.fn(() => new Promise<never>(() => undefined));
    render(<SelectedInstrumentProvider><Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadDecisionCurrent={() => Promise.resolve(emptyDecision)}
      runBacktest={runBacktest}
    /></SelectedInstrumentProvider>);

    fireEvent.click(screen.getByRole("button", { name: "历史复盘" }));

    expect(await screen.findByRole("heading", { name: "策略历史回测工作台" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "回测 A 股代码" })).toHaveValue("600000");
    fireEvent.click(screen.getByRole("button", { name: "运行回测" }));
    expect(runBacktest).toHaveBeenCalledWith("600000", expect.objectContaining({ strategy: "sma_cross" }), expect.any(AbortSignal));
  });

  it("keeps convertible bonds in an isolated route without the A-share symbol", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><Dashboard loadSnapshot={() => Promise.resolve(card)}
      loadBondDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadBondDiagnosis={() => Promise.reject(new Error("unused"))}
      loadBondCandidates={() => Promise.resolve({ status: "empty", items: [] })} /></SelectedInstrumentProvider>);
    fireEvent.click(screen.getByRole("button", { name: "可转债" }));
    expect(await screen.findByRole("heading", { name: "可转债专区" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/convertible-bonds");
    expect(new URL(window.location.href).searchParams.has("symbol")).toBe(false);
  });

  it("restores the last A-share selection after a bond round trip", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><Dashboard loadSnapshot={() => Promise.resolve(card)}
      loadBondDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadBondDiagnosis={() => Promise.reject(new Error("unused"))} loadBondCandidates={() => Promise.resolve({ status: "empty", items: [] })} /></SelectedInstrumentProvider>);
    fireEvent.click(screen.getByRole("button", { name: "可转债" }));
    expect(new URL(window.location.href).searchParams.has("symbol")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "今日研判" }));
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600000");
  });

  it("restores a settings deep link", () => {
    window.history.replaceState({}, "", "/settings");
    render(<Dashboard loadSnapshot={vi.fn(() => Promise.resolve(card))} />);
    expect(screen.getByRole("heading", { name: "数据源与 AI" })).toBeInTheDocument();
  });

  it("opens local operations on its stable first-level route", async () => {
    const operationsStatus = {
      scheduler: { paused: false, jobs: [] },
      backups: [],
      inventory: { generated_at: "2026-08-11T08:00:00Z", directories: {}, databases: {}, scan_limit: 5000 },
    };
    render(<Dashboard
      loadSnapshot={() => Promise.resolve(card)}
      loadOperationsStatus={() => Promise.resolve(operationsStatus)}
      setSchedulerPaused={() => Promise.resolve(operationsStatus.scheduler)}
      createBackup={() => Promise.reject(new Error("unused"))}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.reject(new Error("unused"))}
      cleanupCache={() => Promise.resolve({ removed_count: 0, removed_bytes: 0 })}
    />);

    fireEvent.click(screen.getByRole("button", { name: "本地运维" }));

    expect(window.location.pathname).toBe("/operations");
    expect(await screen.findByRole("heading", { name: "数据与运维中心" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "本地运维" })).toHaveAttribute("aria-current", "page");
  });

  it("does not pass an older stock preparation into settings for a new symbol", () => {
    const old = { symbol: "600000", preparation: { symbol: "600000", status: "ready", sources: [], refreshed: false, started_at: "2026-07-16T10:00:00+08:00", completed_at: "2026-07-16T10:00:01+08:00" } } as unknown as StockCockpitSnapshot;
    expect(preparationForSymbol(old, "000001")).toBeNull();
    expect(preparationForSymbol(old, "600000")?.symbol).toBe("600000");
  });

  it("selects only the matching candidate sentiment snapshot", () => {
    const batch = {
      candidate_snapshot_id: "candidate-1",
      candidate_input_hash: "a".repeat(64),
      items: [{ symbol: "600000" }, { symbol: "000001" }],
    } as CandidateSentimentBatch;

    expect(candidateSentimentForSymbol(batch, "000001")?.symbol).toBe("000001");
    expect(candidateSentimentForSymbol(batch, "300750")).toBeNull();
    expect(candidateSentimentForSymbol(null, "600000")).toBeNull();
    expect(candidateSentimentForSymbol(batch, null)).toBeNull();
  });
});
