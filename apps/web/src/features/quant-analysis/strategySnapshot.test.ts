import { describe, expect, it } from "vitest";

import type { QuantStrategyDashboard } from "./types";
import { retainReadyStrategySnapshot } from "./strategySnapshot";

function dashboard(overrides: Partial<QuantStrategyDashboard> = {}): QuantStrategyDashboard {
  return {
    as_of: "2026-07-31",
    status: "partial",
    candidate_scan_state: "ready",
    metrics: { up_ratio: "66" },
    regime: { regime: "情绪主升", emotion_score: "76" },
    strategy_models: [{ name: "0轴低吸模型" }],
    candidates: [{ symbol: "600001" }],
    discipline: "只做真实触发确认。",
    sources: ["tdx-local-daily"],
    missing_data: [],
    warnings: [],
    ...overrides,
  } as unknown as QuantStrategyDashboard;
}

describe("retainReadyStrategySnapshot", () => {
  it("keeps same-day business data while carrying pending scan metadata", () => {
    const previous = dashboard();
    const incoming = dashboard({
      status: "unavailable",
      candidate_scan_state: "pending",
      candidate_scan_phase: "computing_factors",
      metrics: { up_ratio: null } as unknown as QuantStrategyDashboard["metrics"],
      regime: { regime: null, emotion_score: null } as unknown as QuantStrategyDashboard["regime"],
      strategy_models: [],
      candidates: [],
      missing_data: ["candidate_scan_pending"],
    });

    const result = retainReadyStrategySnapshot(previous, incoming);

    expect(result.metrics).toBe(previous.metrics);
    expect(result.regime).toBe(previous.regime);
    expect(result.candidates).toBe(previous.candidates);
    expect(result.candidate_scan_state).toBe("pending");
    expect(result.candidate_scan_phase).toBe("computing_factors");
    expect(result.missing_data).toEqual(["candidate_scan_pending"]);
  });

  it("replaces the snapshot when the refreshed scan is ready", () => {
    const previous = dashboard();
    const incoming = dashboard({
      candidate_scan_state: "ready",
      candidates: [{ symbol: "600002" }] as unknown as QuantStrategyDashboard["candidates"],
    });

    expect(retainReadyStrategySnapshot(previous, incoming)).toBe(incoming);
  });

  it("does not carry yesterday's payload into a new trading date", () => {
    const previous = dashboard();
    const incoming = dashboard({
      as_of: "2026-08-01",
      candidate_scan_state: "pending",
      candidates: [],
    });

    expect(retainReadyStrategySnapshot(previous, incoming)).toBe(incoming);
  });
});
