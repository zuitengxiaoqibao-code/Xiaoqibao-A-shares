export type PerfEvent = {
  domain: string;
  phase: string;
  durationMs: number;
  cacheHit: boolean;
  status: string;
  observedAt: string;
};

export type PerfSummary = {
  domain: string;
  count: number;
  p50Ms: number | null;
  p95Ms: number | null;
  cacheHitRate: number | null;
};

const MAX_EVENTS = 500;
const events: PerfEvent[] = [];

function percentile(values: number[], percentileValue: number): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const rank = Math.ceil(percentileValue * sorted.length) - 1;
  return Math.round(sorted[Math.max(0, Math.min(rank, sorted.length - 1))]);
}

export function recordPerfEvent(event: PerfEvent): void {
  if (!event.domain || !event.phase || !Number.isFinite(event.durationMs)) return;
  events.push({ ...event, durationMs: Math.max(0, Math.round(event.durationMs)) });
  if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
}

export function readPerfSummary(domain?: string): PerfSummary[] {
  const selected = domain ? events.filter((event) => event.domain === domain) : events;
  const grouped = new Map<string, PerfEvent[]>();
  selected.forEach((event) => grouped.set(event.domain, [...(grouped.get(event.domain) ?? []), event]));
  return [...grouped.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([name, items]) => {
    const hits = items.filter((event) => event.cacheHit).length;
    return {
      domain: name,
      count: items.length,
      p50Ms: percentile(items.map((event) => event.durationMs), 0.5),
      p95Ms: percentile(items.map((event) => event.durationMs), 0.95),
      cacheHitRate: Math.round((hits / items.length) * 1000) / 10,
    };
  });
}

export function resetPerfLedgerForTests(): void {
  events.length = 0;
}

