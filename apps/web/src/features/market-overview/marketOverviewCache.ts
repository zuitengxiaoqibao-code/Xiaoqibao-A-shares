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

function shanghaiMinutes(value: Date): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(value);
  const part = (type: string) => Number(parts.find((item) => item.type === type)?.value ?? 0);
  return part("hour") * 60 + part("minute");
}

function dayDistance(fromDay: string, toDay: string): number {
  const from = Date.parse(`${fromDay}T00:00:00Z`);
  const to = Date.parse(`${toDay}T00:00:00Z`);
  if (!Number.isFinite(from) || !Number.isFinite(to)) return Number.NaN;
  return Math.round((to - from) / 86_400_000);
}

function isBeforeOpen(value: Date): boolean {
  return shanghaiMinutes(value) < 9 * 60 + 25;
}

function isSnapshotDayUsable(snapshotDay: string, now: Date): boolean {
  const today = dayKey(now);
  if (snapshotDay === today) return true;
  const distance = dayDistance(snapshotDay, today);
  return isBeforeOpen(now) && Number.isFinite(distance) && distance >= 1 && distance <= 3;
}

export function isMarketOverviewSnapshotCurrent(value: Pick<MarketOverviewResponse, "observed_at"> | null, now = new Date()): boolean {
  if (!value?.observed_at) return false;
  const observedAt = Date.parse(value.observed_at);
  return Number.isFinite(observedAt) && isSnapshotDayUsable(dayKey(new Date(observedAt)), now);
}

export function readMarketOverviewCache(now = new Date()): { value: MarketOverviewResponse; cachedAt: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CACHE_KEY) ?? "null") as CacheEnvelope | null;
    if (!parsed || !isSnapshotDayUsable(parsed?.day ?? "", now) || !parsed.cachedAt || !isMarketOverviewSnapshotCurrent(parsed.value, now)) {
      if (parsed) window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    if (!Number.isFinite(Date.parse(parsed.cachedAt))) {
      window.localStorage.removeItem(CACHE_KEY);
      return null;
    }
    const snapshotDay = dayKey(new Date(Date.parse(parsed.value.observed_at)));
    const value = snapshotDay !== dayKey(now) && parsed.value.market_data && !parsed.value.market_data.freshness
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
