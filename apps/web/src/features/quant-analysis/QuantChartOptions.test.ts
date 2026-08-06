import { describe, expect, it } from "vitest";

import { tickOption } from "./QuantAnalysisDashboard";
import type { IntradayTick } from "./types";

const ticks: IntradayTick[] = [
  { symbol: "600000", observed_at: "2026-08-06T09:31:00+08:00", price: "10", change: "0.12", volume: "100", change_percent: "1.2", quality: "ready", source: "tdx", fetched_at: "2026-08-06T09:31:01+08:00", source_snapshot_id: "a" },
  { symbol: "600000", observed_at: "2026-08-06T09:32:00+08:00", price: "9.8", change: "-0.08", volume: "80", change_percent: "-0.8", quality: "ready", source: "tdx", fetched_at: "2026-08-06T09:32:01+08:00", source_snapshot_id: "b" },
];

describe("quant chart options", () => {
  it("keeps dense tick history navigable and colors volume by verified A-share direction", () => {
    const option = tickOption(ticks) as { dataZoom?: Array<{ type?: string }>; series?: Array<{ type?: string; itemStyle?: { color?: (params: { dataIndex: number }) => string } }> };
    expect(option.dataZoom?.map((item) => item.type)).toEqual(["inside", "slider"]);
    expect(option.series?.[1]?.itemStyle?.color?.({ dataIndex: 0 })).toBe("#f04f5f");
    expect(option.series?.[1]?.itemStyle?.color?.({ dataIndex: 1 })).toBe("#2fcf91");
  });
});
