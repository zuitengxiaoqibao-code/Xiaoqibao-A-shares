export type FirstLimitUpStage =
  | "limit_up_day"
  | "waiting_pullback"
  | "pullback_window"
  | "risk_expanded"
  | "data_insufficient";

export type FirstLimitUpCandidate = {
  symbol: string;
  name: string;
  as_of: string;
  limit_up_date: string;
  limit_up_close: string;
  current_close: string;
  pe_ttm: string | null;
  limit_rate: string;
  weekly_distance_to_low: string | null;
  monthly_distance_to_low: string | null;
  weekly_bottom: boolean | null;
  monthly_bottom: boolean | null;
  pullback_pct: string;
  consolidation_days: number;
  selection_status: "qualified" | "excluded" | "data_insufficient";
  stage: FirstLimitUpStage;
  action: "no_buy" | "observe" | "staged_entry_reference" | "avoid" | "data_insufficient";
  score: string;
  reasons: string[];
  risk_flags: string[];
  sources: string[];
  entry_reference: {
    buy_steps_pct: string[];
    sell_steps_pct: string[];
    note: string;
  };
};

export type FirstLimitUpBoard = {
  asset: "a_share";
  status: "ready" | "partial" | "empty";
  as_of: string;
  rule_version: "first-limit-up-v1";
  universe_count: number;
  history_eligible_count: number;
  scan_coverage_count: number;
  coverage_complete: boolean;
  scanned_count: number;
  qualified_count: number;
  pullback_window_count: number;
  no_buy_count: number;
  today: FirstLimitUpCandidate[];
  pool: FirstLimitUpCandidate[];
  priority_symbol: string | null;
  missing_data: string[];
  sources: string[];
};
