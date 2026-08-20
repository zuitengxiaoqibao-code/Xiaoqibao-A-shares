export type RuntimeSnapshotStatus = "ready" | "partial" | "stale" | "unavailable" | "error";
export type RuntimeSnapshotFreshness = "current" | "delayed" | "stale" | "unknown";

export type RuntimeSnapshot<T> = {
  data: T | null;
  status: RuntimeSnapshotStatus;
  freshness: RuntimeSnapshotFreshness;
  observedAt: string | null;
  generatedAt: string;
  tradeDate: string | null;
  source: string;
  coverage: number | null;
  cache: { state: "live" | "hit" | "stale" | "miss"; cachedAt: string | null };
  progress: unknown | null;
  error: { code: string; message: string } | null;
  traceId: string;
};

export type ResolvedSnapshotState<T> = {
  snapshot: RuntimeSnapshot<T>;
  refreshError: string | null;
};

export function resolveSnapshotState<T>(
  current: RuntimeSnapshot<T> | null,
  incoming: RuntimeSnapshot<T>,
  isEmpty: (value: T) => boolean,
): ResolvedSnapshotState<T> {
  if (!current || current.data === null) return { snapshot: incoming, refreshError: null };
  if (incoming.status === "error" || incoming.status === "unavailable" || incoming.data === null) {
    return { snapshot: current, refreshError: incoming.error?.message ?? "最新数据暂不可用" };
  }
  if (current.tradeDate && incoming.tradeDate && incoming.tradeDate < current.tradeDate) {
    return { snapshot: current, refreshError: "新响应属于更早交易日，继续展示当前数据" };
  }
  const currentObservedAt = Date.parse(current.observedAt ?? "");
  const incomingObservedAt = Date.parse(incoming.observedAt ?? "");
  if (
    Number.isFinite(currentObservedAt)
    && Number.isFinite(incomingObservedAt)
    && incomingObservedAt < currentObservedAt
  ) {
    return { snapshot: current, refreshError: "新响应时间早于当前数据，继续展示当前数据" };
  }
  if (isEmpty(incoming.data) && !isEmpty(current.data)) {
    return { snapshot: current, refreshError: "新数据为空，继续展示上一次完整数据" };
  }
  if (current.coverage !== null && incoming.coverage !== null && incoming.coverage < current.coverage) {
    return { snapshot: current, refreshError: "新数据覆盖率较低，继续展示上一次完整数据" };
  }
  return { snapshot: incoming, refreshError: null };
}
