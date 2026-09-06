import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataScreenCharts } from "./DataScreenCharts";
import type { DataScreenModel } from "./types";

vi.mock("../quant-analysis/QuantChart", () => ({
  QuantChart: ({ ariaLabel, option }: { ariaLabel: string; option?: { xAxis?: { data?: string[] } } }) => (
    <div role="img" aria-label={ariaLabel} data-points={option?.xAxis?.data?.join(",") ?? ""} />
  ),
}));

const model = {
  status: "ready", asOf: "2026-09-01", observedAt: "2026-09-01T06:00:00.000Z", marketPhase: "intraday", freshness: "live",
  breadth: { rising: 1, falling: 1, flat: 0, total: 2, risingPercent: 50 }, limits: { up: 1, down: 1, broken: 0, sealRate: 100 },
  liquidity: { total: 100, relative: 1 }, sentiment: { score: 60, band: "偏强", coverage: 100 }, regime: { name: "轮动震荡", emotion: 60, risk: 30, heat: 60, rotation: 70 },
  indices: [
    { instrument: "sh000001", name: "上证指数", value: "3200", change: "1", change_percent: "0.1", observed_at: "2026-09-01T06:00:00.000Z", source: "tencent", quality: "ready", tone: "up" },
    { instrument: "sz399001", name: "深证成指", value: "10000", change: "2", change_percent: "0.2", observed_at: "2026-09-01T06:00:00.000Z", source: "tencent", quality: "ready", tone: "up" },
    { instrument: "sz399006", name: "创业板指", value: "2000", change: "3", change_percent: "0.3", observed_at: "2026-09-01T06:00:00.000Z", source: "tencent", quality: "ready", tone: "up" },
  ],
  minuteSeries: [{ observed_at: "2026-09-01T09:30:00+08:00", price: 3200, changePercent: 0, volume: 1 }],
  minuteSeriesByIndex: {
    sh000001: [{ observed_at: "2026-09-01T09:30:00+08:00", price: 3200, changePercent: 0, volume: 1 }],
    sz399001: [{ observed_at: "2026-09-01T09:30:00+08:00", price: 10000, changePercent: 0, volume: 2 }],
    sz399006: [{ observed_at: "2026-09-01T09:30:00+08:00", price: 2000, changePercent: 0, volume: 3 }],
  },
  sectors: [], sectorFlows: [], largeOrders: [], topStocks: [], anomalies: [], liveFeed: [], officialEvents: [],
  dataScope: { marketQuotes: null, universe: null, stockSamples: null, sectorSamples: null, largeOrderSamples: null }, coverage: { quoteCount: null, universeCount: null, percent: null, label: "" }, sources: [],
} satisfies DataScreenModel;

describe("DataScreenCharts index trend rotation", () => {
  it("renders trend titles and rotates the active index every ten seconds", () => {
    vi.useFakeTimers();
    const { unmount } = render(<DataScreenCharts model={model} showNews={false} />);
    expect(screen.getByText("上证指数趋势")).toBeInTheDocument();
    expect(screen.getByText("深圳成指趋势")).toBeInTheDocument();
    expect(screen.getByText("创业板指趋势")).toBeInTheDocument();
    expect(screen.getByTestId("data-screen-index-trend-sh000001")).toHaveAttribute("aria-current", "true");
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByTestId("data-screen-index-trend-sz399001")).toHaveAttribute("aria-current", "true");
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByTestId("data-screen-index-trend-sz399006")).toHaveAttribute("aria-current", "true");
    unmount();
    act(() => vi.advanceTimersByTime(30_000));
    vi.useRealTimers();
  });

  it("binds the chart to the active index minute series", () => {
    vi.useFakeTimers();
    render(<DataScreenCharts model={model} showNews={false} />);
    const chart = screen.getByRole("img", { name: "指数趋势图" });
    expect(chart).toHaveAttribute("data-points", "09:30");
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByRole("img", { name: "指数趋势图" })).toHaveAttribute("data-points", "09:30");
    vi.useRealTimers();
  });
});
