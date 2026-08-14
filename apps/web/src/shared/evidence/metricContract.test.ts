import { describe, expect, it } from "vitest";

import { createMetricContract } from "./metricContract";

describe("createMetricContract", () => {
  it("keeps exact totals separate from currently loaded members", () => {
    const contract = createMetricContract({
      metricId: "market.limit-up.count", label: "严格涨停", value: "23", unit: "只",
      scope: "全市场严格涨停", status: "ready", tradeDate: "2026-08-13",
      observedAt: "2026-08-13T10:30:00+08:00", source: "tdx-local-rpc",
      formulaVersion: "strict-limit-v1", sampleCount: 5198, totalCount: 23,
      drilldownKind: "members", members: [
        { symbol: "600001", name: "样本一", reason: "严格涨停" },
        { symbol: "000001", name: "样本二", reason: "严格涨停" },
      ],
    });

    expect(contract.loadedMemberCount).toBe(2);
    expect(contract.totalCount).toBe(23);
  });

  it("rejects an aggregate metric without an explicit non-drilldown reason", () => {
    expect(() => createMetricContract({
      metricId: "market.breadth.rising", label: "上涨家数", value: "3000",
      scope: "全市场行情横截面", status: "ready", tradeDate: "2026-08-13",
      observedAt: "2026-08-13T10:30:00+08:00", source: "tdx-local-rpc",
      formulaVersion: null, sampleCount: 5198, totalCount: 3000,
      drilldownKind: "aggregate_only", members: [],
    })).toThrow(/unavailableReason/);
  });

  it("uses the honest fallback name for a member with no resolved name", () => {
    const contract = createMetricContract({
      metricId: "market.theme.symbols", label: "题材关联股票", value: "1", unit: "只",
      scope: "题材关联股票去重", status: "ready", tradeDate: "2026-08-13",
      observedAt: "2026-08-13T10:30:00+08:00", source: "local-event-store",
      formulaVersion: null, sampleCount: 1, totalCount: 1,
      drilldownKind: "members", members: [{ symbol: "600001", name: "", reason: "题材关联" }],
    });

    expect(contract.members[0].name).toBe("名称待补齐");
  });
});
