export type LateSessionRuleSettings = {
  time_enabled: boolean;
  start_time: string;
  end_time: string;
  change_enabled: boolean;
  change_min: string | number;
  change_max: string | number;
  volume_ratio_enabled: boolean;
  volume_ratio_min: string | number;
  volume_ratio_max: string | number;
  turnover_rate_enabled: boolean;
  turnover_rate_min: string | number;
  turnover_rate_max: string | number;
  market_cap_enabled: boolean;
  market_cap_min: string | number;
  market_cap_max: string | number;
  twenty_day_limit_up_enabled: boolean;
  twenty_day_limit_up_min: number;
  twenty_day_limit_up_max: number | null;
  intraday_average_enabled: boolean;
  intraday_relation: "above" | "below" | "any";
};

export type LateSessionRule = {
  key: string;
  label: string;
  actual?: string | number | null;
  target: string;
  status: "passed" | "failed" | "unavailable" | "disabled";
  detail: string;
};

export type LateSessionAIAnalysis = {
  status: "ready" | "unconfigured" | "no_candidates" | "error";
  mode: "ai" | "rule_interpretation" | "unavailable";
  title: string;
  summary: string;
  key_points: string[];
  risk_points: string[];
  data_gaps: string[];
  candidate_count: number;
  source_evidence: string[];
  observed_at: string;
  reason: string | null;
};

export type LateSessionCandidate = {
  quote: {
    symbol: string;
    name: string;
    price: string;
    change_percent: string;
    volume_ratio: string | null;
    turnover_rate: string | null;
    market_cap_yi: string | null;
    twenty_day_limit_up_count: number | null;
    intraday_average_price: string | null;
    observed_at: string;
    source: string;
  };
  passed: boolean;
  rules: LateSessionRule[];
  behavior_tags: string[];
  risk_notes: string[];
  lifecycle_status: "strict_passed" | "near_match" | "data_pending" | "invalidated";
  first_seen_at: string | null;
  last_updated_at: string | null;
  continuous_hits: number;
  continuous_seconds: number;
  trigger_count: number;
  rule_bitmap: string;
  latest_change: string | null;
  invalidation_reason: string | null;
};

export type LateSessionBehavior = {
  key: string;
  title: string;
  level: "observe" | "risk" | "pending";
  description: string;
  evidence: string[];
};

export type LateSessionSelectionResponse = {
  status: "ready" | "partial" | "unavailable";
  trading_date: string;
  server_time: string;
  phase: "pre_screen" | "live_monitor" | "post_close";
  monitor_stage: "idle" | "precompute" | "reduce_pool" | "monitor" | "confirm" | "closing_auction" | "frozen";
  refresh_interval_ms: number;
  next_refresh_ms: number;
  source_quality: "ready" | "partial" | "stale" | "unavailable";
  universe_count: number;
  quote_count: number;
  candidate_count: number;
  rules: LateSessionRule[];
  data_state: "ready" | "partial" | "no_candidates" | "no_market_data";
  no_data_reason: string | null;
  settings: LateSessionRuleSettings;
  default_settings: LateSessionRuleSettings;
  candidates: LateSessionCandidate[];
  invalidated_candidates: LateSessionCandidate[];
  behaviors: LateSessionBehavior[];
  source_evidence: string[];
  limitations: string[];
};

export type LateSessionSelectionLoader = (settings?: LateSessionRuleSettings, onProgress?: LoadProgressCallback) => Promise<LateSessionSelectionResponse>;
export type LateSessionAIAnalysisLoader = (selection: LateSessionSelectionResponse) => Promise<LateSessionAIAnalysis>;
export type { LoadProgress };
import type { LoadProgress, LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
