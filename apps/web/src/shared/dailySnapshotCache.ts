import { shanghaiDay } from "./tradingDayContext";
import { recordPerfEvent } from "./performance/perfLedger";

const CACHE_PREFIX = "qibao.daily-snapshot.v1";
const MAX_SCOPE_ENTRIES = 12;
export const DAILY_SNAPSHOT_UPDATED_EVENT = "qibao:daily-snapshot-updated";

type CacheEnvelope<T> = {
  schemaVersion?: number;
  symbol: string;
  day: string;
  cachedAt: string;
  sourceCutoff?: string | null;
  completeness?: "complete" | "partial";
  value: T;
};

type SnapshotWriteOptions = {
  sourceCutoff?: string | null;
  completeness?: "complete" | "partial";
};

export type DailySnapshotHit<T> = {
  value: T;
  cachedAt: string;
};

export type DailySnapshotMetadata = {
  sourceCutoff: string | null;
  completeness: "complete" | "partial";
  day: string;
};

export type DailySnapshotListItem<T> = DailySnapshotHit<T> & {
  symbol: string;
};

export { shanghaiDay } from "./tradingDayContext";

function scopePrefix(scope: string): string {
  return `${CACHE_PREFIX}.${scope}.`;
}

function cacheKey(scope: string, day: string, symbol: string): string {
  return `${scopePrefix(scope)}${day}.${symbol}`;
}

function readEnvelope<T>(scope: string, symbol: string, now: Date): CacheEnvelope<T> | null {
  const day = shanghaiDay(now);
  try {
    removeOtherDays(scope, day);
    const raw = localStorage.getItem(cacheKey(scope, day, symbol));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    const valueSymbol = (parsed?.value as { symbol?: unknown } | null)?.symbol;
    if (
      parsed?.symbol !== symbol || parsed.day !== day || typeof parsed.cachedAt !== "string" ||
      parsed.completeness === "partial" || valueSymbol !== symbol
    ) return null;
    return parsed;
  } catch {
    return null;
  }
}

function scopeKeys(scope: string): string[] {
  const prefix = scopePrefix(scope);
  const keys: string[] = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    if (key?.startsWith(prefix)) keys.push(key);
  }
  return keys;
}

function removeOtherDays(scope: string, day: string): void {
  const prefix = scopePrefix(scope);
  for (const key of scopeKeys(scope)) {
    const rest = key.slice(prefix.length);
    if (!rest.startsWith(`${day}.`)) localStorage.removeItem(key);
  }
}

function trimScope(scope: string): void {
  const entries = scopeKeys(scope).flatMap((key) => {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) ?? "null") as CacheEnvelope<unknown> | null;
      if (!parsed?.cachedAt) return [{ key, timestamp: Number.NEGATIVE_INFINITY }];
      return [{ key, timestamp: Date.parse(parsed.cachedAt) }];
    } catch {
      return [{ key, timestamp: Number.NEGATIVE_INFINITY }];
    }
  }).sort((left, right) => right.timestamp - left.timestamp);

  for (const entry of entries.slice(MAX_SCOPE_ENTRIES)) localStorage.removeItem(entry.key);
}

export function readDailySnapshot<T>(
  scope: string,
  symbol: string,
  now = new Date(),
): DailySnapshotHit<T> | null {
  const day = shanghaiDay(now);
  try {
    removeOtherDays(scope, day);
    const key = cacheKey(scope, day, symbol);
    const raw = localStorage.getItem(key);
    if (!raw) {
      recordPerfEvent({ domain: scope, phase: "cache-read", durationMs: 0, cacheHit: false, status: "miss", observedAt: now.toISOString() });
      return null;
    }
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    const valueSymbol = (parsed?.value as { symbol?: unknown } | null)?.symbol;
    if (
      parsed?.symbol !== symbol
      || parsed.day !== day
      || typeof parsed.cachedAt !== "string"
      || parsed.completeness === "partial"
      || valueSymbol !== symbol
    ) {
      localStorage.removeItem(key);
      return null;
    }
    recordPerfEvent({ domain: scope, phase: "cache-read", durationMs: 0, cacheHit: true, status: "ready", observedAt: now.toISOString() });
    return { value: parsed.value, cachedAt: parsed.cachedAt };
  } catch {
    recordPerfEvent({ domain: scope, phase: "cache-read", durationMs: 0, cacheHit: false, status: "error", observedAt: now.toISOString() });
    localStorage.removeItem(cacheKey(scope, day, symbol));
    return null;
  }
}

export function readDailySnapshotMetadata(
  scope: string,
  symbol: string,
  now = new Date(),
): DailySnapshotMetadata | null {
  const envelope = readEnvelope<unknown>(scope, symbol, now);
  if (!envelope) return null;
  return {
    sourceCutoff: envelope.sourceCutoff ?? null,
    completeness: envelope.completeness ?? "complete",
    day: envelope.day,
  };
}

export function listDailySnapshots<T>(
  scope: string,
  now = new Date(),
): DailySnapshotListItem<T>[] {
  const day = shanghaiDay(now);
  removeOtherDays(scope, day);
  const entries: DailySnapshotListItem<T>[] = [];
  for (const key of scopeKeys(scope)) {
    try {
      const raw = localStorage.getItem(key);
      const parsed = JSON.parse(raw ?? "null") as CacheEnvelope<T> | null;
      const valueSymbol = (parsed?.value as { symbol?: unknown } | null)?.symbol;
      if (
        !parsed
        || parsed.day !== day
        || typeof parsed.symbol !== "string"
        || typeof parsed.cachedAt !== "string"
        || parsed.completeness === "partial"
        || valueSymbol !== parsed.symbol
        || !Number.isFinite(Date.parse(parsed.cachedAt))
      ) {
        localStorage.removeItem(key);
        continue;
      }
      entries.push({ symbol: parsed.symbol, cachedAt: parsed.cachedAt, value: parsed.value });
    } catch {
      localStorage.removeItem(key);
    }
  }
  return entries.sort((left, right) => Date.parse(right.cachedAt) - Date.parse(left.cachedAt));
}

export function writeDailySnapshot<T>(
  scope: string,
  symbol: string,
  value: T,
  now = new Date(),
  options: SnapshotWriteOptions = {},
): DailySnapshotHit<T> {
  const day = shanghaiDay(now);
  const cachedAt = now.toISOString();
  const completeness = options.completeness ?? "complete";
  const envelope: CacheEnvelope<T> = {
    schemaVersion: 2,
    symbol,
    day,
    cachedAt,
    sourceCutoff: options.sourceCutoff ?? null,
    completeness,
    value,
  };
  try {
    removeOtherDays(scope, day);
    const key = cacheKey(scope, day, symbol);
    if (completeness === "partial") {
      const current = localStorage.getItem(key);
      if (current) {
        const parsed = JSON.parse(current) as CacheEnvelope<T>;
        if ((parsed.completeness ?? "complete") === "complete") {
          return { value: parsed.value, cachedAt: parsed.cachedAt };
        }
      }
    }
    localStorage.setItem(key, JSON.stringify(envelope));
    trimScope(scope);
    window.dispatchEvent(new CustomEvent(DAILY_SNAPSHOT_UPDATED_EVENT, { detail: { scope, symbol } }));
  } catch {
    // A cache write must never make fresh API data unavailable to the page.
  }
  return { value, cachedAt };
}
