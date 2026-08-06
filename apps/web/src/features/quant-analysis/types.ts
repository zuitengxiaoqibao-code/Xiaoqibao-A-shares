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
  evidence_coverage_percent: string;
  buy_triggers: string[];
  invalidation_rules: string[];
  risk_flags: string[];
  missing_evidence: string[];
  factor_as_of: string;
  sources: string[];
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
  next_refresh_at: string;
  candidate_scan_at: string | null;
  candidate_scan_age_seconds: number | null;
  candidate_scan_cached: boolean;
  candidate_scan_state: "ready" | "pending" | "failed";
  candidate_scan_started_at: string | null;
  candidate_scan_error: string | null;
  trigger_evidence_at: string | null;
  trigger_evidence_age_seconds: number | null;
  trigger_evidence_cached: boolean;
  formula_version: "a-share-short-strategy-v2.0";
  metrics: QuantRegimeMetrics;
  regime: {
    regime: "情绪主升" | "指数权重进攻" | "轮动震荡" | "冰点修复" | "高位退潮" | "缩量混沌" | null;
    emotion_score: string | null;
    risk_score: string | null;
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
  candidates: QuantStrategyCandidate[];
  discipline: string;
  missing_data: string[];
  warnings: string[];
  sources: string[];
};

export type QuantStrategyLoader = (limit?: number) => Promise<QuantStrategyDashboard>;

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
