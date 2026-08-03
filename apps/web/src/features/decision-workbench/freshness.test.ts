import { describe, expect, it } from "vitest";

import { livePhaseFreshness } from "./freshness";
import type { DecisionResponse } from "./types";

const polling: DecisionResponse["polling"] = {
  status: "normal",
  focus_interval_seconds: 60,
  universe_interval_seconds: 240,
  stale_after_seconds: 180,
  next_check_seconds: 60,
  last_focus_success_at: "2026-07-15T10:29:30+08:00",
  last_universe_success_at: "2026-07-15T10:22:30+08:00",
};

function input(overrides: Partial<Parameters<typeof livePhaseFreshness>[0]> = {}) {
  return {
    phase: "intraday" as const,
    marketSession: "open" as const,
    serverTime: "2026-07-15T10:30:00+08:00",
    generatedAt: "2026-07-15T10:00:00+08:00",
    selectedSymbol: undefined,
    polling,
    ...overrides,
  };
}

describe("livePhaseFreshness", () => {
  it("uses the universe success timestamp and twice its interval for market-wide advice", () => {
    expect(livePhaseFreshness(input())).toEqual({
      status: "fresh",
      scope: "universe",
      referenceAt: "2026-07-15T10:22:30+08:00",
      referenceSource: "poll_success",
      thresholdSeconds: 480,
    });
  });

  it("uses the focus success timestamp when a stock is selected", () => {
    expect(livePhaseFreshness(input({ selectedSymbol: "600000" }))).toEqual({
      status: "fresh",
      scope: "focus",
      referenceAt: "2026-07-15T10:29:30+08:00",
      referenceSource: "poll_success",
      thresholdSeconds: 180,
    });
  });

  it("marks only the relevant scope stale", () => {
    const result = livePhaseFreshness(input({
      selectedSymbol: "600000",
      polling: { ...polling, last_focus_success_at: "2026-07-15T10:26:00+08:00" },
    }));

    expect(result.status).toBe("stale");
    expect(result.scope).toBe("focus");
    expect(result.referenceAt).toBe("2026-07-15T10:26:00+08:00");
  });

  it("falls back to the phase generation time before the first successful poll", () => {
    expect(livePhaseFreshness(input({
      polling: { ...polling, last_universe_success_at: null },
      generatedAt: "2026-07-15T10:29:00+08:00",
    }))).toMatchObject({
      status: "fresh",
      scope: "universe",
      referenceAt: "2026-07-15T10:29:00+08:00",
      referenceSource: "generated_at",
    });
  });

  it("does not apply live freshness outside an open intraday phase", () => {
    expect(livePhaseFreshness(input({ phase: "premarket" })).status).toBe("not_applicable");
    expect(livePhaseFreshness(input({ marketSession: "closed" })).status).toBe("not_applicable");
  });

  it("does not turn invalid or unavailable timestamps into a stale warning", () => {
    expect(livePhaseFreshness(input({ serverTime: "invalid" })).status).toBe("uninitialized");
    expect(livePhaseFreshness(input({
      polling: { ...polling, last_universe_success_at: null }, generatedAt: undefined,
    })).status).toBe("uninitialized");
  });
});
