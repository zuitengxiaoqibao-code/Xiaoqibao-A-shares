const CACHE_PREFIX = "qibao.daily-snapshot.v1";
const MAX_SCOPE_ENTRIES = 12;
export const DAILY_SNAPSHOT_UPDATED_EVENT = "qibao:daily-snapshot-updated";

type CacheEnvelope<T> = {
  symbol: string;
  day: string;
  cachedAt: string;
  value: T;
};

export type DailySnapshotHit<T> = {
  value: T;
  cachedAt: string;
};

export type DailySnapshotListItem<T> = DailySnapshotHit<T> & {
  symbol: string;
};

function localDay(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function scopePrefix(scope: string): string {
  return `${CACHE_PREFIX}.${scope}.`;
}

function cacheKey(scope: string, day: string, symbol: string): string {
  return `${scopePrefix(scope)}${day}.${symbol}`;
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
  const day = localDay(now);
  try {
    removeOtherDays(scope, day);
    const key = cacheKey(scope, day, symbol);
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    const valueSymbol = (parsed?.value as { symbol?: unknown } | null)?.symbol;
    if (
      parsed?.symbol !== symbol
      || parsed.day !== day
      || typeof parsed.cachedAt !== "string"
      || valueSymbol !== symbol
    ) {
      localStorage.removeItem(key);
      return null;
    }
    return { value: parsed.value, cachedAt: parsed.cachedAt };
  } catch {
    localStorage.removeItem(cacheKey(scope, day, symbol));
    return null;
  }
}

export function listDailySnapshots<T>(
  scope: string,
  now = new Date(),
): DailySnapshotListItem<T>[] {
  const day = localDay(now);
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
): DailySnapshotHit<T> {
  const day = localDay(now);
  const cachedAt = now.toISOString();
  const envelope: CacheEnvelope<T> = { symbol, day, cachedAt, value };
  try {
    removeOtherDays(scope, day);
    localStorage.setItem(cacheKey(scope, day, symbol), JSON.stringify(envelope));
    trimScope(scope);
    window.dispatchEvent(new CustomEvent(DAILY_SNAPSHOT_UPDATED_EVENT, { detail: { scope, symbol } }));
  } catch {
    // A cache write must never make fresh API data unavailable to the page.
  }
  return { value, cachedAt };
}
