export type EvidenceStatus = "ready" | "partial" | "stale" | "unavailable" | "error";

export type EvidenceState = {
  status: EvidenceStatus;
  source: string;
  observedAt: string | null;
  coverage: number | null;
  warnings: string[];
};

export type MetricTone = "up" | "down" | "warning" | "live" | "neutral" | "unavailable";

export type MetricItem = {
  label: string;
  value: number | string | null;
  tone?: MetricTone;
  detail?: string;
};

export type RankItem = {
  label: string;
  value: number | null;
  detail?: string;
};
