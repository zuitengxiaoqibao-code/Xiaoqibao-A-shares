import type { FieldEvidence } from "../../shared/evidence/FieldEvidenceDetails";

export type IntradayTick = {
  symbol: string;
  price: string;
  change: string;
  change_percent: string;
  volume: string;
  source: string;
  observed_at: string;
  fetched_at: string;
  quality: "ready" | "partial" | "blocked";
  source_snapshot_id: string;
};

export type QuantTickLoader = (
  symbol: string,
  tradingDate?: string,
) => Promise<IntradayTick[]>;

export type KronosForecastStatus = "ready" | "unavailable" | "insufficient" | "error";

export type KronosForecastResponse = {
  status: KronosForecastStatus;
  symbol: string;
  as_of: string;
  observed_through: string | null;
  model: string;
  frequency: "1d";
  lookback_bars: number;
  horizon_bars: number;
  sample_count: number;
  summary: {
    median_return_pct: string;
    upper_return_pct: string;
    lower_return_pct: string;
    path_dispersion_pct: string;
    downside_probability_pct: string;
  } | null;
  points: Array<{
    trade_date: string;
    median_close: string;
    lower_close: string;
    upper_close: string;
  }>;
  reasons: string[];
  sources: string[];
  warnings: string[];
};

export type QuantForecastLoader = (
  symbol: string,
  asOf?: string,
  horizon?: number,
) => Promise<KronosForecastResponse>;

export type QuantStrategyCandidate = {
  symbol: string;
  name: string;
  model: string;
  strategy_score: string;
  regime_match: string;
  stock_score: string;
  trigger_score: string;
  rr_score: string;
  risk_penalty: string;
  status: "alert" | "watch" | "reject" | "pending_trigger";
  trigger_confirmed: boolean;
  position: string;
  planned_position: string;
  vote_consensus?: string;
  vote_position?: string;
  signal_votes?: Array<{ signal: string; vote: -1 | 0 | 1; evidence_value: string }>;
  evidence_coverage_percent: string;
  buy_triggers: string[];
  invalidation_rules: string[];
  risk_flags: string[];
  missing_evidence: string[];
  alert_gate?: {
    eligible: boolean;
    checks: Array<{
      key: "regime_match" | "strategy_score" | "trigger_confirmed" | "risk_penalty" | "evidence_coverage" | "hard_risk";
      label: string;
      passed: boolean;
      detail: string;
    }>;
    blockers: string[];
  };
  factor_as_of: string;
  sources: string[];
};

export type CandidateSelectionFunnel = {
  stages: Array<{
    key: "universe" | "history_ready" | "factor_ready" | "liquidity_ready" | "ranked" | "trigger_confirmed" | "final_candidates";
    label: string;
    count: number;
  }>;
  exclusion_reasons: Record<string, number>;
  completeness: "complete" | "partial" | "unavailable";
  blockers: string[];
};

export type QuantRegimeMetrics = {
  up_ratio: string | null;
  zt_ratio: string | null;
  dt_ratio: string | null;
  median_ret: string | null;
  amt_heat: string | null;
  strong_close_ratio: string | null;
  weak_close_ratio: string | null;
  limit_fail_ratio: string | null;
  panic_ratio: string | null;
  amp_ratio: string | null;
  net_positive_ratio: string | null;
  net_positive_ratio_coverage_percent?: string | null;
  large_amount_strong_close_ratio: string | null;
  factor_coverage_percent: string;
};

export type QuantStrategyDashboard = {
  status: "ready" | "partial" | "unavailable";
  as_of: string;
  observed_at: string;
  generated_at: string;
  market_observed_at: string;
  data_age_seconds: number;
  refresh_mode: "live" | "delayed" | "postclose" | "stale";
  refresh_state?: "ready" | "pending" | "failed";
  snapshot_at?: string | null;
  refresh_started_at?: string | null;
  refresh_finished_at?: string | null;
  snapshot_source?: string;
  next_refresh_at: string;
  candidate_scan_at: string | null;
  candidate_scan_age_seconds: number | null;
  candidate_scan_cached: boolean;
  candidate_scan_state: "ready" | "pending" | "failed";
  candidate_scan_started_at: string | null;
  candidate_scan_error: string | null;
  candidate_scan_phase: "loading_history" | "computing_factors" | "ranking" | "ready" | "failed";
  candidate_scan_processed: number | null;
  candidate_scan_total: number | null;
  trigger_evidence_at: string | null;
  trigger_evidence_age_seconds: number | null;
  trigger_evidence_cached: boolean;
  formula_version: "a-share-short-strategy-v2.0";
  input_snapshot_ids?: string[];
  metrics: QuantRegimeMetrics;
  regime: {
    regime: "情绪主升" | "指数权重进攻" | "轮动震荡" | "冰点修复" | "高位退潮" | "缩量混沌" | null;
    emotion_score: string | null;
    risk_score: string | null;
    previous_risk_score?: string | null;
    heat_score: string | null;
    rotation_score: string | null;
    coverage_percent: string;
    market_coef: string;
    suitable_strategies: string[];
    avoid_strategies: string[];
    reasons: string[];
    missing_factors: string[];
    rule_matched: boolean;
    quality: "ready" | "partial" | "stale" | "unavailable";
    formula_version: string;
  };
  strategy_models: Array<{
    name: string;
    applicable_regimes: string[];
    selected: boolean;
    defensive: boolean;
  }>;
  candidate_funnel?: CandidateSelectionFunnel;
  evidence_ledger?: EvidenceLedgerEntry[];
  field_evidence?: FieldEvidence[];
  candidates: QuantStrategyCandidate[];
  discipline: string;
  missing_data: string[];
  warnings: string[];
  sources: string[];
};

export type QuantStrategyLoader = (limit?: number) => Promise<QuantStrategyDashboard>;

export type QuantShadowOutcome = {
  decision_id: string;
  horizon: number;
  status: "pending" | "ready" | "unavailable";
  evaluated_trade_date: string | null;
  return_percent: string | null;
  mfe_percent: string | null;
  mae_percent: string | null;
  invalidation_state: "not_observed" | "observed" | "unavailable";
  evaluated_at: string | null;
  limitation: string | null;
};

export type QuantShadowDecisionRecord = {
  decision_id: string;
  as_of: string;
  symbol: string;
  formula_version: string;
  candidate_status: string;
  market_regime?: string | null;
  strategy_score: string;
  reference_price: string | null;
  frozen_at: string;
  outcomes: QuantShadowOutcome[];
  lifecycle?: string[];
  input_snapshot_ids?: string[];
};

export type QuantShadowLoader = (limit?: number) => Promise<QuantShadowDecisionRecord[]>;

export type QuantShadowAnalytics = {
  status: "ready" | "partial" | "insufficient";
  horizon: 1 | 3 | 5 | 10 | 20;
  mature_sample_count: number;
  pending_sample_count: number;
  hit_rate_percent: string | null;
  average_return_percent: string | null;
  average_mfe_percent: string | null;
  average_mae_percent: string | null;
  brier_score: string | null;
  buckets: Array<{
    label: string;
    score_min: number;
    score_max: number;
    sample_count: number;
    average_score: string | null;
    hit_rate_percent: string | null;
    average_return_percent: string | null;
    average_mfe_percent: string | null;
    average_mae_percent: string | null;
    calibration_gap_percent: string | null;
    status: "ready" | "insufficient";
  }>;
  regime_performance?: Array<{
    regime: "情绪主升" | "指数权重进攻" | "轮动震荡" | "冰点修复" | "高位退潮" | "缩量混沌";
    sample_count: number;
    hit_rate_percent: string | null;
    average_return_percent: string | null;
    expected_value_percent: string | null;
    profit_loss_ratio: string | null;
    max_consecutive_losses: number;
    max_drawdown_percent: string | null;
    sharpe_ratio: string | null;
  }>;
  drift: {
    status: "stable" | "warning" | "drift" | "insufficient";
    recent_sample_count: number;
    baseline_sample_count: number;
    recent_hit_rate_percent: string | null;
    baseline_hit_rate_percent: string | null;
    recent_average_return_percent: string | null;
    baseline_average_return_percent: string | null;
    reasons: string[];
  };
  generated_at: string;
  limitations: string[];
};

export type QuantShadowAnalyticsLoader = (horizon?: 1 | 3 | 5 | 10 | 20) => Promise<QuantShadowAnalytics>;

export type DecisionJournalAction = "observe" | "no_trade" | "buy" | "sell";

export type DecisionJournalEntry = {
  entry_id: string;
  decision_id: string | null;
  symbol: string;
  action: DecisionJournalAction;
  recorded_at: string;
  actual_price: string | null;
  quantity: string | null;
  note: string;
  market_regime?: string | null;
  screener_session_id?: string | null;
  snapshot_hash?: string | null;
  observation_reason?: string | null;
  risks?: string[];
  invalidation_conditions?: string[];
  created_at: string;
};

export type DecisionJournalCreate = Omit<DecisionJournalEntry, "entry_id" | "created_at">;
export type DecisionJournalLoader = (limit?: number) => Promise<DecisionJournalEntry[]>;
export type DecisionJournalCreator = (request: DecisionJournalCreate) => Promise<DecisionJournalEntry>;

export type TdxFormulaResponse = {
  status: "ready" | "unavailable";
  points: Array<{
    symbol: string;
    name: string | null;
    formula_name: string;
    values: Record<string, string>;
    fetched_at: string;
    source: string;
  }>;
  fetched_at: string | null;
  source: string;
  detail: string | null;
};

export type TdxFormulaLoader = (
  formulaName: string,
  stockCodes: string[],
) => Promise<TdxFormulaResponse>;

export type SignalMetric = {
  key: "vol" | "score" | "win_rate" | "odds" | "risk" | "position" | "ev";
  label: string;
  value: string;
  detail: string;
  barValue: number;
  tone: "positive" | "warning" | "danger" | "muted";
};
import type { EvidenceLedgerEntry } from "../../shared/evidence/EvidenceLedger";
