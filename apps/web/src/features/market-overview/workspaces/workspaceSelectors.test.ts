import { describe, expect, it } from "vitest";
import type { MarketOverviewResponse } from "../types";
import { buildWorkspaceMarketModel, numberValue, stocksForVariant } from "./workspaceSelectors";

const baseResponse = (overrides: Partial<MarketOverviewResponse> = {}): MarketOverviewResponse => ({
  status: "ready",
  as_of: "2026-08-06",
  observed_at: "2026-08-06T10:00:00+08:00",
  sentiment: { score: null, band: "数据不足", coverage_percent: "0", quality: "partial", observed_at: "2026-08-06T10:00:00+08:00" },
  breadth: { rising_count: 0, falling_count: 0, flat_count: 0, valid_count: 0 },
  limit_ecology: { limit_up_count: 0, limit_down_count: 0, broken_limit_up_count: 0, seal_rate_percent: null },
  liquidity: { total_amount_yi: null, baseline_amount_yi: null, relative_amount: null },
  market_data: { source: "test", quality: "ready", observed_at: "2026-08-06T10:00:00+08:00", quote_count: 1, universe_count: 1 },
  indices: [],
  minute_series: [],
  anomalies: [],
  live_feed: [],
  sectors: [],
  sector_stocks: {},
  market_stocks: [],
  warnings: [],
  sources: ["test"],
  ...overrides,
});

describe("workspaceSelectors evidence boundaries", () => {
  it("keeps missing numeric evidence unavailable instead of coercing it to zero", () => {
    expect(numberValue(null)).toBeNull();
    expect(numberValue(undefined)).toBeNull();
    expect(numberValue("not-a-number")).toBeNull();
  });

  it("does not derive price metrics or attention score from incomplete stock evidence", () => {
    const model = buildWorkspaceMarketModel(baseResponse({
      market_stocks: [{
        symbol: "600001",
        name: "缺失数据股",
        price: null as unknown as string,
        previous_close: null as unknown as string,
        open: null as unknown as string,
        high: null as unknown as string,
        low: null as unknown as string,
        volume: null as unknown as string,
        amount_yi: null as unknown as string,
        change_percent: null as unknown as string,
        state: "active",
        observed_at: "2026-08-06T10:00:00+08:00",
        source: "test",
        quality: "partial",
      }],
    }));

    expect(model.stocks[0]).toMatchObject({
      change: null,
      amount: null,
      gap: null,
      amplitude: null,
      closePosition: null,
      highPullback: null,
      attentionScore: null,
    });
  });

  it("excludes incomplete stocks from amount and auction rule results", () => {
    const model = buildWorkspaceMarketModel(baseResponse({
      market_stocks: [{
        symbol: "600002",
        name: "缺失成交额",
        price: "10.5",
        previous_close: "10",
        open: "10.1",
        high: "10.8",
        low: "9.9",
        volume: "1000",
        amount_yi: null as unknown as string,
        change_percent: "5",
        state: "active",
        observed_at: "2026-08-06T10:00:00+08:00",
        source: "test",
        quality: "partial",
      }],
    }));

    expect(stocksForVariant(model, "amount-only")).toEqual([]);
    expect(stocksForVariant(model, "auction-pass")).toEqual([]);
  });

  it("keeps sector strength unavailable when required market fields are missing", () => {
    const model = buildWorkspaceMarketModel(baseResponse({
      sectors: [{
        sector_id: "s1",
        name: "字段不足板块",
        change_percent: null,
        amount_yi: null,
        limit_up_count: 0,
        rising_count: 0,
        falling_count: 0,
        stock_count: 0,
      }],
    }));

    expect(model.sectors[0]).toMatchObject({
      change: null,
      amount: null,
      breadthPercent: null,
      limitDensityPercent: null,
      strengthScore: null,
    });
  });
});
