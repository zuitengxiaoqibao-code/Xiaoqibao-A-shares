export type VerificationState = "verified" | "multi_source_confirmed" | "pending" | "unverified";
export type AlertUrgency = "breaking" | "tracking" | "normal";
export type AssociationKind = "direct" | "context" | "theme" | "macro";
export type ImpactDirection = "positive" | "negative" | "neutral" | "uncertain";

export interface BreakingNewsAlert {
  event_id: string;
  headline: string;
  occurred_at: string;
  verification_state: VerificationState;
  urgency: AlertUrgency;
  association_kind: AssociationKind;
  association_reasons: string[];
  affected_symbols: string[];
  themes: string[];
  publishers: string[];
  source_urls: string[];
  source_count: number;
  impact_direction: ImpactDirection;
  impact_confidence: string | null;
  ai_degraded: boolean;
}

export interface BreakingNewsAlertResponse {
  status: "ready" | "empty";
  observed_at: string;
  alerts: BreakingNewsAlert[];
  sources: string[];
  warnings: string[];
}

export type BreakingNewsAlertLoader = (
  symbol?: string | null,
  signal?: AbortSignal,
  limit?: number,
) => Promise<BreakingNewsAlertResponse>;
