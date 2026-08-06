import { describe, expect, it } from "vitest";

import {
  buildBarLineOption,
  buildCandlestickOption,
  buildDualAxisOption,
  buildGaugeOption,
  buildHeatmapOption,
  buildRadarOption,
  buildTreemapOption,
} from "./chartOptions";

function firstSeries(option: { series?: unknown }) {
  return Array.isArray(option.series)
    ? option.series[0] as { data?: unknown; type?: string }
    : option.series as { data?: unknown; type?: string };
}

describe("chart option factories", () => {
  it("keeps missing bar and line points as null and disables false interpolation", () => {
    const option = buildBarLineOption({
      categories: ["09:30", "09:31"],
      bars: [{ name: "成交额", values: [10, null] }],
      lines: [{ name: "价格", values: [12.2, null] }],
    });
    expect(option.series).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: "成交额", data: [10, null], type: "bar" }),
      expect.objectContaining({ name: "价格", data: [12.2, null], type: "line", connectNulls: false }),
    ]));
  });

  it("uses explicit red/green semantic colors for dual-axis rise and fall series", () => {
    const option = buildDualAxisOption({
      categories: ["A", "B"],
      primary: { name: "涨幅", values: [1, -1] },
      secondary: { name: "成交额", values: [100, 120] },
      primaryTone: "up",
      secondaryTone: "neutral",
    });
    expect(option.yAxis).toHaveLength(2);
    expect(option.series).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: "涨幅", itemStyle: expect.objectContaining({ color: "var(--market-up, #f04f5f)" }) }),
    ]));
  });

  it("builds radar, heatmap, treemap, gauge and candlestick without inventing null values", () => {
    const radar = buildRadarOption({ indicators: [{ name: "趋势", max: 100 }], values: [null] });
    expect(firstSeries(radar)).toEqual(expect.objectContaining({ type: "radar" }));
    expect((firstSeries(radar).data as Array<{ value?: unknown }>)[0]?.value).toEqual([null]);

    const heatmap = buildHeatmapOption({ x: ["周一"], y: ["金融"], values: [[0, 0, null]] });
    expect(firstSeries(heatmap)).toEqual(expect.objectContaining({ type: "heatmap" }));
    expect(firstSeries(heatmap).data).toEqual([[0, 0, null]]);

    const treemap = buildTreemapOption({ data: [{ name: "资产", value: null }] });
    expect(firstSeries(treemap)).toEqual(expect.objectContaining({ type: "treemap" }));
    expect(firstSeries(treemap).data).toEqual([{ name: "资产", value: null }]);

    const gauge = buildGaugeOption({ value: null, name: "情绪" });
    expect(firstSeries(gauge)).toEqual(expect.objectContaining({ type: "gauge" }));
    expect(firstSeries(gauge).data).toEqual([{ value: null, name: "情绪" }]);

    const candle = buildCandlestickOption({ categories: ["D1"], values: [[null, null, null, null]] });
    expect(firstSeries(candle)).toEqual(expect.objectContaining({ type: "candlestick" }));
    expect(firstSeries(candle).data).toEqual([[null, null, null, null]]);
  });
});
