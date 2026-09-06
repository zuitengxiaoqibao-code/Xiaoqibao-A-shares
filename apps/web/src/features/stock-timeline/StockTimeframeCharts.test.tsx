import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import { StockTimeframeCharts, stockIntradayOption, stockThirtyDayOption } from "./StockTimeframeCharts";
import type { StockTimelineResponse } from "./types";


vi.mock("echarts", () => ({
  init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })),
}));

function timeline(): StockTimelineResponse {
  const bars = Array.from({ length: 35 }, (_, index) => {
    const tradeDate = new Date(Date.UTC(2026, 5, 1 + index)).toISOString().slice(0, 10);
    const close = 100 + index;
    return {
      symbol: "600519",
      trade_date: tradeDate,
      open: String(close - 1),
      high: String(close + 2),
      low: String(close - 2),
      close: String(close),
      volume: 1000 + index,
      amount: String((1000 + index) * close),
      source: "local-daily-bars",
    };
  });
  return {
    symbol: "600519",
    as_of: "2026-07-05",
    cutoff: "2026-07-05T15:00:00+08:00",
    status: "ready",
    bars,
    events: [],
    sources: ["local-daily-bars"],
    warnings: [],
    intraday_status: "ready",
    intraday_points: [
      { symbol: "600519", price: "133", change: "1", change_percent: "0.76", volume: "1000", source: "tencent-realtime", observed_at: "2026-07-05T09:31:10+08:00", fetched_at: "2026-07-05T09:31:11+08:00", quality: "ready", source_snapshot_id: "minute-1a" },
      { symbol: "600519", price: "133.5", change: "1.5", change_percent: "1.14", volume: "1100", source: "tencent-realtime", observed_at: "2026-07-05T09:31:50+08:00", fetched_at: "2026-07-05T09:31:51+08:00", quality: "ready", source_snapshot_id: "minute-1b" },
      { symbol: "600519", price: "132", change: "-1", change_percent: "-0.75", volume: "1300", source: "tencent-realtime", observed_at: "2026-07-05T09:32:00+08:00", fetched_at: "2026-07-05T09:32:01+08:00", quality: "ready", source_snapshot_id: "minute-2" },
    ],
    intraday_sources: ["tencent-realtime"],
    intraday_warnings: [],
  };
}

describe("stock timeframe chart options", () => {
  it("builds an intraday price line, previous-close guide, and red-green volume", () => {
    const data = timeline();
    const option = stockIntradayOption(data);
    const series = option.series as Array<Record<string, unknown>>;

    expect(series.map((item) => item.name)).toEqual(["价格", "成交量"]);
    expect(series[0].type).toBe("line");
    expect((series[0].markLine as { data: Array<{ name: string; yAxis: number }> }).data)
      .toContainEqual(expect.objectContaining({ name: "昨收", yAxis: 133 }));
    expect(series[1].type).toBe("bar");
    const volumes = series[1].data as Array<number | null>;
    expect([volumes[1], volumes[2]]).toEqual([null, 200]);
    const color = (series[1].itemStyle as { color: (item: { dataIndex: number }) => string }).color;
    expect(color({ dataIndex: 1 })).toBe("#f04f5f");
    expect(color({ dataIndex: 2 })).toBe("#2fcf91");
  });

  it("uses only the latest thirty real bars with candlesticks, moving averages, and volume", () => {
    const option = stockThirtyDayOption(timeline());
    const series = option.series as Array<Record<string, unknown>>;
    const xAxis = option.xAxis as Array<{ data: string[] }>;

    expect(xAxis[0].data).toHaveLength(30);
    expect(xAxis[0].data[0]).toBe("2026-06-06");
    expect(series.map((item) => item.name)).toEqual(["日 K", "MA5", "MA10", "MA20", "成交量"]);
    expect(series[0]).toMatchObject({ type: "candlestick" });
    expect(series[4]).toMatchObject({ type: "bar" });
    expect((series[3].data as Array<number | null>).filter((item) => item !== null)).toHaveLength(11);
  });

  it("keeps a real post-close snapshot visible at the end of the intraday session", () => {
    const source = timeline();
    const data = {
      ...source,
      intraday_points: [
        { ...source.intraday_points![0]!, observed_at: "2026-07-05T15:35:00+08:00", fetched_at: "2026-07-05T15:35:01+08:00", price: "134" },
      ],
    };
    const option = stockIntradayOption(data);
    const series = option.series as Array<Record<string, unknown>>;
    const prices = series[0].data as Array<number | null>;

    expect(prices.at(-1)).toBe(134);
    expect(series[0]).toMatchObject({ showSymbol: true, symbol: "circle", symbolSize: 8 });
  });
});

describe("StockTimeframeCharts", () => {
  it("renders both chart cards from the same timeline response", () => {
    render(<StockTimeframeCharts data={timeline()} />);

    expect(screen.getByRole("heading", { name: "当日分时" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "近 30 交易日" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "600519 当日分时行情" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "600519 近 30 交易日日 K 线" })).toBeInTheDocument();
  });

  it("keeps the daily chart visible when intraday snapshots are unavailable", () => {
    const data = { ...timeline(), intraday_status: "unavailable" as const, intraday_points: [], intraday_warnings: ["intraday_snapshots_unavailable"] };
    render(<StockTimeframeCharts data={data} />);

    expect(screen.getByText("当日没有已归档的真实分时数据")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "600519 近 30 交易日日 K 线" })).toBeInTheDocument();
  });

  it("keeps the intraday chart visible when daily bars are unavailable", () => {
    const data = { ...timeline(), status: "unavailable" as const, bars: [], warnings: ["local_daily_bars_unavailable"] };
    render(<StockTimeframeCharts data={data} />);

    expect(screen.getByRole("img", { name: "600519 当日分时行情" })).toBeInTheDocument();
    expect(screen.getByText("本地日线尚未就绪")).toBeInTheDocument();
  });

  it("uses two equal desktop columns and one responsive column", () => {
    const css = readFileSync("src/app/theme.css", "utf8");
    expect(css).toMatch(/\.stock-timeframe-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+minmax\(0,\s*1fr\)/s);
    expect(css).toMatch(/@media\s*\(max-width:\s*900px\)[\s\S]*?\.stock-timeframe-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  });
});
