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
  refresh_interval_ms: number;
  next_refresh_ms: number;
  source_quality: "ready" | "partial" | "stale" | "unavailable";
  universe_count: number;
  quote_count: number;
  candidate_count: number;
  rules: LateSessionRule[];
  settings: LateSessionRuleSettings;
  default_settings: LateSessionRuleSettings;
  candidates: LateSessionCandidate[];
  behaviors: LateSessionBehavior[];
  source_evidence: string[];
  limitations: string[];
};

export type LateSessionSelectionLoader = (settings?: LateSessionRuleSettings) => Promise<LateSessionSelectionResponse>;
