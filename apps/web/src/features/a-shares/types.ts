export type FactorSnapshot = {
  symbol: string; as_of: string; latest_trade_date?: string | null; close: string;
  return_5d: string; return_20d: string;
  distance_ma20: string; volume_ratio_5_20: string; volatility_20d: string;
  drawdown_60d: string; liquidity_amount_20d: string; factor_version: string;
  source: string;
};

export type CandidateEntry = {
  symbol: string; horizon: "short_term" | "swing"; score: string;
  score_breakdown: Record<string, string>; factor_snapshot: FactorSnapshot;
};

export type CandidateBoard = {
  asset: "a_share"; snapshot_id: string | null; input_snapshot_hash: string | null;
  universe_status: "ready" | "empty"; as_of: string; factor_version: string; short_term: CandidateEntry[];
  universe_size?: number; eligible_size?: number; latest_trade_date?: string | null;
  sources?: string[]; refresh_policy?: "after_close";
  swing: CandidateEntry[];
  exclusions: Array<{
    symbol: string; reason_code: "insufficient_liquidity" | "invalid_history" | "stale_history";
    observed_value: string | null; threshold: string | null; detail: string | null;
  }>;
};

export type CandidateScoreItem = {
  symbol: string;
  status: "ready" | "insufficient_history" | "insufficient_liquidity" | "invalid_history" | "stale_history";
  score: string | null;
  latest_trade_date: string | null;
  reason: "history_requires_60_bars" | "liquidity_below_threshold" | "history_invalid" | "history_not_through_confirmed_day" | null;
};

export type CandidateScoreBoard = {
  as_of: string; horizon: "short_term" | "swing"; factor_version: string;
  universe_size: number; eligible_size: number; latest_trade_date: string | null;
  sources: string[]; items: CandidateScoreItem[];
};

export type CandidateScoreLoader = (
  symbols: string[], horizon?: "short_term" | "swing",
) => Promise<CandidateScoreBoard>;

export type DiagnosisSection = {
  status: "ready" | "unavailable"; observed_at: string | null; source: string;
  metrics: Record<string, string | number | null>; evidence_ids: string[];
  explanation: string;
};

export type AShareDiagnosis = {
  asset: "a_share"; snapshot_id: string | null; input_snapshot_hash: string | null;
  symbol: string; as_of: string; action: "observe" | "blocked";
  overall_status: "ready" | "partial"; sections: Record<string, DiagnosisSection>;
  missing_data: string[]; factor_version: string;
};
