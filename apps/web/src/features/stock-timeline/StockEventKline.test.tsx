import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StockEventKline, stockTimelineOption } from "./StockEventKline";
import type { StockTimelineResponse } from "./types";


const setOption = vi.fn();
vi.mock("echarts", () => ({
  init: vi.fn(() => ({ setOption, resize: vi.fn(), dispose: vi.fn() })),
}));

const alertMeta = {
  association_kind: "direct" as const,
  association_reasons: ["security_code:600519"],
  verification_state: "multi_source_confirmed" as const,
  source_count: 2,
  urgency: "breaking" as const,
  category: "industry_sector" as const,
  strength: "medium" as const,
  credibility: "multi_source_verified" as const,
  duration: "unknown" as const,
  price_reflection: "unknown" as const,
  follow_up_indicators: ["观察板块成交额、涨停扩散和龙头持续性"],
};


function timeline(): StockTimelineResponse {
  return {
    symbol: "600519",
    as_of: "2026-07-28",
    cutoff: "2026-07-28T15:30:00+08:00",
    status: "ready",
    bars: [
      { symbol: "600519", trade_date: "2026-07-24", open: "1400", high: "1420", low: "1390", close: "1410", volume: 100, amount: "141000", source: "local-daily-bars" },
      { symbol: "600519", trade_date: "2026-07-27", open: "1410", high: "1430", low: "1380", close: "1390", volume: 120, amount: "168000", source: "local-daily-bars" },
      { symbol: "600519", trade_date: "2026-07-28", open: "1390", high: "1450", low: "1385", close: "1430", volume: 160, amount: "227000", source: "local-daily-bars" },
    ],
    events: [
      { ...alertMeta, event_id: "positive", event_type: "market_news", occurred_at: "2026-07-24T10:01:00+08:00", mapped_trade_date: "2026-07-24", label: "白酒消费", headline: "消费政策迎来边际变化", direction: "positive", confidence: "0.82", themes: ["白酒"], industries: ["食品饮料"], publisher: "证券时报", source_url: "https://news.example/positive", association_confidence: "0.95", review_state: "verified" },
      { ...alertMeta, urgency: "tracking", event_id: "negative", event_type: "market_news", occurred_at: "2026-07-27T09:20:00+08:00", mapped_trade_date: "2026-07-27", label: "业绩压力", headline: "公司披露阶段性经营压力", direction: "negative", confidence: "0.75", themes: ["业绩"], industries: ["食品饮料"], publisher: "上交所", source_url: "https://news.example/negative", association_confidence: "1", review_state: "verified" },
      { ...alertMeta, event_id: "uncertain", event_type: "market_news", occurred_at: "2026-07-28T12:10:00+08:00", mapped_trade_date: "2026-07-28", label: "渠道调研", headline: "机构发布渠道调研纪要", direction: "uncertain", confidence: null, themes: ["渠道"], industries: ["食品饮料"], publisher: "公开资讯", source_url: "https://news.example/uncertain", association_confidence: "0.9", review_state: "verified" },
      { ...alertMeta, urgency: "tracking", verification_state: "verified", source_count: 1, event_id: "weekend", event_type: "market_news", occurred_at: "2026-07-25T08:30:00+08:00", mapped_trade_date: null, label: "周末事件", headline: "周末公开新闻", direction: "neutral", confidence: "0.61", themes: [], industries: ["食品饮料"], publisher: "公开资讯", source_url: "https://news.example/weekend", association_confidence: "0.9", review_state: "verified" },
    ],
    sources: ["local-daily-bars", "verified-market-news"],
    warnings: ["event_without_matching_trade_date:weekend"],
  };
}

function denseTimeline(): StockTimelineResponse {
  const bars = Array.from({ length: 30 }, (_, index) => ({
    symbol: "600519",
    trade_date: `2026-06-${String(index + 1).padStart(2, "0")}`,
    open: "1400",
    high: "1420",
    low: "1390",
    close: "1410",
    volume: 100,
    amount: "141000",
    source: "local-daily-bars",
  }));
  return {
    ...timeline(),
    bars,
    events: bars.map((bar, index) => ({
      ...alertMeta,
      event_id: `dense-${index}`,
      event_type: "market_news" as const,
      occurred_at: `${bar.trade_date}T10:00:00+08:00`,
      mapped_trade_date: bar.trade_date,
      label: `高密度事件标签${index}`,
      headline: `第 ${index + 1} 条已核验新闻`,
      direction: index % 2 ? "negative" as const : "positive" as const,
      confidence: "0.8",
      themes: ["测试题材"],
      industries: ["测试行业"],
      publisher: "测试来源",
      source_url: `https://news.example/dense-${index}`,
      association_confidence: "0.95",
      review_state: "verified" as const,
    })),
  };
}


describe("stockTimelineOption", () => {
  it("renders event headlines centered on vertical dashed lines without changing red-green candlesticks", () => {
    const option = stockTimelineOption(timeline(), "negative");
    const candle = (option.series as Array<Record<string, unknown>>)[0];
    expect(candle.itemStyle).toMatchObject({ color: "#f04f5f", color0: "#2fcf91" });
    const markLine = candle.markLine as { data: Array<Record<string, unknown>> };
    expect(markLine.data).toHaveLength(3);
    expect(markLine.data.map((item) => (item.lineStyle as { color: string }).color)).toEqual([
      "#f6bd60", "#f6bd60", "#f6bd60",
    ]);
    expect(markLine.data.map((item) => (item.label as { formatter: string }).formatter)).toEqual([
      "白\n酒\n消\n费", "业\n绩\n压\n力", "渠\n道\n调\n研",
    ]);
    expect(markLine.data.map((item) => item.name)).not.toContain("weekend");
    expect(markLine.data.every((item) => (item.lineStyle as { type: string }).type === "dashed")).toBe(true);
    expect(markLine.data.every((item) => (item.label as { position: string }).position === "middle")).toBe(true);
    expect(markLine.data.every((item) => (item.label as { rotate: number }).rotate === 0)).toBe(true);
    expect((markLine.data[1].lineStyle as { width: number }).width).toBe(2);
  });

  it("keeps every event title centered on its own line when anchors are close together", () => {
    const option = stockTimelineOption(timeline(), null);
    const candle = (option.series as Array<Record<string, unknown>>)[0];
    const markLine = candle.markLine as { data: Array<{ label: { offset: [number, number] } }> };
    expect(markLine.data.map((item) => item.label.offset[1])).toEqual([0, 0, 0]);
  });

  it("thins dense evidence labels while always keeping the selected event visible", () => {
    const option = stockTimelineOption(denseTimeline(), "dense-1");
    const candle = (option.series as Array<Record<string, unknown>>)[0];
    const markLine = candle.markLine as { data: Array<{ name: string; label: { formatter: string } }> };

    expect(markLine.data).toHaveLength(15);
    expect(markLine.data.map((item) => item.name)).toContain("dense-1");
    expect(markLine.data.every((item) => item.label.formatter.includes("\n"))).toBe(true);

    const compact = stockTimelineOption(denseTimeline(), "dense-1", 3);
    const compactCandle = (compact.series as Array<Record<string, unknown>>)[0];
    const compactMarkLine = compactCandle.markLine as { data: Array<{ name: string }> };
    expect(compactMarkLine.data).toHaveLength(3);
    expect(compactMarkLine.data.map((item) => item.name)).toContain("dense-1");
  });
});


describe("StockEventKline", () => {
  beforeEach(() => {
    setOption.mockClear();
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, value: 900 });
    Object.defineProperty(HTMLElement.prototype, "clientHeight", { configurable: true, value: 560 });
  });

  it("links the evidence list to chart selection and explains unpinned events", async () => {
    const load = vi.fn().mockResolvedValue(timeline());
    render(<StockEventKline symbol="600519" asOf="2026-07-28" load={load} />);

    expect(await screen.findByRole("heading", { name: "事件 K 线" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "个股新闻与热点事件 K 线" }))
      .toHaveClass("terminal-panel", "stock-event-kline");
    const evidenceLog = screen.getByRole("complementary", { name: "事件记录" });
    expect(screen.getByText("已落图 3 / 全部 4 条已核验证据")).toBeInTheDocument();
    expect(within(evidenceLog).getByText("消费政策迎来边际变化")).toBeInTheDocument();
    expect(within(evidenceLog).getByText("周末公开新闻").closest("button")).toHaveTextContent("非交易日·未落图");

    fireEvent.click(within(evidenceLog).getByText("公司披露阶段性经营压力"));
    expect(within(evidenceLog).getByText("公司披露阶段性经营压力").closest("button")).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(setOption).toHaveBeenCalled());
    expect(load).toHaveBeenCalledWith("600519", "2026-07-28", expect.any(AbortSignal));
  });

  it("defaults to the latest plotted event and synchronizes index, detail, and evidence", async () => {
    const load = vi.fn().mockResolvedValue(timeline());
    render(<StockEventKline symbol="600519" asOf="2026-07-28" load={load} />);

    const latestIndex = await screen.findByRole("button", { name: /^03 .*渠道调研/ });
    const evidenceLog = screen.getByRole("complementary", { name: "事件记录" });
    expect(latestIndex).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("机构发布渠道调研纪要");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("突发");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("多源确认");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("直接关联");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("2 个来源");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("行业板块");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("影响强度：中");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("价格反映：待核验");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("后续观察：观察板块成交额、涨停扩散和龙头持续性");
    expect(screen.getByRole("region", { name: "个股新闻与热点事件 K 线" })).toHaveTextContent("事件归属色不代表涨跌");
    expect(screen.getByRole("region", { name: "个股新闻与热点事件 K 线" }).querySelectorAll("[data-event-category-legend]")).toHaveLength(8);
    expect(within(evidenceLog).getByText("机构发布渠道调研纪要").closest("button")).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: /^02 .*公司披露阶段性经营压力/ }));

    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("公司披露阶段性经营压力");
    expect(within(evidenceLog).getByText("公司披露阶段性经营压力").closest("button")).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps non-trading-day evidence out of the numbered event index", async () => {
    const load = vi.fn().mockResolvedValue(timeline());
    render(<StockEventKline symbol="600519" asOf="2026-07-28" load={load} />);

    expect(await screen.findAllByTestId("stock-event-index-item")).toHaveLength(3);
    const evidenceLog = screen.getByRole("complementary", { name: "事件记录" });
    expect(screen.queryByRole("button", { name: /周末事件/ })).not.toBeInTheDocument();
    expect(within(evidenceLog).getByText("周末公开新闻").closest("button")).toHaveTextContent("非交易日·未落图");
  });

  it("shows up to fifteen readable event headlines in a three-column index", async () => {
    const load = vi.fn().mockResolvedValue(denseTimeline());
    render(<StockEventKline symbol="600000" asOf="2026-06-30" load={load} />);

    await waitFor(() => expect(screen.getAllByTestId("stock-event-index-item")).toHaveLength(15));
    expect(screen.getAllByTestId("stock-event-index-item").every((item) => (
      /第 \d+ 条已核验新闻/.test(item.textContent ?? "")
    ))).toBe(true);

    const css = readFileSync("src/app/theme.css", "utf8");
    expect(css).toMatch(/\.stock-event-index\s*\{[^}]*grid-template-columns:\s*repeat\(3,/s);
    expect(css).toMatch(/\.stock-event-index-item strong\s*\{[^}]*-webkit-line-clamp:\s*2/s);
  });

  it("refreshes the local timeline after the cockpit news snapshot changes", async () => {
    const load = vi.fn().mockResolvedValue(timeline());
    const view = render(<StockEventKline symbol="600001" asOf="2026-07-28" refreshToken="news-1" load={load} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));

    view.rerender(<StockEventKline symbol="600001" asOf="2026-07-28" refreshToken="news-2" load={load} />);

    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });

  it("keeps the cached timeline and explains a failed background refresh", async () => {
    const cacheKeySymbol = "600888";
    const cachedLoad = vi.fn().mockResolvedValue(timeline());
    const first = render(<StockEventKline symbol={cacheKeySymbol} asOf="2026-07-28" load={cachedLoad} />);
    expect((await screen.findAllByText("消费政策迎来边际变化")).length).toBeGreaterThan(0);
    first.unmount();

    render(<StockEventKline
      symbol={cacheKeySymbol}
      asOf="2026-07-28"
      load={() => Promise.reject(new Error("timeline request timeout"))}
    />);

    expect(screen.getAllByText("消费政策迎来边际变化").length).toBeGreaterThan(0);
    expect(await screen.findByText("更新失败：请求超时，请稍后重试。当前保留上次的本地快照")).toBeInTheDocument();
  });

  it("refreshes the live timeline when a verified realtime snapshot arrives", async () => {
    const load = vi.fn().mockResolvedValue(timeline());
    const encoder = new TextEncoder();
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => {
      const frame = "data: " + JSON.stringify({
        event_id: "market-overview-2", kind: "market_overview", sequence: 2,
        observed_at: "2026-08-18T10:01:00Z", source: "tencent-index-minute",
        freshness: "live", payload: { status: "ready" },
      }) + "\n\n";
      return {
        ok: true,
        status: 200,
        body: {
          getReader: () => ({
            read: vi.fn()
              .mockResolvedValueOnce({ done: false, value: encoder.encode(frame) })
              .mockResolvedValue({ done: true, value: undefined }),
            releaseLock: vi.fn(),
          }),
        },
      };
    }));

    render(<StockEventKline symbol="600519" load={load} />);

    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    vi.unstubAllGlobals();
  });
});
