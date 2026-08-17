export type LateSessionRule = {
  key: string;
  label: string;
  actual?: string | number | null;
  target: string;
  status: "passed" | "failed" | "unavailable";
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
  candidates: LateSessionCandidate[];
  behaviors: LateSessionBehavior[];
  source_evidence: string[];
  limitations: string[];
};

export type LateSessionSelectionLoader = () => Promise<LateSessionSelectionResponse>;
