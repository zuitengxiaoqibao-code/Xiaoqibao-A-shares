import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MarketOverviewView } from "./MarketOverviewView";
import { writeMarketOverviewCache } from "./marketOverviewCache";
import type { MarketOverviewResponse } from "./types";
import type { BreakingNewsAlertResponse } from "../news-alerts/types";

const overview: MarketOverviewResponse = {
  status: "partial", as_of: "2026-07-29", observed_at: "2026-07-29T10:30:00+08:00",
  sentiment: { score: "76", band: "neutral", coverage_percent: "88", quality: "partial", observed_at: "2026-07-29T10:30:00+08:00" },
  breadth: { rising_count: 4439, falling_count: 699, flat_count: 10, valid_count: 5148 },
  limit_ecology: { limit_up_count: 78, limit_down_count: 6, broken_limit_up_count: 40, seal_rate_percent: "66.1" },
  liquidity: { total_amount_yi: "15862.96", baseline_amount_yi: "19444.39", relative_amount: "0.82" },
  market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-07-29T10:30:00+08:00", quote_count: 5191, universe_count: 5207 },
  field_evidence: [{
    field_path: "sentiment.score", value: "76", source: "market-sentiment-cache", source_field: "score",
    status: "live", trade_date: "2026-07-29", observed_at: "2026-07-29T10:30:00+08:00",
    coverage_percent: "88", derived: true, formula: "a-share-sentiment-v2",
    evidence_ids: ["sentiment-1"], limitations: [],
  }],
  indices: [
    { instrument: "sh000001", name: "上证指数", value: "3823.73", change: "9.53", change_percent: "0.25", observed_at: "2026-07-29T10:30:00+08:00", source: "腾讯行情", quality: "ready" },
  ],
  minute_series: [
    { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "100", amount: "1000" },
    { observed_at: "2026-07-29T10:00:00+08:00", price: "3812", volume: "110", amount: "1150" },
    { observed_at: "2026-07-29T10:30:00+08:00", price: "3823.73", volume: "120", amount: "1300" },
  ],
  anomalies: [
    { anomaly_id: "a1", occurred_at: "2026-07-29T10:00:00+08:00", label: "光电共封装 CPO", headline: "板块快速拉升", direction: "positive", themes: ["光电共封装 CPO"], symbols: ["603629"] },
  ],
  live_feed: [
    { event_id: "n1", occurred_at: "2026-07-29T10:02:00+08:00", headline: "算力方向活跃", summary: "公开新闻摘要", themes: ["算力"], symbols: ["603629"], source: "公开资讯", review_state: "machine_reviewed" },
    { event_id: "n2", occurred_at: "2026-07-29T10:01:00+08:00", headline: "海外商品期货波动", summary: "未关联 A 股", themes: ["商品"], symbols: [], source: "公开资讯", review_state: "machine_reviewed" },
  ],
  sectors: [
    { sector_id: "s1", name: "脑科学", change_percent: "4.24", amount_yi: "9.52", limit_up_count: 7, rising_count: 70, falling_count: 8, stock_count: 78 },
    { sector_id: "s2", name: "旅游", change_percent: "3.66", amount_yi: "7.57", limit_up_count: 6, rising_count: 69, falling_count: 2, stock_count: 71 },
  ],
  sector_stocks: {
    s1: [{ symbol: "603629", name: "利通电子", change_percent: "10.05", amount_yi: "7.63", market_cap_yi: "106.02", first_limit_time: "09:46:48", position: "首板", quality: "ready" }],
    s2: [{ symbol: "600258", name: "首旅酒店", change_percent: "6.01", amount_yi: "5.13", market_cap_yi: "88.20", first_limit_time: null, position: "题材成员", quality: "ready" }],
  },
  market_stocks: [
    { symbol: "603629", name: "利通电子", price: "11", previous_close: "10", open: "10.3", high: "11", low: "10.2", volume: "1000", amount_yi: "7.63", change_percent: "10", state: "limit_up", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
    { symbol: "600258", name: "首旅酒店", price: "10.5", previous_close: "10", open: "10.1", high: "11", low: "10", volume: "900", amount_yi: "5.13", change_percent: "5", state: "broken_limit_up", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
  ],
  warnings: ["部分字段来自缓存"], sources: ["腾讯行情", "本地新闻库"],
};

const alertResponse: BreakingNewsAlertResponse = {
  status: "ready",
  observed_at: "2026-07-29T10:30:00+08:00",
  alerts: [{
    event_id: "breaking-overview",
    headline: "已核验市场重要事件",
    occurred_at: "2026-07-29T10:12:00+08:00",
    verification_state: "multi_source_confirmed",
    urgency: "breaking",
    association_kind: "theme",
    association_reasons: ["theme_keyword:算力"],
    affected_symbols: ["603629"],
    themes: ["算力"],
    publishers: ["来源甲", "来源乙"],
    source_urls: ["https://news.example/a", "https://news.example/b"],
    source_count: 2,
    impact_direction: "uncertain",
    impact_confidence: null,
    ai_degraded: true,
  }],
  sources: ["来源甲", "来源乙"],
  warnings: [],
};

describe("MarketOverviewView", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    localStorage.clear();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  });
  afterEach(() => vi.useRealTimers());

  it("animates every percent without exceeding the verified startup milestone", async () => {
    let resolveOverview: ((value: MarketOverviewResponse) => void) | undefined;
    const load = vi.fn(() => new Promise<MarketOverviewResponse>((resolve) => {
      resolveOverview = resolve;
    }));

    render(<MarketOverviewView load={load} />);

    const progress = screen.getByRole("progressbar", { name: "首页数据加载进度" });
    expect(progress).toHaveAttribute("aria-valuenow", "1");
    expect(progress).toHaveAttribute("data-verified-target", "48");
    expect(screen.getByTestId("startup-radar")).toBeInTheDocument();
    expect(screen.getByTestId("startup-radar-sweep")).toBeInTheDocument();
    expect(screen.queryByTestId("startup-orbit-slice")).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("读取本地 A 股全市场快照");
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("本地 API 已就绪");

    await act(async () => vi.advanceTimersByTime(200));
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeGreaterThan(1);
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeLessThan(48);

    await act(async () => vi.advanceTimersByTime(1000));
    expect(progress).toHaveAttribute("aria-valuenow", "48");
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("已持续 1 秒");

    await act(async () => resolveOverview?.(overview));
    expect(progress).toHaveAttribute("data-verified-target", "100");
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeGreaterThanOrEqual(48);
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeLessThan(100);
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("5,191 条行情");

    await act(async () => vi.advanceTimersByTime(120));
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeGreaterThan(48);
    expect(Number(progress.getAttribute("aria-valuenow"))).toBeLessThan(100);

    await act(async () => vi.advanceTimersByTime(1200));
    expect(progress).toHaveAttribute("aria-valuenow", "100");
    await act(async () => vi.advanceTimersByTime(300));
    expect(screen.queryByRole("dialog", { name: "正在加载信息总览" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
  });

  it("does not claim 100 percent when the critical overview request fails", async () => {
    render(<MarketOverviewView load={() => Promise.reject(new Error("本地行情缓存损坏"))} />);

    const dialog = await screen.findByRole("dialog", { name: "信息总览实时更新失败" });
    await act(async () => vi.advanceTimersByTime(1000));
    expect(screen.getByRole("progressbar", { name: "首页数据加载进度" })).toHaveAttribute("aria-valuenow", "48");
    expect(dialog).toHaveTextContent("本地行情缓存损坏");
    expect(screen.getByRole("button", { name: "重试首页数据" })).toBeInTheDocument();
  });

  it("keeps visible motion in the radar loader and progress rail while data is pending", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");

    expect(css).toContain("@keyframes homepage-radar-sweep");
    expect(css).toContain("@keyframes homepage-progress-tracer");
    expect(css).not.toContain("homepage-startup-orbit");
  });

  it("keeps evidence-chain labels and rows readable on high-resolution displays", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");

    expect(css).toMatch(/\.evidence-column small \{[^}]*font-size: 12px;/);
    expect(css).toMatch(/\.evidence-column span \{[^}]*font-size: 12px;/);
  });

  it("renders the five information layers and explicit partial state", async () => {
    render(<MarketOverviewView load={() => Promise.resolve(overview)} />);

    expect(await screen.findByRole("heading", { name: "信息总览" })).toBeInTheDocument();
    await screen.findByText("本地通达信实时");
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("中性");
    expect(screen.getByRole("region", { name: "关键指标" })).toHaveTextContent("封板率");
    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项实时");
    expect(screen.getByRole("navigation", { name: "市场功能筛选" })).toHaveTextContent("盘中异动");
    expect(screen.getByRole("region", { name: "上证指数分时与异动" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "分时事件脉冲轨道" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "当前异动摘要" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "异动记录" })).toHaveTextContent("01");
    expect(screen.getByRole("region", { name: "A 股关联资讯" })).toHaveTextContent("算力方向活跃");
    expect(screen.getByRole("region", { name: "A 股关联资讯" })).not.toHaveTextContent("海外商品期货波动");
    expect(screen.getByRole("region", { name: "热门板块与成分股" })).toHaveTextContent("脑科学");
    expect(screen.getByRole("status")).toHaveTextContent("部分数据可用");
  });

  it("groups collapsed evidence summaries into one compact responsive row", async () => {
    const overviewWithEvidenceLedger: MarketOverviewResponse = {
      ...overview,
      review: {
        as_of: "2026-07-29",
        observed_at: "2026-07-29T10:30:00+08:00",
        latest_trade_date: "2026-07-29",
        source: "tdx-local-history",
        quality: "partial",
        universe_count: 5198,
        history_ready_count: 5123,
        watermark: {
          dominant_trade_date: "2026-07-29",
          latest_available_trade_date: "2026-07-29",
          universe_count: 5198,
          history_ready_count: 5123,
          coverage_percent: "98.56",
          fragmented_latest_count: 0,
          missing_history_count: 75,
          quality: "partial",
          blockers: ["history_coverage_low"],
        },
        evidence_ledger: [{
          source: "tdx-local-rpc",
          operation: "market-overview",
          status: "ready",
          trade_date: "2026-07-29",
          observed_at: "2026-07-29T10:30:00+08:00",
          formula_version: null,
          sample_count: 5191,
          limitations: [],
        }],
        consecutive_limit_up: [],
        first_limit_up: [],
        new_high_100: [],
        previous_limit_up: [],
        volume_breakouts: [],
        previous_high_breakouts: [],
        low_position_volume: [],
        dragon_tiger: [],
        warnings: ["history_coverage_low"],
        formula_version: "market-review-v1",
      },
    };

    render(<MarketOverviewView load={() => Promise.resolve(overviewWithEvidenceLedger)} />);

    const summaryRow = await screen.findByRole("group", { name: "数据真实性与证据摘要" });
    expect(summaryRow).toHaveClass("overview-evidence-summary-row");
    expect(summaryRow).toContainElement(screen.getByRole("group", { name: "关键字段证据" }));
    expect(summaryRow).toContainElement(screen.getByRole("region", { name: "证据账本" }));
  });

  it("synchronizes the selected summary and numbered anomaly record without a top event rail", async () => {
    const twoEvents = {
      ...overview,
      minute_series: [
        ...overview.minute_series,
        { observed_at: "2026-07-29T10:31:00+08:00", price: "3825", volume: "130", amount: "1400" },
      ],
      anomalies: [
        ...overview.anomalies,
        { anomaly_id: "a2", occurred_at: "2026-07-29T10:31:00+08:00", label: "医药生物", headline: "创新药方向出现已核验异动", direction: "negative" as const, themes: ["创新药"], symbols: ["600000"] },
      ],
    } satisfies MarketOverviewResponse;

    render(<MarketOverviewView load={() => Promise.resolve(twoEvents)} />);

    const anomalyPanel = await screen.findByRole("region", { name: "异动记录" });
    fireEvent.click(within(anomalyPanel).getByRole("button", { name: /10:31 .*医药生物/ }));

    expect(screen.getByRole("region", { name: "当前异动摘要" })).toHaveTextContent("创新药方向出现已核验异动");
    expect(screen.getByRole("region", { name: "异动记录" }).querySelector('button[aria-pressed="true"]')).toHaveTextContent("02");
    expect(screen.queryByRole("navigation", { name: "分时事件脉冲轨道" })).not.toBeInTheDocument();
  });

  it("keeps same-day anomaly events stable across price refreshes and only appends unseen event ids", async () => {
    const changedExisting = {
      ...overview,
      observed_at: "2026-07-29T10:35:00+08:00",
      minute_series: [
        ...overview.minute_series,
        { observed_at: "2026-07-29T10:35:00+08:00", price: "3830", volume: "150", amount: "1600" },
      ],
      anomalies: [
        { ...overview.anomalies[0], label: "不应替换的刷新文字", headline: "不应覆盖原始异动摘要" },
        { anomaly_id: "a2", occurred_at: "2026-07-29T10:35:00+08:00", label: "机器人", headline: "机器人新增异动", direction: "positive" as const, themes: ["机器人"], symbols: ["603629"] },
      ],
    } satisfies MarketOverviewResponse;
    const load = vi.fn<() => Promise<MarketOverviewResponse>>()
      .mockResolvedValueOnce(overview)
      .mockResolvedValueOnce(changedExisting);

    render(<MarketOverviewView load={load} />);
    const anomalyPanel = await screen.findByRole("region", { name: "异动记录" });
    expect(anomalyPanel).toHaveTextContent("光电共封装 CPO");
    expect(anomalyPanel).toHaveTextContent("01");

    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("region", { name: "异动记录" })).toHaveTextContent("机器人新增异动"));

    const refreshedPanel = screen.getByRole("region", { name: "异动记录" });
    expect(refreshedPanel).toHaveTextContent("光电共封装 CPO");
    expect(refreshedPanel).not.toHaveTextContent("不应替换的刷新文字");
    expect(refreshedPanel).not.toHaveTextContent("不应覆盖原始异动摘要");
    expect(within(refreshedPanel).getByRole("button", { name: /10:00 .*光电共封装 CPO/ })).toHaveTextContent("01");
    expect(within(refreshedPanel).getByRole("button", { name: /10:35 .*机器人/ })).toHaveTextContent("02");
  });

  it("resets the anomaly snapshot when the confirmed trading date changes", async () => {
    const nextDay = {
      ...overview,
      as_of: "2026-07-30",
      observed_at: "2026-07-30T09:31:00+08:00",
      minute_series: [{ observed_at: "2026-07-30T09:31:00+08:00", price: "3840", volume: "10", amount: "100" }],
      anomalies: [{ anomaly_id: "b1", occurred_at: "2026-07-30T09:31:00+08:00", label: "次日事件", headline: "新交易日异动", direction: "neutral" as const, themes: [], symbols: ["603629"] }],
    } satisfies MarketOverviewResponse;
    const load = vi.fn<() => Promise<MarketOverviewResponse>>()
      .mockResolvedValueOnce(overview)
      .mockResolvedValueOnce(nextDay);

    render(<MarketOverviewView load={load} />);
    await waitFor(() => expect(screen.getByRole("region", { name: "异动记录" })).toHaveTextContent("光电共封装 CPO"));
    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(screen.getByRole("region", { name: "异动记录" })).toHaveTextContent("次日事件"));

    const anomalyPanel = screen.getByRole("region", { name: "异动记录" });
    expect(anomalyPanel).not.toHaveTextContent("光电共封装 CPO");
    expect(anomalyPanel).toHaveTextContent("新交易日异动");
  });

  it("opens the regime workspace for an intraday snapshot without verified anomalies", async () => {
    localStorage.clear();
    const calmIntraday = {
      ...overview,
      anomalies: [],
      market_data: { ...overview.market_data, phase: "intraday" as const, freshness: "live" as const },
      regime_metrics: {
        up_ratio: "52", zt_ratio: "1.2", dt_ratio: "0.2", median_ret: "0.3", amt_heat: "1.05",
        strong_close_ratio: "48", weak_close_ratio: "24", limit_fail_ratio: "18", panic_ratio: "1.1",
        amp_ratio: "6.2", net_positive_ratio: "53", large_amount_strong_close_ratio: "58",
        factor_coverage_percent: "100",
      },
      regime: {
        regime: "轮动震荡" as const,
        emotion_score: "58", risk_score: "35", heat_score: "54", rotation_score: "66",
        coverage_percent: "100", market_coef: "0.5", suitable_strategies: ["0轴低吸"],
        avoid_strategies: ["追高"], reasons: ["市场涨跌均衡"], missing_factors: [],
        rule_matched: true, quality: "ready" as const, formula_version: "regime-v2",
      },
    } satisfies MarketOverviewResponse;

    render(<MarketOverviewView load={() => Promise.resolve(calmIntraday)} />);

    expect(await screen.findByRole("region", { name: "A 股市场风格识别工作台" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "情绪周期" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens the review statistics workspace for a final post-close snapshot", async () => {
    localStorage.clear();
    const finalSnapshot = {
      ...overview,
      market_data: { ...overview.market_data, phase: "postclose" as const, freshness: "final" as const },
    } satisfies MarketOverviewResponse;

    render(<MarketOverviewView load={() => Promise.resolve(finalSnapshot)} />);

    expect(await screen.findByRole("region", { name: "复盘统计大全专属工作区" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复盘统计大全" })).toHaveAttribute("aria-pressed", "true");
  });

  it("does not replace the user's selected workspace during a background refresh", async () => {
    localStorage.clear();
    const calmIntraday = {
      ...overview,
      anomalies: [],
      market_data: { ...overview.market_data, phase: "intraday" as const, freshness: "live" as const },
    } satisfies MarketOverviewResponse;
    const load = vi.fn<() => Promise<MarketOverviewResponse>>()
      .mockResolvedValueOnce(calmIntraday)
      .mockResolvedValueOnce({ ...calmIntraday, anomalies: overview.anomalies });

    render(<MarketOverviewView load={load} />);
    await screen.findByRole("region", { name: "情绪周期专属工作区" });
    fireEvent.click(screen.getByRole("button", { name: "炸板" }));
    expect(screen.getByRole("region", { name: "炸板专属工作区" })).toBeInTheDocument();

    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));

    expect(screen.getByRole("button", { name: "炸板" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("region", { name: "炸板专属工作区" })).toBeInTheDocument();
  });

  it("restores the last explicitly selected workspace after leaving and returning", async () => {
    const calmIntraday = {
      ...overview,
      anomalies: [],
      market_data: { ...overview.market_data, phase: "intraday" as const, freshness: "live" as const },
    } satisfies MarketOverviewResponse;
    localStorage.setItem("qibao-market-overview-feature", "炸板");
    render(<MarketOverviewView load={() => Promise.resolve(calmIntraday)} />);

    expect(await screen.findByRole("region", { name: "炸板专属工作区" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "炸板" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "板块涨停" }));
    expect(localStorage.getItem("qibao-market-overview-feature")).toBe("板块涨停");
  });

  it("shows the same-day cache immediately while the newest snapshot is still loading", async () => {
    const cached = { ...overview, observed_at: new Date().toISOString(), as_of: "2026-08-06" };
    writeMarketOverviewCache(cached);
    let resolveLatest: ((value: MarketOverviewResponse) => void) | undefined;
    render(<MarketOverviewView load={() => new Promise<MarketOverviewResponse>((resolve) => { resolveLatest = resolve; })} />);

    await waitFor(() => expect(screen.getAllByText("正在更新最新数据").length).toBeGreaterThan(0));
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
    expect(screen.getAllByText(/缓存/).length).toBeGreaterThan(0);
    expect(screen.getByRole("progressbar", { name: "首页数据加载进度" })).toHaveAttribute("data-verified-target", "48");
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("缓存已展示，正在更新最新数据");
    await act(async () => resolveLatest?.(overview));
    localStorage.clear();
  });

  it("marks the live snapshot as monitored after the refresh completes", async () => {
    render(<MarketOverviewView load={() => Promise.resolve({ ...overview, status: "ready" })} />);

    expect(await screen.findByText("已加载最新数据 · 实时监控中")).toBeInTheDocument();
  });

  it("does not call a previous-close snapshot real-time before the session opens", async () => {
    localStorage.clear();
    const previousClose = {
      ...overview,
      market_data: {
        ...overview.market_data,
        phase: "premarket" as const,
        freshness: "previous_close" as const,
      },
    };

    render(<MarketOverviewView load={() => Promise.resolve(previousClose)} />);

    expect(await screen.findByText("已加载上一交易日快照 · 等待开盘")).toBeInTheDocument();
    expect(screen.queryByText("已加载最新数据 · 实时监控中")).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "首页数据加载进度" })).toHaveAttribute("data-verified-target", "100");
    localStorage.clear();
  });

  it("keeps cached data visible and explains a failed live refresh", async () => {
    const cached = { ...overview, observed_at: new Date().toISOString(), as_of: "2026-08-06" };
    writeMarketOverviewCache(cached);
    render(<MarketOverviewView load={() => Promise.reject(new Error("本地行情源超时"))} />);

    expect(await screen.findByRole("dialog", { name: "信息总览实时更新失败" })).toHaveTextContent("实时更新失败，继续使用缓存");
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
    fireEvent.click(screen.getByRole("button", { name: "继续使用缓存" }));
    expect(screen.queryByRole("dialog", { name: "信息总览实时更新失败" })).not.toBeInTheDocument();
    localStorage.clear();
  });

  it("does not mark an unavailable snapshot as a complete startup", async () => {
    const unavailable = { ...overview, status: "unavailable" as const, market_data: { ...overview.market_data, quality: "unavailable" as const } };
    render(<MarketOverviewView load={() => Promise.resolve(unavailable)} />);

    const progress = await screen.findByRole("progressbar", { name: "首页数据加载进度" });
    expect(progress).toHaveAttribute("data-verified-target", "48");
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("数据证据不足");
  });

  it("loads the newest six market-wide verified alerts", async () => {
    const loadAlerts = vi.fn().mockResolvedValue(alertResponse);

    render(<MarketOverviewView load={() => Promise.resolve(overview)} loadAlerts={loadAlerts} />);

    expect(await screen.findByRole("region", { name: "突发事件" })).toHaveTextContent("已核验市场重要事件");
    expect(loadAlerts).toHaveBeenCalledWith(undefined, expect.any(AbortSignal), 6);
  });

  it("uses the shared dark terminal shell without losing overview regions", async () => {
    render(<MarketOverviewView load={() => Promise.resolve(overview)} />);

    expect(await screen.findByRole("heading", { name: "信息总览" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("terminal-page", "market-overview-page");
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "A 股关联资讯" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "热门板块与成分股" })).toBeInTheDocument();
  });

  it("does not keep an independent light overview palette", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");

    expect(css).toContain("--overview-bg: var(--surface-canvas)");
    expect(css).not.toMatch(/background:\s*#fff(?:fff)?\b/i);
    expect(css).not.toMatch(/--overview-(?:bg|panel):\s*#f[0-9a-f]{5}\b/i);
  });

  it("keeps paired workspace panels equal-height without imposing a fixed minimum", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");
    const rule = (selector: string) => {
      const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
    };

    expect(rule(".distinct-block-grid")).toContain("align-items: stretch");
    expect(rule(".distinct-block")).toContain("height: 100%");
    expect(rule(".distinct-block")).not.toMatch(/min-height\s*:/);
    expect(rule(".distinct-block.size-tall")).not.toMatch(/min-height\s*:/);
    expect(rule(".distinct-block-body")).not.toMatch(/min-height\s*:/);
    expect(rule(".distinct-empty")).toContain("min-height: 112px");
    expect(rule(".layout-hot-news-stream .theme-atlas")).toContain("max-height: 480px");
    expect(rule(".layout-hot-news-stream .theme-atlas")).toContain("overflow: auto");
  });

  it("filters visible content and links anomaly and sector selections", async () => {
    const onOpenAShare = vi.fn();
    render(<MarketOverviewView load={() => Promise.resolve(overview)} onOpenAShare={onOpenAShare} />);
    await screen.findByRole("button", { name: /脑科学.*4.24%/ });

    const anomalyPanel = screen.getByRole("region", { name: "异动记录" });
    fireEvent.click(within(anomalyPanel).getByRole("button", { name: /10:00.*光电共封装 CPO/ }));
    expect(within(anomalyPanel).getByRole("button", { name: /10:00.*光电共封装 CPO/ })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: /旅游.*3.66%/ }));
    const stockTable = screen.getByRole("table", { name: "旅游成分股" });
    expect(within(stockTable).getByText("首旅酒店")).toBeInTheDocument();
    fireEvent.click(within(stockTable).getByRole("button", { name: "查看 600258 首旅酒店" }));
    expect(onOpenAShare).toHaveBeenCalledWith("600258");
  });

  it("activates overview sector and stock rows from any cell or the keyboard", async () => {
    const onOpenAShare = vi.fn();
    render(<MarketOverviewView load={() => Promise.resolve(overview)} onOpenAShare={onOpenAShare} />);

    const sectorTable = await screen.findByRole("table", { name: "热门板块" });
    const tourismRow = within(sectorTable).getByRole("link", { name: "查看旅游板块" });
    fireEvent.click(within(tourismRow).getByText("7.57亿"));

    const stockTable = screen.getByRole("table", { name: "旅游成分股" });
    const hotelRow = within(stockTable).getByRole("link", { name: "查看 600258 首旅酒店" });
    expect(hotelRow).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(hotelRow, { key: " " });

    expect(onOpenAShare).toHaveBeenCalledWith("600258");
  });

  it("opens an independent workspace instead of only highlighting a menu", async () => {
    render(<MarketOverviewView load={() => Promise.resolve(overview)} />);
    await screen.findByText("本地通达信实时");

    fireEvent.click(screen.getByRole("button", { name: "炸板" }));

    expect(screen.getByRole("region", { name: "炸板专属工作区" })).toHaveAttribute("data-layout", "failure-lab");
    expect(screen.getByRole("region", { name: "炸板风险台" })).toHaveTextContent("首旅酒店");
    expect(screen.getByRole("region", { name: "炸板专属工作区" })).not.toHaveTextContent("核心排行");
  });

  it("keeps each workspace content attached to its label after menu reordering", async () => {
    render(<MarketOverviewView load={() => Promise.resolve(overview)} />);
    await screen.findByText("本地通达信实时");

    fireEvent.click(screen.getByRole("button", { name: "首板梯队" }));
    expect(screen.getByRole("region", { name: "首板梯队专属工作区" })).toHaveAttribute("data-layout", "review-first-board");
    expect(screen.getByRole("region", { name: "首板梯队完整清单" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "热点解读" }));
    expect(screen.getByRole("region", { name: "热点解读专属工作区" })).toHaveAttribute("data-layout", "news-theme-market");
    expect(screen.getByRole("region", { name: "热点证据链" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "首板梯队专属工作区" })).not.toBeInTheDocument();
  });

  it("opens a real audio announcer for the voice broadcast menu", async () => {
    const synthesizeSpeech = vi.fn().mockResolvedValue(
      new Blob(["audio"], { type: "audio/mpeg" }),
    );
    const play = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("Audio", vi.fn(() => ({ play, pause: vi.fn(), onended: null, onerror: null })));
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:voice"), revokeObjectURL: vi.fn() });
    const view = render(<MarketOverviewView
      load={() => Promise.resolve(overview)}
      synthesizeSpeech={synthesizeSpeech}
    />);
    await screen.findByText("本地通达信实时");

    fireEvent.click(screen.getByRole("button", { name: "异动语音播报" }));

    expect(await screen.findByRole("region", { name: "异动语音播报" })).toHaveTextContent("真实语音");
    await waitFor(() => expect(synthesizeSpeech).toHaveBeenCalledTimes(1));
    expect(play).toHaveBeenCalledTimes(1);
    view.unmount();
    vi.unstubAllGlobals();
  });

  it("shows local TDX coverage and opens a searched A-share", async () => {
    const onOpenAShare = vi.fn();
    render(<MarketOverviewView load={() => Promise.resolve(overview)} onOpenAShare={onOpenAShare} />);

    expect(await screen.findByText("本地通达信实时")).toBeInTheDocument();
    expect(screen.getByText("5,191 / 5,207")).toBeInTheDocument();
    const search = screen.getByRole("searchbox", { name: "搜索股票代码" });
    fireEvent.change(search, { target: { value: "600519" } });
    fireEvent.keyDown(search, { key: "Enter" });

    expect(onOpenAShare).toHaveBeenCalledWith("600519");
    expect(screen.queryByText("A-SHARE MARKET TERMINAL")).not.toBeInTheDocument();
  });

  it("polls every five seconds, supports manual refresh and pauses while hidden", async () => {
    const load = vi.fn(() => Promise.resolve(overview));
    render(<MarketOverviewView load={load} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));

    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "立即刷新" }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(3));

    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    fireEvent(document, new Event("visibilitychange"));
    await act(async () => vi.advanceTimersByTime(10000));
    expect(load).toHaveBeenCalledTimes(3);
  });

  it("keeps the completed startup overlay hidden during a five-second background refresh", async () => {
    localStorage.clear();
    let resolveInitial: ((value: MarketOverviewResponse) => void) | undefined;
    let resolveRefresh: ((value: MarketOverviewResponse) => void) | undefined;
    const load = vi
      .fn<() => Promise<MarketOverviewResponse>>()
      .mockImplementationOnce(() => new Promise<MarketOverviewResponse>((resolve) => {
        resolveInitial = resolve;
      }))
      .mockImplementationOnce(() => new Promise<MarketOverviewResponse>((resolve) => {
        resolveRefresh = resolve;
      }));

    render(<MarketOverviewView load={load} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));
    await act(async () => vi.advanceTimersByTime(1000));
    await act(async () => resolveInitial?.({ ...overview, status: "ready" }));
    await act(async () => vi.advanceTimersByTime(1200));
    await act(async () => vi.advanceTimersByTime(300));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "正在加载信息总览" })).not.toBeInTheDocument());
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");

    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("dialog", { name: "正在加载信息总览" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");

    await act(async () => resolveRefresh?.({ ...overview, status: "ready", sentiment: { ...overview.sentiment, score: "78" } }));
    await waitFor(() => expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("78"));
    localStorage.clear();
  });

  it("does not start another refresh while the current request is pending", async () => {
    let resolveFirst: ((value: MarketOverviewResponse) => void) | undefined;
    const load = vi.fn(() => new Promise<MarketOverviewResponse>((resolve) => {
      resolveFirst = resolve;
    }));

    render(<MarketOverviewView load={load} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));

    await act(async () => vi.advanceTimersByTime(15000));
    expect(load).toHaveBeenCalledTimes(1);

    await act(async () => resolveFirst?.(overview));
    await act(async () => vi.advanceTimersByTime(5000));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });
});
