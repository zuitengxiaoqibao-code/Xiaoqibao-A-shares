import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("echarts", () => ({ init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })) }));

import { anomalyAttributionColor, buildAnomalyPulseGroups, OverviewMinuteChart, overviewMinuteOption } from "./OverviewMinuteChart";

describe("OverviewMinuteChart", () => {
  it("centers the anomaly title on a vertical dashed marker line", () => {
    const option = overviewMinuteOption(
      [{ observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" }],
      [{ anomaly_id: "a1", occurred_at: "2026-07-29T09:30:00+08:00", label: "算力", headline: "异动", direction: "positive", themes: [], symbols: [] }],
      "a1",
    );

    expect(option.series).toHaveLength(2);
    const priceSeries = (option.series as Array<Record<string, unknown>>)[0];
    const markLine = priceSeries.markLine as { data: Array<Record<string, unknown>> };
    expect(markLine.data[0]).toMatchObject({
      lineStyle: { type: "dashed", width: 2 },
      label: { formatter: "算\n力", position: "middle", rotate: 0 },
    });
    expect(option.animation).toBe(false);
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

  it("pins second-level events to the nearest real minute and exposes both list numbers and chart titles", () => {
    const points = [
      { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" },
      { observed_at: "2026-07-29T09:31:00+08:00", price: "3801", volume: "12", amount: "120" },
    ];
    const groups = buildAnomalyPulseGroups(points, [
      { anomaly_id: "a1", occurred_at: "2026-07-29T09:30:42+08:00", label: "算力", headline: "异动", direction: "positive", themes: [], symbols: [] },
      { anomaly_id: "old", occurred_at: "2026-07-28T09:30:00+08:00", label: "旧闻", headline: "旧闻", direction: "neutral", themes: [], symbols: [] },
    ], "a1");

    expect(groups).toHaveLength(1);
    expect(groups[0]).toMatchObject({ minute: "09:31", marker: "02", lineLabel: "算\n力", selected: true, color: "#a78bfa" });
    expect(groups[0].events.map((item) => item.anomaly_id)).toEqual(["a1"]);
  });

  it("uses attribution colors that stay distinct from the red-green candles and cyan price line", () => {
    const points = [0, 1, 2].map((minute) => ({
      observed_at: `2026-07-29T09:3${minute}:00+08:00`, price: "3800", volume: "10", amount: "100",
    }));
    const groups = buildAnomalyPulseGroups(points, [
      { anomaly_id: "tech", occurred_at: "2026-07-29T09:30:00+08:00", label: "算力异动", headline: "AI 算力板块走强", direction: "positive", themes: ["算力"], symbols: [] },
      { anomaly_id: "finance", occurred_at: "2026-07-29T09:31:00+08:00", label: "券商异动", headline: "证券板块放量", direction: "negative", themes: ["证券"], symbols: [] },
      { anomaly_id: "health", occurred_at: "2026-07-29T09:32:00+08:00", label: "医药异动", headline: "创新药活跃", direction: "uncertain", themes: ["创新药"], symbols: [] },
    ], null);

    expect(groups.map((item) => item.color)).toEqual(["#a78bfa", "#f6bd60", "#f472b6"]);
    expect(groups.map((item) => item.lane)).toEqual([0, 1, 0]);
    expect(groups.map((item) => item.color)).not.toContain("#f04f5f");
    expect(groups.map((item) => item.color)).not.toContain("#2fcf91");
    expect(groups.map((item) => item.color)).not.toContain("#39c8dd");
  });

  it("keeps the same attribution color regardless of event direction or selection", () => {
    const positive = { anomaly_id: "a1", occurred_at: "2026-07-29T09:30:00+08:00", label: "机器人", headline: "工业机器人异动", direction: "positive" as const, themes: ["机器人"], symbols: [] };
    const negative = { ...positive, anomaly_id: "a2", direction: "negative" as const };

    expect(anomalyAttributionColor(positive)).toBe("#60a5fa");
    expect(anomalyAttributionColor(negative)).toBe("#60a5fa");
    const points = [{ observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" }];
    expect(buildAnomalyPulseGroups(points, [positive], "a1")[0].color).toBe("#60a5fa");
  });

  it("aggregates events mapped to the same minute instead of overlapping labels", () => {
    const points = [
      { observed_at: "2026-07-29T09:30:00+08:00", price: "3800", volume: "10", amount: "100" },
      { observed_at: "2026-07-29T09:31:00+08:00", price: "3801", volume: "12", amount: "120" },
    ];
    const groups = buildAnomalyPulseGroups(points, [
      { anomaly_id: "a1", occurred_at: "2026-07-29T09:30:40+08:00", label: "算力", headline: "算力异动", direction: "positive", themes: [], symbols: [] },
      { anomaly_id: "a2", occurred_at: "2026-07-29T09:31:10+08:00", label: "机器人", headline: "机器人异动", direction: "neutral", themes: [], symbols: [] },
    ], null);

    expect(groups).toHaveLength(1);
    expect(groups[0]).toMatchObject({ marker: "01 +1", lineLabel: "算\n力\n+1", minute: "09:31", count: 2 });
    expect(groups[0].events.map((item) => item.anomaly_id)).toEqual(["a1", "a2"]);

    const selectedSecond = buildAnomalyPulseGroups(points, [
      { anomaly_id: "a1", occurred_at: "2026-07-29T09:30:40+08:00", label: "算力", headline: "算力异动", direction: "positive", themes: [], symbols: [] },
      { anomaly_id: "a2", occurred_at: "2026-07-29T09:31:10+08:00", label: "机器人", headline: "机器人异动", direction: "neutral", themes: [], symbols: [] },
    ], "a2");
    expect(selectedSecond[0]).toMatchObject({ marker: "02 +1", lineLabel: "机\n器\n人\n+1", selected: true });
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
      data: [{ name: "01", coord: ["09:31", 3802] }],
    });
    const serialized = JSON.stringify(option);
    expect(serialized).toContain("算\\n力");
  });

  it("shows an explicit empty state instead of synthetic points", () => {
    render(<OverviewMinuteChart points={[]} anomalies={[]} selectedAnomalyId={null} />);
    expect(document.body).toHaveTextContent("分时数据暂不可用");
  });
});
