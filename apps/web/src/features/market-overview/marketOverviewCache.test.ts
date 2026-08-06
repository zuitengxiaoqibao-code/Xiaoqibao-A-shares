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

  it("drops a snapshot from a previous trading day instead of showing stale market numbers", () => {
    writeMarketOverviewCache({ ...payload, observed_at: "2026-08-05T15:00:00+08:00" }, new Date("2026-08-05T15:00:00+08:00"));
    expect(readMarketOverviewCache(new Date("2026-08-06T09:30:00+08:00"))).toBeNull();
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
    expect(isMarketOverviewSnapshotCurrent(payload, new Date("2026-08-07T00:01:00+08:00"))).toBe(false);
  });
});
