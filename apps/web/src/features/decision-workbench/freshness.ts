import type { DecisionPhase, DecisionResponse } from "./types";

export type LivePhaseFreshness = {
  status: "fresh" | "stale" | "uninitialized" | "not_applicable";
  scope: "focus" | "universe" | null;
  referenceAt: string | null;
  referenceSource: "poll_success" | "generated_at" | null;
  thresholdSeconds: number | null;
};

type LivePhaseFreshnessInput = {
  phase: DecisionPhase;
  marketSession: DecisionResponse["market_session"];
  serverTime: string;
  generatedAt?: string;
  selectedSymbol?: string | null;
  polling: DecisionResponse["polling"];
};

export function livePhaseFreshness(_input: LivePhaseFreshnessInput): LivePhaseFreshness {
  const input = _input;
  if (input.phase !== "intraday" || input.marketSession !== "open") {
    return {
      status: "not_applicable", scope: null, referenceAt: null,
      referenceSource: null, thresholdSeconds: null,
    };
  }

  const scope = input.selectedSymbol?.trim() ? "focus" : "universe";
  const interval = scope === "focus"
    ? input.polling.focus_interval_seconds
    : input.polling.universe_interval_seconds;
  const successAt = scope === "focus"
    ? input.polling.last_focus_success_at
    : input.polling.last_universe_success_at;
  const staleAfter = input.polling.stale_after_seconds;
  const validStaleAfter = Number.isFinite(staleAfter) && staleAfter >= 0;
  const validInterval = interval !== null && Number.isFinite(interval) && interval >= 0;
  if (!validStaleAfter) {
    return {
      status: "uninitialized", scope, referenceAt: null,
      referenceSource: null, thresholdSeconds: null,
    };
  }

  const thresholdSeconds = Math.max(staleAfter, validInterval ? interval * 2 : staleAfter);
  const referenceAt = successAt ?? input.generatedAt ?? null;
  const referenceSource = successAt ? "poll_success" : referenceAt ? "generated_at" : null;
  const serverTimestamp = Date.parse(input.serverTime);
  const referenceTimestamp = referenceAt ? Date.parse(referenceAt) : Number.NaN;
  if (!referenceAt || !Number.isFinite(serverTimestamp) || !Number.isFinite(referenceTimestamp)) {
    return { status: "uninitialized", scope, referenceAt, referenceSource, thresholdSeconds };
  }

  return {
    status: serverTimestamp - referenceTimestamp > thresholdSeconds * 1000 ? "stale" : "fresh",
    scope, referenceAt, referenceSource, thresholdSeconds,
  };
}
