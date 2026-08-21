export type RequestLedgerStatus = "ready" | "partial" | "error" | "cancelled";

export type RequestLedgerRecord = {
  key: string;
  domain: string;
  durationMs: number;
  status: RequestLedgerStatus;
  cacheHit: boolean;
};

export type RequestLedgerSummary = {
  domain: string;
  count: number;
  failures: number;
  p50Ms: number | null;
  p95Ms: number | null;
  cacheHitRate: number | null;
  inFlight: number;
};

type RequestMetadata = Pick<RequestLedgerRecord, "domain">;

const MAX_RECORDS = 500;
const inFlight = new Map<string, Promise<unknown>>();
const records: RequestLedgerRecord[] = [];

function isCancelled(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { name?: unknown; message?: unknown };
  return candidate.name === "AbortError"
    || (typeof candidate.message === "string" && /\babort(?:ed)?\b/i.test(candidate.message));
}

function percentile(values: number[], fraction: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const rank = Math.ceil(sorted.length * fraction) - 1;
  return Math.round(sorted[Math.max(0, Math.min(rank, sorted.length - 1))]);
}

function append(record: RequestLedgerRecord): void {
  records.push({ ...record, durationMs: Math.max(0, Math.round(record.durationMs)) });
  if (records.length > MAX_RECORDS) records.splice(0, records.length - MAX_RECORDS);
}

export const requestLedger = {
  run<T>(key: string, operation: () => Promise<T> | T, metadata: RequestMetadata): Promise<T> {
    const active = inFlight.get(key);
    if (active) {
      return (active as Promise<T>).catch((error: unknown) => {
        if (!isCancelled(error)) throw error;
        return requestLedger.run(key, operation, metadata);
      });
    }

    const startedAt = typeof performance === "undefined" ? Date.now() : performance.now();
    let operationResult: Promise<T>;
    try {
      operationResult = Promise.resolve(operation());
    } catch (error) {
      operationResult = Promise.reject(error);
    }
    const promise = operationResult.then(
      (value) => {
        append({ key, domain: metadata.domain, durationMs: (typeof performance === "undefined" ? Date.now() : performance.now()) - startedAt, status: "ready", cacheHit: false });
        return value;
      },
      (error: unknown) => {
        append({ key, domain: metadata.domain, durationMs: (typeof performance === "undefined" ? Date.now() : performance.now()) - startedAt, status: isCancelled(error) ? "cancelled" : "error", cacheHit: false });
        throw error;
      },
    );
    inFlight.set(key, promise);
    promise.finally(() => {
      if (inFlight.get(key) === promise) inFlight.delete(key);
    }).catch(() => undefined);
    return promise;
  },

  record(record: RequestLedgerRecord): void {
    append(record);
  },
};

export function readRequestLedger(domain: string): RequestLedgerSummary {
  const items = records.filter((record) => record.domain === domain);
  const hits = items.filter((record) => record.cacheHit).length;
  return {
    domain,
    count: items.length,
    failures: items.filter((record) => record.status === "error").length,
    p50Ms: percentile(items.map((record) => record.durationMs), 0.5),
    p95Ms: percentile(items.map((record) => record.durationMs), 0.95),
    cacheHitRate: items.length ? Math.round((hits / items.length) * 1000) / 10 : null,
    inFlight: [...inFlight.keys()].filter((key) => key.startsWith(`${domain}:`)).length,
  };
}

export function resetRequestLedgerForTests(): void {
  inFlight.clear();
  records.length = 0;
}
