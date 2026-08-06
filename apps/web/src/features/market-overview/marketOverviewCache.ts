import type { MarketOverviewResponse } from "./types";

const CACHE_KEY = "yishu.market-overview.daily.v1";

type CacheEnvelope = {
  day: string;
  cachedAt: string;
  value: MarketOverviewResponse;
};

function dayKey(value: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "00";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function isMarketOverviewSnapshotCurrent(value: Pick<MarketOverviewResponse, "observed_at"> | null, now = new Date()): boolean {
  if (!value?.observed_at) return false;
  const observedAt = Date.parse(value.observed_at);
  return Number.isFinite(observedAt) && dayKey(new Date(observedAt)) === dayKey(now);
}

export function readMarketOverviewCache(now = new Date()): { value: MarketOverviewResponse; cachedAt: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CACHE_KEY) ?? "null") as CacheEnvelope | null;
    if (!parsed || parsed.day !== dayKey(now) || !parsed.cachedAt || !isMarketOverviewSnapshotCurrent(parsed.value, now)) {
      if (parsed) window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    if (!Number.isFinite(Date.parse(parsed.cachedAt))) {
      window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return { value: parsed.value, cachedAt: parsed.cachedAt };
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
      const snapshotDay = dayKey(new Date(observedAt));
      const envelope: CacheEnvelope = { day: snapshotDay, cachedAt, value };
      window.localStorage.setItem(CACHE_KEY, JSON.stringify(envelope));
      persisted = true;
    } catch {
      // Cache failure must never block the live snapshot.
    }
  }
  return { value, cachedAt, persisted };
}
