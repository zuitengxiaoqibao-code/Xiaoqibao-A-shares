import type { CandidateBoard } from "../a-shares/types";
import type { Advice, DecisionPhase, PhaseExecution } from "../decision-workbench/types";
import type { FieldEvidence } from "../../shared/evidence/FieldEvidenceDetails";

export type AShareInstrument = {
  symbol: string;
  name: string;
  exchange: "sh" | "sz" | "bj";
  observed_at: string;
  quote_quality: "ready" | "stale" | "unavailable";
  short_name?: string | null;
  historical_names?: string[];
  search_aliases?: string[];
  industry?: string | null;
  sectors?: string[];
  trading_status?: "active" | "suspended" | "delisted" | "unknown";
};

export type InstrumentSearchResponse = {
  query: string;
  items: AShareInstrument[];
  server_time: string;
  source_status: "ready" | "unavailable";
};

export type InstrumentDirectoryResponse = {
  items: AShareInstrument[];
  observed_at: string | null;
  count: number;
};

export type CockpitSection = {
  status: "ready" | "partial" | "stale" | "unavailable" | "blocked";
  source: string;
  observed_at: string | null;
  snapshot_id: string | null;
  reason: string | null;
  payload: Record<string, unknown>;
};

export type AssessmentEvidence = {
  evidence_id: string;
  source: string;
  snapshot_id: string;
  summary: string;
  observed_at: string;
};

export type StockAssessment = {
  assessment_id: string;
  symbol: string;
  action: "observe" | "wait" | "avoid";
  conclusion: string;
  confidence: string;
  supporting_evidence: AssessmentEvidence[];
  contrary_evidence: AssessmentEvidence[];
  risks: string[];
  invalidation_conditions: string[];
  generated_at: string;
};

export type AssessmentAIStatus = "ready" | "unconfigured" | "deferred" | "timeout" | "http_error" | "invalid";

export type AssessmentAIExplanation = {
  plain_language: string;
  news_impact: string;
  hotspot_attribution: string;
  uncertainty: string;
  contrary_view: string;
  evidence_ids: string[];
};

export type PreparationSource = {
  name: "quote" | "history" | "finance" | "news" | "classification" | "fund_flow";
  status: "ready" | "partial";
  observed_at: string | null;
  reason: string | null;
};

export type StockPreparation = {
  symbol: string;
  status: "ready" | "partial";
  sources: PreparationSource[];
  refreshed: boolean;
  started_at: string;
  completed_at: string;
};

export type StockCockpitSnapshot = {
  symbol: string;
  as_of: string;
  cutoff: string;
  overall_quality: "ready" | "partial" | "blocked";
  instrument: AShareInstrument;
  preparation?: StockPreparation;
  candidate_membership: Array<"short_term" | "swing">;
  assessment: StockAssessment;
  ai_status: AssessmentAIStatus;
  ai_explanation: AssessmentAIExplanation | null;
  current_advice: Advice[];
  sections: Record<string, CockpitSection>;
  phases: Record<DecisionPhase, StockPhaseHistory>;
  field_evidence?: FieldEvidence[];
};

export type StockQuotePulse = {
  symbol: string;
  name: string;
  price: string | number | null;
  previous_close: string | number | null;
  change: string | number | null;
  change_percent: string | number | null;
  volume: string | number | null;
  turnover_rate: string | number | null;
  market_cap_yi: string | number | null;
  observed_at: string | null;
  fetched_at: string;
  source: string;
  status: "ready" | "stale" | "unavailable";
  freshness: "live" | "stale" | "unavailable";
  age_seconds: number | null;
  reason: string | null;
};

export type DecisionVersion = {
  snapshot_id: string;
  sequence: number;
  generated_at: string;
  status: "ready" | "partial" | "blocked";
};

export type StockPhaseHistory = {
  advice: Advice[];
  change_stream: DecisionVersion[];
  execution?: PhaseExecution | null;
  phase_status?: "empty" | "ready" | "partial" | "blocked";
  quality_reasons?: string[];
};

export type CandidateLoader = () => Promise<CandidateBoard>;
