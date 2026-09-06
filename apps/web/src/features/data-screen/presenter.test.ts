import { describe, expect, it } from "vitest";

import { buildDataScreenModel } from "./presenter";
import type { MarketOverviewResponse } from "../market-overview/types";

function snapshot(overrides: Partial<MarketOverviewResponse> = {}): MarketOverviewResponse {
  return {
    status: "ready",
    as_of: "2026-09-01",
    observed_at: "2026-09-01T02:00:00.000Z",
    sentiment: { score: "68", band: "偏强", coverage_percent: "99", quality: "ready", observed_at: "2026-09-01T02:00:00.000Z" },
    breadth: { rising_count: 3200, falling_count: 1500, flat_count: 200, valid_count: 4900 },
    limit_ecology: { limit_up_count: 80, limit_down_count: 5, broken_limit_up_count: 12, seal_rate_percent: "86.4" },
    liquidity: { total_amount_yi: "9800", baseline_amount_yi: "8600", relative_amount: "1.14" },
    market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-09-01T02:00:00.000Z", quote_count: 4900, universe_count: 5000, phase: "intraday", freshness: "live" },
    indices: [
      { instrument: "sh000001", name: "上证指数", value: "3200", change: "12", change_percent: "0.38", observed_at: "2026-09-01T02:00:00.000Z", source: "tdx-local-rpc", quality: "ready" },
      { instrument: "sz399001", name: "深证成指", value: "10100", change: "-42", change_percent: "-0.41", observed_at: "2026-09-01T02:00:00.000Z", source: "tdx-local-rpc", quality: "ready" },
    ],
    minute_series: [], anomalies: [], live_feed: [],
    sectors: [
      { sector_id: "s1", name: "算力", change_percent: "2.3", amount_yi: "320", limit_up_count: 8, rising_count: 40, falling_count: 4, stock_count: 48 },
      { sector_id: "s2", name: "医药", change_percent: "-1.2", amount_yi: "210", limit_up_count: 1, rising_count: 8, falling_count: 32, stock_count: 44 },
    ],
    sector_stocks: {}, market_stocks: [], warnings: [], sources: ["通达信", "腾讯"],
    ...overrides,
  };
}

describe("buildDataScreenModel", () => {
  it("aggregates breadth, indices and sectors with red-up/green-down tones", () => {
    const model = buildDataScreenModel(snapshot());
    expect(model.breadth.total).toBe(4900);
    expect(model.breadth.risingPercent).toBeCloseTo(65.3, 1);
    expect(model.indices[0]).toMatchObject({ name: "上证指数", tone: "up" });
    expect(model.indices[1]).toMatchObject({ name: "深证成指", tone: "down" });
    expect(model.sectors[0].tone).toBe("up");
    expect(model.sectors[1].tone).toBe("down");
  });

  it("marks missing or unavailable data without inventing values", () => {
    const model = buildDataScreenModel(snapshot({
      status: "unavailable",
      market_data: { ...snapshot().market_data, quality: "unavailable", quote_count: 0 },
      indices: [], sectors: [],
    }));
    expect(model.status).toBe("unavailable");
    expect(model.breadth.total).toBeNull();
    expect(model.indices).toEqual([]);
    expect(model.coverage.label).toBe("暂无有效行情");
  });

  it("keeps projection lists bounded", () => {
    const sectors = Array.from({ length: 30 }, (_, index) => ({
      sector_id: `s${index}`, name: `板块${index}`, change_percent: String(index), amount_yi: "1",
      limit_up_count: 0, rising_count: 1, falling_count: 0, stock_count: 1,
    }));
    expect(buildDataScreenModel(snapshot({ sectors })).sectors).toHaveLength(10);
  });

  it("does not present an unmapped supplier sector as a formal industry", () => {
    const model = buildDataScreenModel(snapshot({
      sectors: [{ sector_id: "raw-1", name: "自定义概念", change_percent: "1.2", amount_yi: "1", limit_up_count: 0, rising_count: 1, falling_count: 0, stock_count: 1 }],
    }));

    expect(model.sectors[0].name).toBe("申万行业待核验");
    expect(model.sectors[0].industry_system).toBe("待核验");
  });

  it("deduplicates historical sector-flow samples and keeps the latest breakdown", () => {
    const model = buildDataScreenModel(snapshot({
      sector_fund_flow: [
        { sector_code: "BK0001", sector_name: "银行", observed_at: "2026-09-01T01:00:00.000Z", main_net_yi: "10.00", large_net_yi: "4.00", super_net_yi: "6.00", source: "eastmoney", quality: "ready" },
        { sector_code: "BK0001", sector_name: "银行", observed_at: "2026-09-01T02:00:00.000Z", main_net_yi: "21.70", large_net_yi: "9.20", super_net_yi: "12.50", source: "eastmoney", quality: "ready" },
        { sector_code: "BK0002", sector_name: "非金融", observed_at: "2026-09-01T02:00:00.000Z", main_net_yi: "15.00", large_net_yi: "7.00", super_net_yi: "8.00", source: "eastmoney", quality: "ready" },
      ],
    }));
    expect(model.sectorFlows).toHaveLength(2);
    expect(model.sectorFlows[0]).toMatchObject({ code: "BK0001", name: "银行", net: 21.7, largeNet: 9.2, superNet: 12.5, delta: 11.7, samples: 2 });
  });

  it("keeps the source sector change percent when the sector catalogue is incomplete", () => {
    const model = buildDataScreenModel(snapshot({
      sectors: [],
      sector_fund_flow: [
        { sector_code: "BK0009", sector_name: "半导体", observed_at: "2026-09-01T02:00:00.000Z", change_percent: "-2.35", main_net_yi: "-18.40", large_net_yi: null, super_net_yi: null, source: "eastmoney", quality: "ready" },
      ],
    }));
    expect(model.sectorFlows[0]).toMatchObject({ code: "BK0009", net: -18.4, changePercent: -2.35 });
  });
});
