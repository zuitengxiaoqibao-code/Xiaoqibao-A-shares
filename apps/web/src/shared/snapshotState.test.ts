import { describe, expect, it } from "vitest";

import { resolveSnapshotState, type RuntimeSnapshot } from "./snapshotState";

type Payload = { rows: Array<{ id: string }> };

function snapshot(overrides: Partial<RuntimeSnapshot<Payload>> = {}): RuntimeSnapshot<Payload> {
  return {
    data: { rows: [{ id: "a" }] },
    status: "ready",
    freshness: "current",
    observedAt: "2026-08-20T10:00:00+08:00",
    generatedAt: "2026-08-20T10:00:01+08:00",
    tradeDate: "2026-08-20",
    source: "test",
    coverage: 100,
    cache: { state: "live", cachedAt: null },
    progress: null,
    error: null,
    traceId: "trace-current",
    ...overrides,
  };
}

describe("runtime snapshot arbitration", () => {
  it("keeps complete cached data when a newer response is empty", () => {
    const current = snapshot({ cache: { state: "hit", cachedAt: "2026-08-20T09:59:00+08:00" } });
    const incoming = snapshot({
      data: { rows: [] },
      status: "partial",
      observedAt: "2026-08-20T10:01:00+08:00",
      generatedAt: "2026-08-20T10:01:01+08:00",
      coverage: 0,
      traceId: "trace-empty",
    });

    const resolved = resolveSnapshotState(current, incoming, (value) => value.rows.length === 0);

    expect(resolved.snapshot).toBe(current);
    expect(resolved.refreshError).toContain("新数据为空");
  });

  it("does not let a lower-coverage response replace a complete response", () => {
    const current = snapshot({ coverage: 98 });
    const incoming = snapshot({
      data: { rows: [{ id: "b" }] },
      coverage: 42,
      observedAt: "2026-08-20T10:05:00+08:00",
      generatedAt: "2026-08-20T10:05:01+08:00",
    });

    expect(resolveSnapshotState(current, incoming, () => false).snapshot).toBe(current);
  });

  it("keeps current data and exposes the Chinese failure reason", () => {
    const current = snapshot();
    const incoming = snapshot({
      data: null,
      status: "error",
      error: { code: "source_timeout", message: "数据源连接超时" },
      observedAt: null,
      coverage: null,
    });

    const resolved = resolveSnapshotState(current, incoming, (value) => value.rows.length === 0);

    expect(resolved.snapshot).toBe(current);
    expect(resolved.refreshError).toBe("数据源连接超时");
  });

  it("accepts a newer response when coverage is not degraded", () => {
    const current = snapshot({ coverage: 80 });
    const incoming = snapshot({
      data: { rows: [{ id: "b" }] },
      coverage: 95,
      observedAt: "2026-08-20T10:05:00+08:00",
      generatedAt: "2026-08-20T10:05:01+08:00",
      traceId: "trace-new",
    });

    expect(resolveSnapshotState(current, incoming, () => false)).toEqual({
      snapshot: incoming,
      refreshError: null,
    });
  });
});
