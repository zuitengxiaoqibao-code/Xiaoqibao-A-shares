import { describe, expect, it } from "vitest";

import { createInstrumentDirectory } from "./instrumentDirectory";

const items = [
  { symbol: "600519", name: "贵州茅台", short_name: "茅台", historical_names: ["贵州茅台酒"], search_aliases: ["gzmt", "maotai"], exchange: "sh" as const, observed_at: "2026-08-13T09:30:00+08:00", quote_quality: "ready" as const, industry: "白酒", sectors: ["消费"], trading_status: "active" as const },
  { symbol: "000001", name: "平安银行", short_name: null, historical_names: [], search_aliases: ["payh"], exchange: "sz" as const, observed_at: "2026-08-13T09:30:00+08:00", quote_quality: "ready" as const, industry: "银行", sectors: [], trading_status: "active" as const },
];

describe("instrument directory", () => {
  it("searches code, Chinese name and precomputed aliases synchronously", () => {
    const directory = createInstrumentDirectory(items);
    expect(directory.search("6005").map((item) => item.symbol)).toEqual(["600519"]);
    expect(directory.search("贵州").map((item) => item.symbol)).toEqual(["600519"]);
    expect(directory.search("gzmt").map((item) => item.symbol)).toEqual(["600519"]);
    expect(directory.search("payh").map((item) => item.symbol)).toEqual(["000001"]);
  });

  it("prefers exact code and exact name over partial matches", () => {
    const directory = createInstrumentDirectory(items);
    expect(directory.search("600519")[0].symbol).toBe("600519");
    expect(directory.search("贵州茅台")[0].symbol).toBe("600519");
  });
});
