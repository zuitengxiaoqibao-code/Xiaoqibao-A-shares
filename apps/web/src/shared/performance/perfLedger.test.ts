import { describe, expect, it, beforeEach } from "vitest";
import { readPerfSummary, recordPerfEvent, resetPerfLedgerForTests } from "./perfLedger";

describe("perfLedger", () => {
  beforeEach(() => resetPerfLedgerForTests());

  it("summarizes bounded domain timings and cache hit rate", () => {
    recordPerfEvent({ domain: "overview", phase: "latest", durationMs: 10, cacheHit: true, status: "ready", observedAt: "2026-08-13T01:00:00.000Z" });
    recordPerfEvent({ domain: "overview", phase: "latest", durationMs: 30, cacheHit: false, status: "partial", observedAt: "2026-08-13T01:00:01.000Z" });
    recordPerfEvent({ domain: "overview", phase: "latest", durationMs: 50, cacheHit: false, status: "ready", observedAt: "2026-08-13T01:00:02.000Z" });

    expect(readPerfSummary("overview")).toEqual([
      { domain: "overview", count: 3, p50Ms: 30, p95Ms: 50, cacheHitRate: 33.3 },
    ]);
  });

  it("returns no summary for an unknown domain", () => {
    expect(readPerfSummary("missing")).toEqual([]);
  });

  it("keeps only the latest 500 events", () => {
    for (let index = 0; index < 501; index += 1) {
      recordPerfEvent({ domain: index === 0 ? "old" : "new", phase: "load", durationMs: index, cacheHit: false, status: "ready", observedAt: new Date(index).toISOString() });
    }
    expect(readPerfSummary("old")).toEqual([]);
    expect(readPerfSummary("new")[0]?.count).toBe(500);
  });
});
