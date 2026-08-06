import { describe, expect, it } from "vitest";

import { featureRows } from "../featureCatalog";
import type { MarketOverviewResponse } from "../types";
import { buildWorkspaceMarketModel } from "./workspaceSelectors";
import { buildWorkspaceInsights, WORKSPACE_INSIGHT_PROFILES } from "./workspaceInsights";

const data = {
  sentiment: { score: "63", band: "轮动", coverage_percent: "92", quality: "ready", observed_at: "2026-07-30T10:30:00+08:00" },
  breadth: { rising_count: 3000, falling_count: 1900, flat_count: 100, valid_count: 5000 },
  limit_ecology: { limit_up_count: 38, limit_down_count: 4, broken_limit_up_count: 12, seal_rate_percent: "76" },
  liquidity: { total_amount_yi: "11000", baseline_amount_yi: "10000", relative_amount: "1.10" },
  market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-07-30T10:30:00+08:00", quote_count: 5000, universe_count: 5200 },
  anomalies: [{ anomaly_id: "a1", occurred_at: "2026-07-30T10:20:00+08:00", label: "算力拉升", headline: "算力快速拉升", direction: "positive", themes: ["算力"], symbols: ["600001"] }],
  live_feed: [{ event_id: "n1", occurred_at: "2026-07-30T10:22:00+08:00", headline: "算力需求增长", summary: "公开摘要", themes: ["算力"], symbols: ["600001"], source: "公开资讯", review_state: "verified" }],
  sectors: [{ sector_id: "s1", name: "算力", change_percent: "4.2", amount_yi: "220", limit_up_count: 3, rising_count: 40, falling_count: 5, stock_count: 50 }],
  market_stocks: [{ symbol: "600001", name: "样本股", price: "11", previous_close: "10", open: "10.3", high: "11", low: "10", volume: "100", amount_yi: "30", change_percent: "10", state: "limit_up", observed_at: "2026-07-30T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" }],
  review: {
    latest_trade_date: "2026-07-29", universe_count: 5200, history_ready_count: 5100,
    consecutive_limit_up: [], first_limit_up: [], volume_breakouts: [], previous_high_breakouts: [], low_position_volume: [],
    dragon_tiger: [{ symbol: "600001", name: "样本股", trade_date: "2026-07-29", reason: "偏离值", change_percent: "10", buy_amount_yi: "3", sell_amount_yi: "1", net_amount_yi: "2", source: "eastmoney-dragon-tiger", seats: [{ symbol: "600001", trade_date: "2026-07-29", seat_name: "某营业部", direction: "buy", buy_amount_yi: "2", sell_amount_yi: "0.5", net_amount_yi: "1.5", source: "eastmoney-dragon-tiger" }] }],
  },
} as unknown as MarketOverviewResponse;

describe("workspace insights", () => {
  it("assigns every menu a unique, explicit metric contract", () => {
    const labels = featureRows.flat();
    expect(Object.keys(WORKSPACE_INSIGHT_PROFILES)).toHaveLength(labels.length);
    expect(new Set(Object.keys(WORKSPACE_INSIGHT_PROFILES))).toEqual(new Set(labels));
    const signatures = labels.map((label) => WORKSPACE_INSIGHT_PROFILES[label].join("|"));
    expect(new Set(signatures)).toHaveLength(labels.length);
  });

  it("uses real seat records for seat workspaces and never amount proxies", () => {
    const model = buildWorkspaceMarketModel(data);
    const tracking = buildWorkspaceInsights("游资追踪", data, model);
    const movement = buildWorkspaceInsights("游资动向", data, model);

    expect(tracking.map((item) => item.label)).toContain("可验证席位");
    expect(tracking.map((item) => item.value)).toContain("1");
    expect(movement.map((item) => item.label)).toContain("席位净买额");
    expect(movement.map((item) => item.value)).toContain("+1.50亿");
    expect([...tracking, ...movement].map((item) => item.detail).join(" ")).not.toMatch(/成交额.*替代/);
  });

  it("marks unsupported proprietary evidence unavailable instead of deriving a proxy", () => {
    const insights = buildWorkspaceInsights("主力大单监控", data, buildWorkspaceMarketModel(data));
    expect(insights.some((item) => item.value === "未接入" && item.quality === "unavailable")).toBe(true);
    expect(insights.map((item) => item.label)).not.toContain("成交活跃");
  });

  it("keeps an unavailable empty dragon-tiger response unavailable", () => {
    const emptySeats = {
      ...data,
      review: { ...data.review!, dragon_tiger: [], warnings: ["dragon_tiger_unavailable"] },
    } as MarketOverviewResponse;
    const insights = buildWorkspaceInsights("游资动向", emptySeats, buildWorkspaceMarketModel(emptySeats));

    expect(insights.every((item) => item.quality === "unavailable")).toBe(true);
    expect(insights.map((item) => item.value)).not.toContain("+0.00亿");
  });

  it("does not report zero history coverage as a verified historical metric", () => {
    const emptyHistory = {
      ...data,
      review: { ...data.review!, universe_count: 5200, history_ready_count: 0, quality: "partial" },
    } as MarketOverviewResponse;
    const insights = buildWorkspaceInsights("百日新高", emptyHistory, buildWorkspaceMarketModel(emptyHistory));
    const coverage = insights.find((item) => item.key === "history-coverage");

    expect(coverage?.quality).toBe("unavailable");
    expect(coverage?.value).toBe("未接入");
    expect(coverage?.value).not.toBe("0.0%");
  });
});
