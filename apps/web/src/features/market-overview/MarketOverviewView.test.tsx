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
  indices: [
    { instrument: "sh000001", name: "上证指数", value: "3823.73", change: "9.53", change_percent: "0.25", observed_at: "2026-07-29T10:30:00+08:00", source: "腾讯行情", quality: "ready" },
  ],
  minute_series: [
    { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "100", amount: "1000" },
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
    expect(screen.getByRole("navigation", { name: "市场功能筛选" })).toHaveTextContent("盘中异动");
    expect(screen.getByRole("region", { name: "上证指数分时与异动" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "A 股关联资讯" })).toHaveTextContent("算力方向活跃");
    expect(screen.getByRole("region", { name: "A 股关联资讯" })).not.toHaveTextContent("海外商品期货波动");
    expect(screen.getByRole("region", { name: "热门板块与成分股" })).toHaveTextContent("脑科学");
    expect(screen.getByRole("status")).toHaveTextContent("部分数据可用");
  });

  it("shows the same-day cache immediately while the newest snapshot is still loading", async () => {
    const cached = { ...overview, observed_at: new Date().toISOString(), as_of: "2026-08-06" };
    writeMarketOverviewCache(cached);
    let resolveLatest: ((value: MarketOverviewResponse) => void) | undefined;
    render(<MarketOverviewView load={() => new Promise<MarketOverviewResponse>((resolve) => { resolveLatest = resolve; })} />);

    await waitFor(() => expect(screen.getAllByText("正在更新实时数据").length).toBeGreaterThan(0));
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
    expect(screen.getAllByText(/缓存/).length).toBeGreaterThan(0);
    expect(screen.getByRole("progressbar", { name: "首页数据加载进度" })).toHaveAttribute("data-verified-target", "48");
    expect(screen.getByRole("dialog", { name: "正在加载信息总览" })).toHaveTextContent("缓存已展示，正在更新实时数据");
    await act(async () => resolveLatest?.(overview));
    localStorage.clear();
  });

  it("marks the live snapshot as monitored after the refresh completes", async () => {
    render(<MarketOverviewView load={() => Promise.resolve({ ...overview, status: "ready" })} />);

    expect(await screen.findByText("已加载最新数据 · 实时监控中")).toBeInTheDocument();
  });

  it("keeps cached data visible and explains a failed live refresh", async () => {
    const cached = { ...overview, observed_at: new Date().toISOString(), as_of: "2026-08-06" };
    writeMarketOverviewCache(cached);
    render(<MarketOverviewView load={() => Promise.reject(new Error("本地行情源超时"))} />);

    expect(await screen.findByRole("dialog", { name: "信息总览实时更新失败" })).toHaveTextContent("实时更新失败，继续使用缓存");
    expect(screen.getByRole("region", { name: "A 股市场情绪与核心指数" })).toHaveTextContent("76");
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

  it("keeps ordinary workspace content content-sized instead of creating blank panels", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");
    const rule = (selector: string) => {
      const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
    };

    expect(rule(".distinct-block-grid")).toContain("align-items: start");
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

    fireEvent.click(screen.getByRole("button", { name: /10:00.*光电共封装 CPO/ }));
    expect(screen.getByRole("button", { name: /10:00.*光电共封装 CPO/ })).toHaveAttribute("aria-pressed", "true");
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
