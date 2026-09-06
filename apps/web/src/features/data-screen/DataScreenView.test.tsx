import { render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

import { DataScreenView } from "./DataScreenView";
import { findChangedSectorIds, sectorHighlightSignature } from "./sectorHighlights";
// ECharts is dynamically imported by QuantChart in production. Keep this view
// test focused on data/state rendering so jsdom does not wait on the chart
// runtime or a zero-sized SVG container.
vi.mock("../quant-analysis/QuantChart", () => ({
  QuantChart: ({ ariaLabel }: { ariaLabel: string }) => (
    <div role="img" aria-label={ariaLabel} />
  ),
}));
import type { MarketOverviewResponse } from "../market-overview/types";
import type { FirstLimitUpBoard } from "../first-limit-up/types";
import type { LateSessionSelectionResponse } from "../late-session-selection/types";
import type { BreakingNewsAlertResponse } from "../news-alerts/types";
import type { QuantStrategyDashboard } from "../quant-analysis/types";

const dataScreenCss = readFileSync(resolve(process.cwd(), "src/features/data-screen/dataScreen.css"), "utf8");
const dataScreenViewportCss = readFileSync(resolve(process.cwd(), "src/features/data-screen/dataScreenViewport.css"), "utf8");
const dataScreenSource = readFileSync(resolve(process.cwd(), "src/features/data-screen/DataScreenView.tsx"), "utf8");

const response: MarketOverviewResponse = {
  status: "ready", as_of: "2026-09-01", observed_at: "2026-09-01T02:00:00.000Z",
  sentiment: { score: "68", band: "偏强", coverage_percent: "99", quality: "ready", observed_at: "2026-09-01T02:00:00.000Z" },
  breadth: { rising_count: 3200, falling_count: 1500, flat_count: 200, valid_count: 4900 },
  limit_ecology: { limit_up_count: 80, limit_down_count: 5, broken_limit_up_count: 12, seal_rate_percent: "86.4" },
  liquidity: { total_amount_yi: "9800", baseline_amount_yi: "8600", relative_amount: "1.14" },
  market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-09-01T02:00:00.000Z", quote_count: 4900, universe_count: 5000, phase: "intraday", freshness: "live" },
  indices: [{ instrument: "sh000001", name: "上证指数", value: "3200", change: "12", change_percent: "0.38", observed_at: "2026-09-01T02:00:00.000Z", source: "tdx-local-rpc", quality: "ready" }],
  minute_series: [], anomalies: [], live_feed: [], sectors: [], sector_stocks: {}, market_stocks: [], warnings: [], sources: ["通达信"],
};

const lateSession: LateSessionSelectionResponse = {
  status: "ready", trading_date: "2026-09-01", server_time: "2026-09-01T06:00:00.000Z", phase: "live_monitor", monitor_stage: "monitor", refresh_interval_ms: 3000, next_refresh_ms: 3000,
  source_quality: "ready", universe_count: 5200, monitor_pool_count: 120, quote_count: 120, candidate_count: 1, rules: [], data_state: "ready", no_data_reason: null,
  settings: {} as LateSessionSelectionResponse["settings"], default_settings: {} as LateSessionSelectionResponse["default_settings"], candidates: [{
    quote: { symbol: "600519", name: "贵州茅台", price: "1600", change_percent: "3.20", volume_ratio: "1.8", turnover_rate: "2.1", market_cap_yi: "20000", twenty_day_limit_up_count: 1, intraday_average_price: "1588", observed_at: "2026-09-01T06:00:00.000Z", source: "tdx" },
    passed: true, rules: [], behavior_tags: ["尾盘平稳走高"], risk_notes: [], lifecycle_status: "strict_passed", first_seen_at: "2026-09-01T05:58:00.000Z", last_updated_at: "2026-09-01T06:00:00.000Z", continuous_hits: 3, continuous_seconds: 6, trigger_count: 1, rule_bitmap: "111", latest_change: "新增候选", invalidation_reason: null,
  }], invalidated_candidates: [], behaviors: [], source_evidence: [], limitations: [],
};

const firstLimitUp: FirstLimitUpBoard = {
  asset: "a_share", status: "ready", as_of: "2026-09-01", scan_date: "2026-09-01", expected_scan_date: "2026-09-01", scan_updated_at: "2026-09-01T06:00:00.000Z", refresh_required: false, rule_version: "first-limit-up-v1", universe_count: 5200, history_eligible_count: 5000, scan_coverage_count: 5000, coverage_complete: true, scanned_count: 5000, qualified_count: 1, pullback_window_count: 0, no_buy_count: 0,
  today: [{ symbol: "000001", name: "平安银行", as_of: "2026-09-01", limit_up_date: "2026-09-01", limit_up_close: "12.30", current_close: "12.30", pe_ttm: "6.2", limit_rate: "10.0", weekly_distance_to_low: "4.0", monthly_distance_to_low: "8.0", weekly_bottom: false, monthly_bottom: false, pullback_pct: "0", consolidation_days: 0, selection_status: "qualified", stage: "limit_up_day", action: "observe", score: "82", reasons: ["首次涨停"], risk_flags: [], sources: ["tdx"], entry_reference: { buy_steps_pct: [], sell_steps_pct: [], note: "" } }], pool: [], priority_symbol: "000001", missing_data: [], sources: ["tdx"],
};

const alerts: BreakingNewsAlertResponse = {
  status: "ready", observed_at: "2026-09-01T06:00:00.000Z", sources: ["verified-news"], warnings: [], alerts: [{ event_id: "news-1", headline: "银行板块资金流入扩大", occurred_at: "2026-09-01T05:59:00.000Z", verification_state: "verified", urgency: "breaking", association_kind: "theme", association_reasons: [], affected_symbols: ["000001"], themes: ["银行"], publishers: ["交易所"], source_urls: [], source_count: 1, impact_direction: "positive", impact_confidence: "0.9", ai_degraded: false }],
};

const nineAlerts: BreakingNewsAlertResponse = {
  ...alerts,
  alerts: Array.from({ length: 9 }, (_, index) => ({
    ...alerts.alerts[0],
    event_id: `news-${index + 1}`,
    headline: `实时快讯 ${index + 1}`,
    verification_state: index % 3 === 0 ? "verified" : index % 3 === 1 ? "pending" : "unverified",
    urgency: index % 2 === 0 ? "tracking" : "normal",
    impact_direction: index % 3 === 0 ? "positive" : index % 3 === 1 ? "negative" : "neutral",
    affected_symbols: index % 2 === 0 ? ["000001"] : [],
  })),
};

const tenAlerts: BreakingNewsAlertResponse = {
  ...nineAlerts,
  alerts: [...nineAlerts.alerts, { ...nineAlerts.alerts[0], event_id: "news-10", headline: "实时快讯 10" }],
};

const quantStrategy: QuantStrategyDashboard = {
  status: "ready", as_of: "2026-09-01", observed_at: "2026-09-01T06:00:00.000Z", generated_at: "2026-09-01T06:00:00.000Z", market_observed_at: "2026-09-01T06:00:00.000Z", data_age_seconds: 2, refresh_mode: "live", refresh_state: "ready", snapshot_at: "2026-09-01T06:00:00.000Z", refresh_started_at: "2026-09-01T05:59:59.000Z", refresh_finished_at: "2026-09-01T06:00:00.000Z", snapshot_source: "quant-engine", next_refresh_at: "2026-09-01T06:00:05.000Z", candidate_scan_at: "2026-09-01T06:00:00.000Z", candidate_scan_age_seconds: 2, candidate_scan_cached: false, candidate_scan_state: "ready", candidate_scan_started_at: "2026-09-01T05:59:59.000Z", candidate_scan_error: null, candidate_scan_phase: "ready", candidate_scan_processed: 5000, candidate_scan_total: 5000, trigger_evidence_at: "2026-09-01T06:00:00.000Z", trigger_evidence_age_seconds: 2, trigger_evidence_cached: false, formula_version: "a-share-short-strategy-v2.0", metrics: {} as QuantStrategyDashboard["metrics"], regime: { regime: "轮动震荡", emotion_score: "68", risk_score: "32", heat_score: "72", rotation_score: "66", coverage_percent: "98", market_coef: "1.0", suitable_strategies: [], avoid_strategies: [], reasons: [], missing_factors: [], rule_matched: true, quality: "ready", formula_version: "a-share-short-strategy-v2.0" }, strategy_models: [], candidates: [{ symbol: "600519", name: "贵州茅台", model: "趋势突破", strategy_score: "88", regime_match: "适配", stock_score: "86", trigger_score: "90", rr_score: "82", risk_penalty: "8", status: "alert", trigger_confirmed: true, position: "观察", planned_position: "轻仓", evidence_coverage_percent: "96", buy_triggers: ["放量突破"], invalidation_rules: ["跌破支撑"], risk_flags: [], missing_evidence: [], factor_as_of: "2026-09-01", sources: ["tdx"] }], discipline: "只在证据充分时触发", missing_data: [], warnings: [], sources: ["量化引擎"],
};

describe("DataScreenView", () => {
  it("ships the dedicated projection layout and digital-twin visual layer", () => {
    expect(dataScreenCss).toContain(".data-screen-grid");
    expect(dataScreenCss).toContain(".data-screen-flow-canvas");
    expect(dataScreenCss).toContain(".data-screen-kpi-ribbon");
    expect(dataScreenCss).toContain(".data-screen-up");
    expect(dataScreenCss).toContain(".data-screen-down");
    expect(dataScreenCss).toMatch(/\.data-screen-indices \.terminal-panel-body[\s\S]*?display:\s*flex/);
    expect(dataScreenCss).toMatch(/\.data-screen-intraday-chart[\s\S]*?flex:\s*1 1 auto/);
    expect(dataScreenCss).toContain("grid-template-rows: repeat(2, minmax(0, 1fr))");
  });

  it("defines the compact C3 information hierarchy", () => {
    expect(dataScreenCss).toContain("data-screen-c3");
    expect(dataScreenCss).toContain("data-screen-left-matrix");
    expect(dataScreenCss).toContain("data-screen-chart-news-list");
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-grid[\s\S]*grid-template-areas/);
    expect(dataScreenCss).toContain("grid-template-columns: minmax(0, 28fr) minmax(0, 44fr) minmax(0, 28fr)");
    expect(dataScreenCss).toContain("grid-area: filter");
    expect(dataScreenCss).toContain("grid-area: stocks");
    expect(dataScreenCss).toContain(".data-screen-hologram-corners");
    expect(dataScreenCss).toContain(".data-screen-radar-page");
  });

  it("keeps centre news styled while removing the retired footer news rail", () => {
    expect(dataScreenCss).toContain(".data-screen-chart-news-list");
    expect(dataScreenCss).not.toContain(".data-screen-news-viewport");
    expect(dataScreenCss).not.toContain(".data-screen-news-track");
    expect(dataScreenCss).toContain("screen-flow-marquee");
    expect(dataScreenCss).toContain(".data-screen-flow-scroll-viewport.is-paused");
  });

  it("keeps the centre chart zone focused on market data", async () => {
    expect(dataScreenCss).toContain(".data-screen-chart-sector");
    expect(dataScreenCss).toContain(".data-screen-chart-capital-share");
    render(<DataScreenView load={vi.fn(async () => response)} loadAlerts={vi.fn(async () => alerts)} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "指数与市场图表" })).toBeInTheDocument());
    expect(screen.queryByRole("region", { name: "数据大屏新闻" })).not.toBeInTheDocument();
    expect(screen.queryByText("涨跌分布")).not.toBeInTheDocument();
    expect(screen.getByText("板块成交额占比 · 北向资金待接入")).toBeInTheDocument();
  });

  it("shows the real overseas index and eight overseas indicators in one panel", async () => {
    const overseas = {
      quality: "ready",
      trading_label: "美股 2026-09-02 最近收盘",
      source: "tencent_overseas",
      source_trading_date: "2026-09-02",
      observed_at: "2026-09-02T20:00:00.000Z",
      reason: null,
      indices: ["道琼斯", "标普500", "纳斯达克"].map((name, index) => ({ symbol: `us-index-${index}`, name, ticker: name, region: "index", price: "40000", change: "1", change_percent: "0.1", observed_at: "2026-09-02T20:00:00.000Z", trading_state: "最近收盘", quality: "ready" })),
      mag7: [
        ["苹果", "AAPL"], ["微软", "MSFT"], ["英伟达", "NVDA"], ["谷歌", "GOOGL"],
        ["亚马逊", "AMZN"], ["Meta", "META"], ["特斯拉", "TSLA"], ["博通", "AVGO"],
      ].map(([name, ticker], index) => ({ symbol: `us-stock-${index}`, name, ticker, region: "mag7", price: "200", change: "1", change_percent: "0.5", observed_at: "2026-09-02T20:00:00.000Z", trading_state: "最近收盘", quality: "ready" })),
    };
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(overseas), { status: 200 }))));
    render(<DataScreenView load={vi.fn(async () => response)} />);
    const panel = await waitFor(() => screen.getByRole("region", { name: "美股八个风向标" }));
    expect(within(panel).getByText("隔夜外盘")).toBeInTheDocument();
    expect(within(panel).getAllByText("道琼斯").length).toBeGreaterThan(0);
    expect(within(panel).getAllByText("特斯拉").length).toBeGreaterThan(0);
    expect(within(panel).getAllByText("博通").length).toBeGreaterThan(0);
    expect(within(panel).getAllByText("AVGO").length).toBeGreaterThan(0);
    expect(within(panel).getByText("美股港股的涨跌幅都是对比它们各自的前一交易日收盘。港股在北京时间白天可能正在交易，所以会标「盘中」——那是抓取那一刻的延时行情，没标具体几点。")).toBeInTheDocument();
    expect(within(panel).getByText("美股 2026-09-02 最近收盘 · 来源：腾讯财经")).toBeInTheDocument();
  });

  it("moves overnight markets into sector sentiment, puts breadth in the lower right, and keeps fund flow as a vertical tape", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} />);
    const sectorSentiment = await screen.findByRole("region", { name: "行业板块列表" });
    const overseas = screen.getByRole("region", { name: "美股八个风向标" });
    const sectorBreadth = screen.getByRole("region", { name: "板块广度与主线" });
    const sectorFlow = screen.getByRole("region", { name: "行业资金流向" });

    expect(sectorSentiment).toContainElement(overseas);
    expect(sectorBreadth).toHaveClass("data-screen-sector-breadth-panel");
    expect(sectorBreadth.querySelectorAll(".data-screen-sector-breadth-row")).toHaveLength(0);
    expect(sectorFlow).toHaveClass("data-screen-sector-flow-tape-panel");
    expect(within(sectorFlow).getByText("暂无有效行业资金数据")).toBeInTheDocument();
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-vertical-rail \.data-screen-loop-track\s*\{[\s\S]*?animation:\s*screen-sector-flow-vertical-marquee/);
  });

  it("removes the redundant left-panel heading and verified-topic tag block", async () => {
    render(<DataScreenView load={vi.fn(async () => ({ ...response, sectors: [] }))} loadAlerts={vi.fn(async () => alerts)} />);
    const sectorPanel = await screen.findByRole("region", { name: "行业板块列表" });
    expect(within(sectorPanel).queryByText("板块情绪")).not.toBeInTheDocument();
    expect(within(sectorPanel).queryByText(/已核验题材热度/)).not.toBeInTheDocument();
    expect(sectorPanel).toHaveClass("data-screen-panel-headerless");
  });

  it("places sector turnover share immediately to the right of sector gains", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-chart-stack:not\(\.has-news\)\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);[\s\S]*?grid-template-rows:\s*minmax\(0, 1\.45fr\) minmax\(0, 1fr\);/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-chart-stack:not\(\.has-news\) \.data-screen-chart-sector\s*\{[\s\S]*?grid-column:\s*1;[\s\S]*?grid-row:\s*2;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-chart-stack:not\(\.has-news\) \.data-screen-chart-capital-share\s*\{[\s\S]*?grid-column:\s*2;[\s\S]*?grid-row:\s*2;/);
  });

  it("keeps realtime news static while limit pools scroll without underline bars", async () => {
    const marketStocks = [
      { symbol: "000001", name: "平安银行", price: "12.3", previous_close: "11.18", open: "11.2", high: "12.3", low: "11.1", volume: "100", amount_yi: "12", change_percent: "10", state: "limit_up", observed_at: "2026-09-01T06:00:00.000Z", source: "tdx", quality: "ready" },
      { symbol: "000002", name: "万科A", price: "6.1", previous_close: "6.78", open: "6.7", high: "6.8", low: "6.1", volume: "80", amount_yi: "8", change_percent: "-10", state: "limit_down", observed_at: "2026-09-01T06:00:00.000Z", source: "tdx", quality: "ready" },
    ] as MarketOverviewResponse["market_stocks"];
    render(<DataScreenView load={vi.fn(async () => ({ ...response, market_stocks: marketStocks }))} loadAlerts={vi.fn(async () => alerts)} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "当前涨停股票" })).toBeInTheDocument());
    const limitUpRegion = screen.getByRole("region", { name: "当前涨停股票" });
    const limitDownRegion = screen.getByRole("region", { name: "当前跌停股票" });
    expect(limitDownRegion).toBeInTheDocument();
    expect(screen.getAllByText("平安银行").length).toBeGreaterThan(0);
    expect(screen.getAllByText("万科A").length).toBeGreaterThan(0);
    expect(limitUpRegion.querySelector(".data-screen-loop-viewport")).toHaveClass("is-looping");
    expect(limitDownRegion.querySelector(".data-screen-loop-viewport")).toHaveClass("is-looping");
    expect(within(limitUpRegion).getByText(/循环滚动/)).toBeInTheDocument();
    expect(within(limitDownRegion).getByText(/循环滚动/)).toBeInTheDocument();
    expect(dataScreenCss).toMatch(/\.data-screen-limit-stock-row\s*\{[^}]*border:\s*0;/);
    expect(dataScreenCss).toMatch(/\.data-screen-limit-stock-row:hover,[\s\S]*?background:/);
    const newsRegion = screen.getByRole("region", { name: "实时资讯" });
    const newsCard = within(newsRegion).getByText(alerts.alerts[0].headline).closest("article");
    expect(newsCard).not.toHaveAttribute("style");
    expect(dataScreenCss).not.toMatch(/\.data-screen-news-card[^}]*animation:/);
    expect(dataScreenCss).not.toMatch(/\.data-screen-news-card\.is-breaking[^}]*animation:/);
    expect(dataScreenCss).not.toMatch(/\.data-screen-pulse \.data-screen-news-card[^}]*animation:/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-panel\s*\{[^}]*animation:\s*none;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-panel::before\s*\{[^}]*animation:\s*none;/);
  });

  it("keeps limit-pool scrolling at a stable per-row cadence after track duplication", async () => {
    const marketStocks = Array.from({ length: 4 }, (_, index) => ({
      symbol: `00000${index + 1}`,
      name: `测试股票${index + 1}`,
      price: "12.3",
      previous_close: "11.18",
      open: "11.2",
      high: "12.3",
      low: "11.1",
      volume: "100",
      amount_yi: "12",
      change_percent: index % 2 === 0 ? "10" : "-10",
      state: index % 2 === 0 ? "limit_up" : "limit_down",
      observed_at: "2026-09-01T06:00:00.000Z",
      source: "tdx",
      quality: "ready" as const,
    })) as MarketOverviewResponse["market_stocks"];
    render(<DataScreenView load={vi.fn(async () => ({ ...response, market_stocks: marketStocks }))} />);
    const limitUpRegion = await screen.findByRole("region", { name: "当前涨停股票" });
    const track = limitUpRegion.querySelector<HTMLElement>(".data-screen-loop-track");
    expect(track?.style.getPropertyValue("--data-screen-loop-duration")).toBe("8s");
  });

  it("moves the static realtime limit pools below the centre charts", async () => {
    const marketStocks = [
      { symbol: "000001", name: "平安银行", price: "12.3", previous_close: "11.18", open: "11.2", high: "12.3", low: "11.1", volume: "100", amount_yi: "12", change_percent: "10", state: "limit_up", observed_at: "2026-09-01T06:00:00.000Z", source: "tdx", quality: "ready" },
      { symbol: "000002", name: "万科A", price: "6.1", previous_close: "6.78", open: "6.7", high: "6.8", low: "6.1", volume: "80", amount_yi: "8", change_percent: "-10", state: "limit_down", observed_at: "2026-09-01T06:00:00.000Z", source: "tdx", quality: "ready" },
    ] as MarketOverviewResponse["market_stocks"];
    render(<DataScreenView load={vi.fn(async () => ({ ...response, market_stocks: marketStocks }))} />);
    const centre = await screen.findByRole("region", { name: "指数与市场图表" });
    const news = screen.getByRole("region", { name: "实时资讯" });
    expect(within(centre).getByRole("region", { name: "当前涨停股票" })).toBeInTheDocument();
    expect(within(centre).getByRole("region", { name: "当前跌停股票" })).toBeInTheDocument();
    expect(within(centre).getByRole("region", { name: "资金轮动" })).toBeInTheDocument();
    expect(within(news).queryByRole("region", { name: "当前涨停股票" })).not.toBeInTheDocument();
    expect(within(news).queryByRole("region", { name: "当前跌停股票" })).not.toBeInTheDocument();
    expect(dataScreenCss).toMatch(/\.data-screen-center-monitor-stack\s*\{[\s\S]*?grid-template-rows:\s*minmax\(0, 1\.65fr\) minmax\(190px, \.75fr\);/);
    expect(dataScreenCss).toMatch(/\.data-screen-center-limit-board\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);/);
    expect(dataScreenCss).toMatch(/\.data-screen-capital-rotation-pair\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
    expect(dataScreenCss).toMatch(/\.data-screen-capital-rotation-row\s*\{[\s\S]*?grid-template-columns:\s*24px minmax\(0, 1fr\) 76px 88px;/);
    expect(dataScreenCss).toMatch(/\.data-screen-capital-rotation-row\s*\{[\s\S]*?column-gap:\s*12px;/);
    expect(dataScreenCss).toMatch(/\.data-screen-capital-rotation-row\s*>\s*span[\s\S]*?text-align:\s*center;/);
    expect(dataScreenCss).toMatch(/\.data-screen-capital-rotation-row\s*>\s*strong[\s\S]*?text-align:\s*right;/);
  });

  it("splits sector fund flow into inflow and outflow rotation columns", async () => {
    const flowResponse = {
      ...response,
      sectors: [
        { sector_id: "S1", name: "证券", change_percent: "1.62", amount_yi: "100", limit_up_count: 1, rising_count: 20, falling_count: 3, stock_count: 23 },
        { sector_id: "S2", name: "半导体", change_percent: "-0.91", amount_yi: "90", limit_up_count: 0, rising_count: 4, falling_count: 18, stock_count: 22 },
      ],
      sector_fund_flow: [
        { sector_code: "S1", sector_name: "证券", observed_at: response.observed_at, main_net_yi: "28.26", large_net_yi: null, super_net_yi: null, source: "test", quality: "ready" as const },
        { sector_code: "S2", sector_name: "半导体", observed_at: response.observed_at, main_net_yi: "-39.46", large_net_yi: null, super_net_yi: null, source: "test", quality: "ready" as const },
      ],
    } satisfies MarketOverviewResponse;
    render(<DataScreenView load={vi.fn(async () => flowResponse)} />);
    const rotation = await screen.findByRole("region", { name: "资金轮动" });
    expect(within(rotation).getByRole("region", { name: "流入 Top" })).toHaveTextContent("证券");
    expect(within(rotation).getByRole("region", { name: "流出 Top" })).toHaveTextContent("半导体");
    expect(within(rotation).getByText("+28.26 亿")).toBeInTheDocument();
    expect(within(rotation).getByText("-39.46 亿")).toBeInTheDocument();
  });

  it("shows the live dashboard once the shared market snapshot arrives", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} />);
    expect(screen.getByRole("heading", { name: "数据大屏" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "行业板块列表" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("上证指数")).toBeInTheDocument());
    expect(screen.getByText("实时市场监控中")).toBeInTheDocument();
    expect(screen.getAllByText(/98\.0% 行情覆盖/).length).toBeGreaterThan(0);
    expect(screen.queryByText("北向资金")).not.toBeInTheDocument();
    expect(screen.queryByText(/沪股通 \+ 深股通 · 当前来源未提供/)).not.toBeInTheDocument();
    expect(screen.getByText("市场情绪")).toBeInTheDocument();
    expect(screen.getByText(/距收盘|距开盘|等待下一交易时段/)).toBeInTheDocument();
  });

  it("shows consecutive and first-board ladders from the shared review snapshot", async () => {
    const review = {
      as_of: response.as_of,
      observed_at: response.observed_at,
      latest_trade_date: response.as_of,
      source: "tdx-local-day",
      quality: "ready" as const,
      universe_count: 5000,
      history_ready_count: 5000,
      consecutive_limit_up: Array.from({ length: 6 }, (_, index) => ({
        symbol: `60000${index + 1}`,
        name: `连板股${index + 1}`,
        trade_date: response.as_of,
        category: "consecutive_limit_up" as const,
        close: "10",
        change_percent: "10",
        amount_yi: "1",
        source: "tdx-local-day",
        board_count: index + 2,
        limit_statistics: `${index + 2}/${index + 2}`,
        prior_close: null,
        prior_change_percent: null,
        turnover_rate: null,
        seal_amount_yi: null,
        failed_limit_count: null,
        first_seal_time: null,
        volume_multiple: null,
        reference_high: null,
        window_days: null,
        range_position_percent: null,
      })),
      first_limit_up: [{
        symbol: "000001",
        name: "首板股",
        trade_date: response.as_of,
        category: "first_limit_up" as const,
        close: "10",
        change_percent: "10",
        amount_yi: "1",
        source: "tdx-local-day",
        board_count: 1,
        limit_statistics: "1/1",
        prior_close: null,
        prior_change_percent: null,
        turnover_rate: null,
        seal_amount_yi: null,
        failed_limit_count: null,
        first_seal_time: null,
        volume_multiple: null,
        reference_high: null,
        window_days: null,
        range_position_percent: null,
      }],
      new_high_100: [],
      previous_limit_up: [],
      volume_breakouts: [],
      previous_high_breakouts: [],
      low_position_volume: [],
      dragon_tiger: [],
      warnings: [],
      formula_version: "test",
    } satisfies NonNullable<MarketOverviewResponse["review"]>;
    render(<DataScreenView load={vi.fn(async () => ({ ...response, review }))} />);
    const consecutive = await screen.findByRole("region", { name: "连板梯队" });
    const first = screen.getByRole("region", { name: "首板梯队" });
    const ecology = screen.getByRole("region", { name: "封板生态统计" });
    expect(within(consecutive).getAllByText("连板股1").length).toBeGreaterThan(0);
    expect(within(first).getByText("首板股")).toBeInTheDocument();
    expect(within(ecology).getByText("封板数量")).toBeInTheDocument();
    expect(within(ecology).getByText("80")).toBeInTheDocument();
    expect(within(ecology).getByText(/炸板率 13\.0%/)).toBeInTheDocument();
    expect(within(ecology).getByText("封住 / 尝试涨停")).toBeInTheDocument();
    expect(within(ecology).getByText("炸板 / 尝试涨停")).toBeInTheDocument();
    expect(within(ecology).getByText("前一交易日涨停的票，又封住")).toBeInTheDocument();
    expect(consecutive.querySelector(".data-screen-ladder-rail")).toHaveClass("is-looping");
    expect(dataScreenCss).toContain("data-screen-ladder-pair");
    expect(dataScreenCss).toMatch(/data-screen-ladder-rail[\s\S]*min-height:\s*calc\(5 \* 34px \+ 4 \* 4px/);
  });

  it("colors top market numbers by their financial meaning", async () => {
    const coloredResponse: MarketOverviewResponse = {
      ...response,
      indices: [
        { instrument: "sh000001", name: "上证指数", value: "3941.39", change: "-38.50", change_percent: "-0.97", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sz399001", name: "深证成指", value: "13611.55", change: "-260.83", change_percent: "-1.88", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sz399006", name: "创业板指", value: "3312.24", change: "81.19", change_percent: "2.39", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
      ],
    };
    render(<DataScreenView load={vi.fn(async () => coloredResponse)} />);
    const ribbon = await screen.findByRole("region", { name: "市场核心指标" });
    expect(within(ribbon).getByText("3941.39")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("13611.55")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("3312.24")).toHaveClass("data-screen-up");
    expect(within(ribbon).getByText("9,800")).toHaveClass("data-screen-kpi-gold");
    expect(within(ribbon).getByText("3,200")).toHaveClass("data-screen-up");
    expect(within(ribbon).getByText("1,500")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("80")).toHaveClass("data-screen-up");
    expect(within(ribbon).getByText("5")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("68")).toHaveClass("data-screen-quantum");
    expect(dataScreenCss).toMatch(/\.data-screen-kpi-gold\s*\{[^}]*color:\s*var\(--screen-gold\)/);
    expect(dataScreenCss).toMatch(/\.data-screen-quantum\s*\{[^}]*color:\s*#c084fc/);
  });

  it("shows 科创50 and 中证500 after 创业板指 with real quote values", async () => {
    const fiveIndexResponse: MarketOverviewResponse = {
      ...response,
      indices: [
        { instrument: "sh000001", name: "上证指数", value: "3200.11", change: "12.10", change_percent: "0.38", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sz399001", name: "深证成指", value: "10500.22", change: "-21.00", change_percent: "-0.20", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sz399006", name: "创业板指", value: "2200.33", change: "8.80", change_percent: "0.40", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sh000688", name: "科创50", value: "1001.44", change: "-5.10", change_percent: "-0.51", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
        { instrument: "sh000905", name: "中证500", value: "5900.55", change: "35.40", change_percent: "0.60", observed_at: response.observed_at, source: "tdx-local-rpc", quality: "ready" },
      ],
    };
    render(<DataScreenView load={vi.fn(async () => fiveIndexResponse)} />);
    const ribbon = await screen.findByRole("region", { name: "市场核心指标" });
    const labels = Array.from(ribbon.querySelectorAll(":scope > div > small")).map((node) => node.textContent);
    expect(labels.slice(0, 6)).toEqual(["上证指数", "深证成指", "创业板指", "科创50", "中证500", "两市成交额"]);
    expect(within(ribbon).getByText("1001.44")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("5900.55")).toHaveClass("data-screen-up");
    expect(within(ribbon).getByText("-0.51% · -5.10点")).toHaveClass("data-screen-down");
    expect(within(ribbon).getByText("+0.60% · +35.40点")).toHaveClass("data-screen-up");
  });

  it("labels empty outflow rotation as no negative-flow industry instead of an unconnected source", async () => {
    const inflowOnly = {
      ...response,
      sector_fund_flow: [{ sector_code: "BK0001", sector_name: "证券", observed_at: response.observed_at, main_net_yi: "28.26", large_net_yi: null, super_net_yi: null, source: "test", quality: "ready" as const }],
    } satisfies MarketOverviewResponse;
    render(<DataScreenView load={vi.fn(async () => inflowOnly)} />);
    const rotation = await screen.findByRole("region", { name: "资金轮动" });
    expect(within(rotation).getByRole("region", { name: "流出 Top" })).toHaveTextContent("暂无净流出行业");
    expect(within(rotation).getByRole("region", { name: "流出 Top" })).not.toHaveTextContent("待接入");
  });

  it("keeps split market KPI numbers at the same readable size as other KPIs", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-kpi-ribbon \.data-screen-kpi-split\s*>\s*span\s*\{[^}]*font-size:\s*inherit;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-kpi-ribbon \.data-screen-kpi-split\s*>\s*i\s*\{[^}]*font-size:\s*inherit;/);
  });

  it("keeps realtime news cards compact instead of stretching empty space", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-grid\s*\{[\s\S]*?grid-auto-rows:\s*minmax\(56px, 1fr\);[\s\S]*?gap:\s*5px;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card\s*\{[\s\S]*?grid-template-rows:\s*auto auto;[\s\S]*?gap:\s*2px 5px;[\s\S]*?padding:\s*5px 6px;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card b\s*\{[\s\S]*?min-height:\s*0;[\s\S]*?line-height:\s*1\.2;/);
  });

  it("shows urgency, verification, impact, and confidence tags on realtime news", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} loadAlerts={vi.fn(async () => alerts)} />);
    const news = await screen.findByRole("region", { name: "实时资讯" });
    const card = within(news).getByText(alerts.alerts[0].headline).closest("article");
    expect(card).toHaveTextContent("突发");
    expect(card).toHaveTextContent("已核验");
    expect(card).toHaveTextContent("可信度 90%");
    expect(card).toHaveTextContent("正向");
    expect(card?.querySelectorAll(".data-screen-news-tags small")).toHaveLength(4);
  });

  it("renders live news and limit-board feeds in compact dedicated regions", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} loadLateSession={vi.fn(async () => lateSession)} loadFirstLimitUp={vi.fn(async () => firstLimitUp)} loadAlerts={vi.fn(async () => alerts)} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "当前涨停股票" })).toBeInTheDocument());
    expect(screen.getByRole("region", { name: "实时资讯" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "当前跌停股票" })).toBeInTheDocument();
  });

  it("shows quant hits and late-session candidates in a compact two-column rail below news", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} loadLateSession={vi.fn(async () => lateSession)} loadQuantStrategy={vi.fn(async () => quantStrategy)} loadAlerts={vi.fn(async () => alerts)} />);
    const news = await screen.findByRole("region", { name: "实时资讯" });
    const quantRegion = within(news).getByRole("region", { name: "量化命中" });
    const lateRegion = within(news).getByRole("region", { name: "尾盘选股" });
    expect(within(quantRegion).getByText("贵州茅台")).toBeInTheDocument();
    expect(within(lateRegion).getByText("贵州茅台")).toBeInTheDocument();
    expect(within(quantRegion).getByText("600519 · 趋势突破")).toBeInTheDocument();
    expect(within(lateRegion).getByText("600519 · 尾盘平稳走高")).toBeInTheDocument();
    expect(dataScreenCss).toMatch(/\.data-screen-news-signal-pair\s*\{[\s\S]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-panel-layout\s*\{[\s\S]*grid-template-areas:\s*"feed" "signals"/);
  });

  it("keeps every real sector fund-flow item in the continuous vertical tape", async () => {
    const flowResponse = {
      ...response,
      sector_fund_flow: Array.from({ length: 12 }, (_, index) => ({
        sector_code: `S${index + 1}`,
        sector_name: `行业${index + 1}`,
        observed_at: response.observed_at,
        main_net_yi: String(index + 1),
        large_net_yi: null,
        super_net_yi: null,
        source: "test",
        quality: "ready" as const,
      })),
    } satisfies MarketOverviewResponse;
    render(<DataScreenView load={vi.fn(async () => flowResponse)} loadAlerts={vi.fn(async () => alerts)} />);
    const news = await screen.findByRole("region", { name: "实时资讯" });
    const sectorFlow = screen.getByRole("region", { name: "行业资金流向" });
    expect(within(news).queryByRole("region", { name: "行业资金流向" })).not.toBeInTheDocument();
    expect(sectorFlow).toBeInTheDocument();
    expect(sectorFlow).toHaveClass("data-screen-sector-flow-tape-panel");
    expect(sectorFlow.querySelectorAll(".data-screen-sector-flow-item")).toHaveLength(24);
    expect(sectorFlow.querySelector(".data-screen-sector-flow-track")).toBeInTheDocument();
    expect(sectorFlow.querySelector(".data-screen-sector-flow-vertical-rail")).toBeInTheDocument();
    expect(within(sectorFlow).getAllByText("行业12")).toHaveLength(2);
    expect(within(sectorFlow).getAllByText("行业10")).toHaveLength(2);
    expect(within(sectorFlow).getAllByText("行业2")).toHaveLength(2);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-vertical-rail \.data-screen-loop-track\s*\{[\s\S]*animation:\s*screen-sector-flow-vertical-marquee/);
  });

  it("renders each sector fund-flow row on one line and scrolls the tape upward", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-track\s*\{[\s\S]*?animation:\s*none\s*!important;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-vertical-rail \.data-screen-loop-track\s*\{[\s\S]*?display:\s*grid;[\s\S]*?width:\s*100%;[\s\S]*?animation:\s*screen-sector-flow-vertical-marquee/);
    expect(dataScreenCss).toMatch(/@keyframes screen-sector-flow-vertical-marquee[\s\S]*?translate3d\(0,\s*-50%/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-item\s*\{[\s\S]*?grid-template-columns:\s*minmax\(80px, \.65fr\) auto minmax\(0, 1\.35fr\);[\s\S]*?grid-template-rows:\s*1fr;/);
    expect(dataScreenCss).toMatch(/\.data-screen-sector-flow-detail\s*\{[\s\S]*?grid-column:\s*auto;/);
  });

  it("shows a concise empty state when no verified sector fund-flow data is available", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} />);
    const sectorFlow = await screen.findByRole("region", { name: "行业资金流向" });
    expect(sectorFlow.querySelectorAll(".data-screen-sector-flow-item")).toHaveLength(0);
    expect(within(sectorFlow).getByText("暂无有效行业资金数据")).toBeInTheDocument();
  });

  it("keeps the sector strength area bounded instead of letting content stretch the panel", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sectors \.terminal-panel-body\s*\{[\s\S]*?min-height:\s*0;[\s\S]*?overflow:\s*hidden;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sectors \.data-screen-opportunity-sections\s*\{[\s\S]*?grid-template-rows:\s*minmax\(0, 1fr\)\s+minmax\(0, \.9fr\)\s+auto\s+auto;[\s\S]*?height:\s*100%;[\s\S]*?min-height:\s*0;[\s\S]*?overflow:\s*hidden;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sectors \.data-screen-sector-tags\s*\{[\s\S]*?overflow-y:\s*auto;[\s\S]*?overflow-x:\s*hidden;/);
  });

  it("lets the ladder rails fill their section and keeps ecology card borders visible", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-ladder-rail\s*\{[\s\S]*?max-height:\s*none;[\s\S]*?overflow:\s*hidden;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-limit-ecology-section\s*\{[\s\S]*?display:\s*flex;[\s\S]*?flex-direction:\s*column;[\s\S]*?box-sizing:\s*border-box;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-limit-ecology-grid\s*\{[\s\S]*?flex:\s*1 1 auto;[\s\S]*?height:\s*auto;[\s\S]*?box-sizing:\s*border-box;/);
  });

  it("removes the bottom scrolling news ticker", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} loadAlerts={vi.fn(async () => tenAlerts)} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "实时资讯" })).toBeInTheDocument());
    expect(document.querySelector(".data-screen-news-ticker")).not.toBeInTheDocument();
    expect(document.querySelector(".data-screen-footer")).not.toBeInTheDocument();
  });

  it("keeps two complete headline lines without stretching empty card space", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card\s*\{[\s\S]*?grid-template-columns:\s*42px minmax\(0, 1fr\) auto;[\s\S]*?grid-template-rows:\s*auto auto;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card b\s*\{[\s\S]*?grid-column:\s*2 \/ 4;[\s\S]*?min-height:\s*0;[\s\S]*?line-height:\s*1\.2;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card span\s*\{[\s\S]*?grid-column:\s*1 \/ 3;[\s\S]*?grid-row:\s*2;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-news-card small\s*\{[\s\S]*?grid-column:\s*3;[\s\S]*?grid-row:\s*2;/);
  });

  it("keeps capital content filling its panel and the first flow row visible", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-capital \.terminal-panel-body[\s\S]*?display:\s*flex/);
    expect(dataScreenCss).toContain(".data-screen-capital-content");
    expect(dataScreenCss).toMatch(/\.data-screen-flow-scroll-viewport\s*\{[\s\S]*?padding-block-start:\s*\d+px/);
    expect(dataScreenCss).not.toMatch(/mask-image:\s*linear-gradient\(180deg,\s*transparent/);
  });

  it("keeps market-stat labels, values, and notes fully visible in compact cells", () => {
    expect(dataScreenCss).toMatch(/\/\* Keep each market-stat cell readable[\s\S]*?\.data-screen-c3 \.data-screen-capital-grid\s*\{[\s\S]*?grid-template-rows:\s*repeat\(2, minmax\(54px, 1fr\)\);[\s\S]*?grid-auto-rows:\s*auto;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-capital-grid > div\s*\{[\s\S]*?align-content:\s*center;[\s\S]*?gap:\s*1px;[\s\S]*?padding:\s*3px 6px;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-capital-grid small,[\s\S]*?line-height:\s*1;/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-capital-grid span\s*\{[\s\S]*?line-height:\s*1;/);
  });

  it("keeps the flat count in the top KPI ribbon and removes retired KPI cards", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} />);
    const kpis = await screen.findByRole("region", { name: "市场核心指标" });
    expect(within(kpis).getByText("平盘家数")).toBeInTheDocument();
    expect(within(kpis).queryByText("炸板数量")).not.toBeInTheDocument();
    expect(within(kpis).getByText("200")).toBeInTheDocument();
    expect(within(kpis).getByText(/封板率 86\.4%/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "市场统计" })).not.toBeInTheDocument();
  });

  it("strengthens projection motion without changing the dashboard layout", () => {
    expect(dataScreenCss).toMatch(/animation:\s*screen-scanline\s+7s\s+linear\s+infinite/);
    expect(dataScreenCss).toMatch(/animation:\s*screen-particle-drift\s+18s\s+linear\s+infinite/);
    expect(dataScreenCss).toMatch(/@keyframes screen-panel-breathe[\s\S]*rgba\(57, 214, 206, \.14\)/);
    expect(dataScreenCss).toMatch(/@keyframes screen-number-tick[\s\S]*scale\(1\.045\)/);
    expect(dataScreenCss).toMatch(/@keyframes screen-quant-hit-flash[\s\S]*0 0 30px rgba\(57, 214, 206, \.78\)/);
    expect(dataScreenCss).toMatch(/\.data-screen-panel::before[\s\S]*opacity:\s*\.95/);
  });

  it("keeps the right rail available when quant-analysis data is present", async () => {
    render(<DataScreenView load={vi.fn(async () => response)} loadQuantStrategy={vi.fn(async () => quantStrategy)} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "当前涨停股票" })).toBeInTheDocument());
    expect(screen.getByRole("region", { name: "当前跌停股票" })).toBeInTheDocument();
  });

  it("uses continuous scrolling rails for quant hits, late candidates, and limit-up previews", () => {
    expect(dataScreenCss).toContain("data-screen-loop-viewport");
    expect(dataScreenCss).toContain("data-screen-loop-track");
    expect(dataScreenCss).toContain("screen-vertical-marquee");
    expect(dataScreenCss).toContain("data-screen-opportunity-pair");
    expect(dataScreenCss).toMatch(/\.data-screen-opportunity-pair[\s\S]*grid-template-columns:\s*repeat\(2,/);
    expect(dataScreenCss).toMatch(/\.data-screen-loop-viewport[\s\S]*max-height:\s*calc\(5\s*\*/);
  });

  it("keeps information rails moving even when reduced-motion is enabled", () => {
    expect(dataScreenCss).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\.data-screen-flow-scroll-track\s*\{\s*animation:\s*screen-flow-marquee/);
    expect(dataScreenCss).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\.data-screen-loop-viewport\.is-looping \.data-screen-loop-track\s*\{\s*animation:\s*screen-vertical-marquee/);
    expect(dataScreenCss).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\.data-screen-limit-flow-rail\.is-looping \.data-screen-loop-track\s*\{\s*animation:\s*screen-limit-stock-marquee\s+var\(--data-screen-loop-duration/);
  });

  it("keeps every continuous information rail infinite after global motion safeguards", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-limit-flow-rail\.is-looping \.data-screen-loop-track\s*\{[\s\S]*animation-iteration-count:\s*infinite\s*!important/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-loop-viewport\.is-looping \.data-screen-loop-track\s*\{[\s\S]*animation-iteration-count:\s*infinite\s*!important/);
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-flow-track\s*\{[\s\S]*animation-iteration-count:\s*infinite\s*!important/);
  });

  it("keeps limit-up and limit-down feeds in one fixed two-column row", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-center-limit-board\s*\{[\s\S]*?display:\s*grid;[\s\S]*?grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
    expect(dataScreenCss).toMatch(/\.data-screen-limit-flow-rail\.is-looping \.data-screen-loop-track\s*\{[\s\S]*?animation:\s*screen-limit-stock-marquee\s+var\(--data-screen-loop-duration,\s*12s\)\s+linear\s+infinite/);
    expect(dataScreenCss).toContain("animation-timing-function: linear");
  });

  it("preserves per-row duration for limit feeds when reduced-motion is enabled", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-limit-flow-rail\.is-looping \.data-screen-loop-track\s*\{[\s\S]*?animation:\s*screen-limit-stock-marquee\s+var\(--data-screen-loop-duration/);
    expect(dataScreenCss).not.toMatch(/\.data-screen-c3 \.data-screen-limit-flow-rail\.is-looping \.data-screen-loop-track\s*\{[\s\S]*?animation:\s*screen-limit-stock-marquee\s+36s/);
  });

  it("uses a stable per-item scroll cadence instead of speeding up with long lists", () => {
    expect(dataScreenSource).toContain("cadenceSeconds = 4");
    expect(dataScreenSource).toContain("cadenceSeconds={1}");
    expect(dataScreenSource).not.toContain("items.length * 2.4");
  });

  it("starts continuous scrolling for compact three-item signal pools", async () => {
    const threeQuant = { ...quantStrategy, candidates: [quantStrategy.candidates[0], { ...quantStrategy.candidates[0], symbol: "000001", name: "平安银行" }, { ...quantStrategy.candidates[0], symbol: "000002", name: "万科A" }] };
    render(<DataScreenView load={vi.fn(async () => response)} loadQuantStrategy={vi.fn(async () => threeQuant)} />);
    const news = await screen.findByRole("region", { name: "实时资讯" });
    expect(within(news).getByRole("region", { name: "量化命中" }).querySelector(".data-screen-loop-viewport")).toHaveClass("is-looping");
  });

  it("gives quant-analysis hits a purple luminous treatment", () => {
    expect(dataScreenCss).toMatch(/\.data-screen-quant-hit-row[\s\S]*--quant-hit-color:\s*#c084fc/);
    expect(dataScreenCss).toMatch(/screen-quant-hit-flash[\s\S]*192,\s*132,\s*252/);
  });

  it("keeps a verified snapshot visible when a later refresh fails", async () => {
    const load = vi.fn().mockResolvedValueOnce(response).mockRejectedValueOnce(new Error("网络暂不可用"));
    render(<DataScreenView load={load} />);
    await waitFor(() => expect(screen.getByText("上证指数")).toBeInTheDocument());
    expect(screen.queryByText("网络暂不可用")).not.toBeInTheDocument();
  });

  it("detects only displayed sector rows whose content changed after the initial baseline", () => {
    const baseline = [
      { sector_id: "bank", name: "银行", leaderName: "平安银行", change_percent: "2.10", rising_count: 30, falling_count: 4, amount_yi: "180" },
      { sector_id: "chip", name: "芯片", leaderName: "中芯国际", change_percent: "1.20", rising_count: 24, falling_count: 8, amount_yi: "160" },
    ];
    const previous = new Map(baseline.map((sector) => [sector.sector_id, sectorHighlightSignature(sector)]));
    const next = [
      { ...baseline[0], change_percent: "2.35" },
      baseline[1],
      { sector_id: "new-energy", name: "新能源", leaderName: "宁德时代", change_percent: "3.01", rising_count: 21, falling_count: 3, amount_yi: "142" },
    ];

    expect(findChangedSectorIds(previous, next)).toEqual(["bank", "new-energy"]);
    expect(findChangedSectorIds(null, baseline)).toEqual([]);
  });

  it("keeps changed sector rows highlighted for ten seconds and then clears them", () => {
    expect(dataScreenSource).toContain("const SECTOR_HIGHLIGHT_DURATION_MS = 10_000;");
    expect(dataScreenSource).toContain("sectorHotIds.has(sector.sector_id)");
    expect(dataScreenCss).toMatch(/\.data-screen-c3 \.data-screen-sector-breadth-row\.is-updated[\s\S]*animation:\s*screen-sector-update-highlight\s+10s/);
  });

  it("uses the complete wide-screen height for the three data-screen columns", () => {
    expect(dataScreenCss).toMatch(/\/\* Full-screen vertical allocation contract:[\s\S]*?@media \(min-width: 1251px\) \{[\s\S]*?\.data-screen-page\.data-screen-c3\s*\{[\s\S]*?height:\s*100%;[\s\S]*?min-height:\s*100%;[\s\S]*?\.data-screen-c3 \.data-screen-grid\s*\{[\s\S]*?flex:\s*1 1 0;[\s\S]*?grid-template-columns:\s*minmax\(0, 28fr\) minmax\(0, 44fr\) minmax\(0, 28fr\);[\s\S]*?grid-template-rows:\s*minmax\(0, 1fr\);[\s\S]*?grid-template-areas:\s*"sectors indices news";[\s\S]*?\.data-screen-c3 \.data-screen-news-stack\s*\{[\s\S]*?grid-area:\s*news;[\s\S]*?grid-column:\s*auto;[\s\S]*?grid-row:\s*auto;/);
  });

  it("passes the full viewport height into the wide-screen dashboard", () => {
    expect(dataScreenViewportCss).toMatch(/@media \(min-width: 1251px\) \{[\s\S]*?\.app-shell-data-screen > \.data-screen-page\.data-screen-c3\s*\{[\s\S]*?height:\s*100%;[\s\S]*?min-height:\s*100%;/);
  });
});
