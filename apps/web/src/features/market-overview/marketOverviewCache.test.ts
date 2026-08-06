import { beforeEach, describe, expect, it, vi } from "vitest";

import { isMarketOverviewSnapshotCurrent, readMarketOverviewCache, writeMarketOverviewCache } from "./marketOverviewCache";
import type { MarketOverviewResponse } from "./types";

const payload = { status: "ready", observed_at: "2026-08-06T10:00:00+08:00" } as MarketOverviewResponse;

describe("market overview cache", () => {
  beforeEach(() => localStorage.clear());

  it("stores and restores a same-day snapshot with cache time", () => {
    writeMarketOverviewCache(payload, new Date("2026-08-06T10:01:00+08:00"));
    expect(readMarketOverviewCache(new Date("2026-08-06T10:03:00+08:00"))).toEqual({
      value: payload,
      cachedAt: "2026-08-06T02:01:00.000Z",
    });
  });

  it("keeps the previous close before open but drops it once the session starts", () => {
    writeMarketOverviewCache({ ...payload, observed_at: "2026-08-05T15:00:00+08:00" }, new Date("2026-08-05T15:00:00+08:00"));
    expect(readMarketOverviewCache(new Date("2026-08-06T09:20:00+08:00"))?.value.observed_at).toBe("2026-08-05T15:00:00+08:00");
    expect(readMarketOverviewCache(new Date("2026-08-06T09:30:00+08:00"))).toBeNull();
  });

  it("upgrades an older premarket cache with explicit previous-close metadata", () => {
    const legacy = {
      ...payload,
      observed_at: "2026-08-05T15:00:00+08:00",
      market_data: {
        source: "tdx-local-rpc", quality: "ready", observed_at: "2026-08-05T15:00:00+08:00",
        quote_count: 5100, universe_count: 5200,
      },
    } as MarketOverviewResponse;
    writeMarketOverviewCache(legacy, new Date("2026-08-05T15:01:00+08:00"));

    const restored = readMarketOverviewCache(new Date("2026-08-06T08:30:00+08:00"));

    expect(restored?.value.market_data.phase).toBe("premarket");
    expect(restored?.value.market_data.freshness).toBe("previous_close");
  });

  it("drops a snapshot with an invalid observation timestamp", () => {
    writeMarketOverviewCache({ ...payload, observed_at: "not-a-date" }, new Date("2026-08-06T10:01:00+08:00"));
    expect(readMarketOverviewCache(new Date("2026-08-06T10:03:00+08:00"))).toBeNull();
  });

  it("reports when browser storage refuses a write", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
    expect(writeMarketOverviewCache(payload, new Date("2026-08-06T10:01:00+08:00")).persisted).toBe(false);
    setItem.mockRestore();
  });

  it("recognizes the Shanghai trading day of a snapshot", () => {
    expect(isMarketOverviewSnapshotCurrent(payload, new Date("2026-08-06T23:59:00+08:00"))).toBe(true);
    expect(isMarketOverviewSnapshotCurrent(payload, new Date("2026-08-07T00:01:00+08:00"))).toBe(true);
    expect(isMarketOverviewSnapshotCurrent(payload, new Date("2026-08-07T09:30:00+08:00"))).toBe(false);
  });
});
