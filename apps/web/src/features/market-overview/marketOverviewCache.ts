import type { MarketOverviewResponse } from "./types";
import { isUsableSnapshotDay, marketPhase, shanghaiDay } from "../../shared/tradingDayContext";

const CACHE_KEY = "yishu.market-overview.daily.v1";

type CacheEnvelope = {
  day: string;
  cachedAt: string;
  value: MarketOverviewResponse;
};

export function isMarketOverviewSnapshotCurrent(value: Pick<MarketOverviewResponse, "observed_at"> | null, now = new Date()): boolean {
  if (!value?.observed_at) return false;
  const observedAt = Date.parse(value.observed_at);
  return Number.isFinite(observedAt) && isUsableSnapshotDay(shanghaiDay(new Date(observedAt)), now);
}

export function readMarketOverviewCache(now = new Date()): { value: MarketOverviewResponse; cachedAt: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CACHE_KEY) ?? "null") as CacheEnvelope | null;
    if (!parsed || !isUsableSnapshotDay(parsed?.day ?? "", now) || !parsed.cachedAt || !isMarketOverviewSnapshotCurrent(parsed.value, now)) {
      if (parsed) window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    if (!Number.isFinite(Date.parse(parsed.cachedAt))) {
      window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    const snapshotDay = shanghaiDay(new Date(Date.parse(parsed.value.observed_at)));
    const value = snapshotDay !== shanghaiDay(now) && parsed.value.market_data && !parsed.value.market_data.freshness
      ? {
          ...parsed.value,
          market_data: { ...parsed.value.market_data, phase: "premarket" as const, freshness: "previous_close" as const },
        }
      : parsed.value;
    return { value, cachedAt: parsed.cachedAt };
  } catch {
    window.localStorage.removeItem(CACHE_KEY);
    return null;
  }
}

export function writeMarketOverviewCache(value: MarketOverviewResponse, now = new Date()): { value: MarketOverviewResponse; cachedAt: string; persisted: boolean } {
  const cachedAt = now.toISOString();
  let persisted = false;
  if (typeof window !== "undefined") {
    try {
      const observedAt = Date.parse(value.observed_at);
      if (!Number.isFinite(observedAt)) return { value, cachedAt, persisted };
      const snapshotDay = shanghaiDay(new Date(observedAt));
      const envelope: CacheEnvelope = { day: snapshotDay, cachedAt, value };
      window.localStorage.setItem(CACHE_KEY, JSON.stringify(envelope));
      persisted = true;
    } catch {
      // Cache failure must never block the live snapshot.
    }
  }
  return { value, cachedAt, persisted };
}
