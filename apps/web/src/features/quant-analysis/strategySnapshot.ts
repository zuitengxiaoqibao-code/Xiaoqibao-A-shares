import type { QuantStrategyDashboard } from "./types";

/**
 * Candidate scans are intentionally deferred by the API. During a scan the
 * response contains fresh progress metadata but an empty/incomplete payload.
 * Keep the last same-day ready payload visible until the new scan is ready.
 */
export function retainReadyStrategySnapshot(
  previous: QuantStrategyDashboard | null,
  incoming: QuantStrategyDashboard,
): QuantStrategyDashboard {
  if (
    previous === null
    || previous.as_of !== incoming.as_of
    || previous.candidate_scan_state !== "ready"
    || incoming.candidate_scan_state === "ready"
  ) {
    return incoming;
  }

  return {
    ...incoming,
    status: previous.status,
    metrics: previous.metrics,
    regime: previous.regime,
    strategy_models: previous.strategy_models,
    candidates: previous.candidates,
    discipline: previous.discipline,
    sources: previous.sources,
    missing_data: Array.from(new Set([...previous.missing_data, ...incoming.missing_data])),
    warnings: Array.from(new Set([...previous.warnings, ...incoming.warnings])),
  };
}
