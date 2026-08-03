import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("echarts", () => ({ init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })) }));

import { buildAnomalyMarkers, OverviewMinuteChart, overviewMinuteOption } from "./OverviewMinuteChart";

describe("OverviewMinuteChart", () => {
  it("creates an intraday option with anomaly marker lines", () => {
    const option = overviewMinuteOption(
      [{ observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" }],
      [{ anomaly_id: "a1", occurred_at: "2026-07-29T09:30:00+08:00", label: "算力", headline: "异动", direction: "positive", themes: [], symbols: [] }],
      "a1",
    );

    expect(option.series).toHaveLength(2);
    expect(JSON.stringify(option)).toContain("算力");
  });

  it("keeps the complete A-share session on the axis without inventing future prices", () => {
    const option = overviewMinuteOption(
      [
        { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" },
        { observed_at: "2026-07-29T10:00:00+08:00", price: "3810", volume: "12", amount: "120" },
      ],
      [],
      null,
    );

    const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
    const priceSeries = Array.isArray(option.series) ? option.series[0] : option.series;
    expect(xAxis).toMatchObject({
      data: expect.arrayContaining(["09:30", "11:30", "13:00", "15:00"]),
    });
    expect((priceSeries as { data: Array<number | null> }).data.at(-1)).toBeNull();
  });

  it("pins second-level events to the nearest real minute and drops unrelated events", () => {
    const points = [
      { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" },
      { observed_at: "2026-07-29T09:31:00+08:00", price: "3801", volume: "12", amount: "120" },
    ];
    const markers = buildAnomalyMarkers(points, [
      { anomaly_id: "a1", occurred_at: "2026-07-29T09:30:42+08:00", label: "算力", headline: "异动", direction: "positive", themes: [], symbols: [] },
      { anomaly_id: "old", occurred_at: "2026-07-28T09:30:00+08:00", label: "旧闻", headline: "旧闻", direction: "neutral", themes: [], symbols: [] },
    ], "a1");

    expect(markers).toHaveLength(1);
    expect(markers[0].xAxis).toBe("09:31");
    expect(markers[0].lineStyle).toMatchObject({ color: "#d92131", type: "solid", width: 2 });
    expect(markers[0].label).toMatchObject({ formatter: "算\n力", rotate: 0 });
  });

  it("uses A-share colors and staggered labels for adjacent event markers", () => {
    const points = [0, 1, 2].map((minute) => ({
      observed_at: `2026-07-29T09:3${minute}:00+08:00`, price: "3800", volume: "10", amount: "100",
    }));
    const markers = buildAnomalyMarkers(points, [
      { anomaly_id: "up", occurred_at: "2026-07-29T09:30:00+08:00", label: "拉升", headline: "拉升", direction: "positive", themes: [], symbols: [] },
      { anomaly_id: "down", occurred_at: "2026-07-29T09:31:00+08:00", label: "风险", headline: "风险", direction: "negative", themes: [], symbols: [] },
      { anomaly_id: "wait", occurred_at: "2026-07-29T09:32:00+08:00", label: "待确认", headline: "待确认", direction: "uncertain", themes: [], symbols: [] },
    ], null);

    expect(markers.map((item) => item.lineStyle.color)).toEqual(["#96343d", "#96343d", "#7b8794"]);
    expect(markers.map((item) => item.label.offset[1])).toEqual([0, 148, 0]);
  });

  it("adds a hollow intersection marker at each verified event price", () => {
    const option = overviewMinuteOption(
      [
        { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" },
        { observed_at: "2026-07-29T09:31:00+08:00", price: "3802", volume: "12", amount: "120" },
      ],
      [{ anomaly_id: "a1", occurred_at: "2026-07-29T09:30:42+08:00", label: "算力", headline: "异动", direction: "positive", themes: [], symbols: [] }],
      null,
    );

    const priceSeries = (option.series as Array<Record<string, unknown>>)[0];
    expect(priceSeries.markPoint).toMatchObject({
      symbol: "circle",
      data: [{ name: "算力", coord: ["09:31", 3802] }],
    });
  });

  it("shows an explicit empty state instead of synthetic points", () => {
    render(<OverviewMinuteChart points={[]} anomalies={[]} selectedAnomalyId={null} />);
    expect(document.body).toHaveTextContent("分时数据暂不可用");
  });
});
