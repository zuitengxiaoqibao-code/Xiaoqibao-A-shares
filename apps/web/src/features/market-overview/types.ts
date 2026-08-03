export type OverviewQuality = "ready" | "partial" | "stale" | "unavailable";

export type OverviewSentiment = {
  score: string | null;
  band: string;
  coverage_percent: string;
  quality: OverviewQuality;
  observed_at: string;
};

export type OverviewIndexQuote = {
  instrument: string;
  name: string;
  value: string;
  change: string;
  change_percent: string;
  observed_at: string;
  source: string;
  quality: OverviewQuality;
};

export type OverviewMinutePoint = {
  observed_at: string;
  price: string;
  volume: string;
  amount: string;
};

export type OverviewAnomaly = {
  anomaly_id: string;
  occurred_at: string;
  label: string;
  headline: string;
  direction: "positive" | "negative" | "neutral" | "uncertain";
  themes: string[];
  symbols: string[];
};

export type OverviewLiveFeedItem = {
  event_id: string;
  occurred_at: string;
  headline: string;
  summary: string;
  themes: string[];
  symbols: string[];
  source: string;
  review_state: string;
};

export type OverviewSector = {
  sector_id: string;
  name: string;
  change_percent: string | null;
  amount_yi: string | null;
  limit_up_count: number;
  rising_count: number;
  falling_count: number;
  stock_count: number;
};

export type OverviewSectorStock = {
  symbol: string;
  name: string;
  change_percent: string | null;
  amount_yi: string | null;
  market_cap_yi: string | null;
  first_limit_time: string | null;
  position: string;
  quality: OverviewQuality;
};

export type OverviewFeatureStock = {
  symbol: string;
  name: string;
  price: string;
  previous_close: string;
  open: string;
  high: string;
  low: string;
  volume: string;
  amount_yi: string;
  change_percent: string;
  state: "limit_up" | "broken_limit_up" | "limit_down" | "active";
  observed_at: string;
  source: string;
  quality: OverviewQuality;
};

export type MarketReviewStock = {
  symbol: string;
  name: string;
  trade_date: string;
  category: "consecutive_limit_up" | "first_limit_up" | "volume_breakout" | "previous_high_breakout" | "low_position_volume";
  close: string;
  change_percent: string;
  amount_yi: string;
  source: string;
  board_count: number | null;
  limit_statistics: string | null;
  turnover_rate: string | null;
  seal_amount_yi: string | null;
  failed_limit_count: number | null;
  first_seal_time: string | null;
  volume_multiple: string | null;
  reference_high: string | null;
  window_days: number | null;
  range_position_percent: string | null;
};

export type DragonTigerSeat = {
  symbol: string;
  trade_date: string;
  seat_name: string;
  direction: "buy" | "sell" | "mixed";
  buy_amount_yi: string;
  sell_amount_yi: string;
  net_amount_yi: string;
  source: string;
};

export type DragonTigerStock = {
  symbol: string;
  name: string;
  trade_date: string;
  reason: string;
  change_percent: string | null;
  buy_amount_yi: string;
  sell_amount_yi: string;
  net_amount_yi: string;
  seats: DragonTigerSeat[];
  source: string;
};

export type MarketReviewSnapshot = {
  as_of: string;
  observed_at: string;
  latest_trade_date: string | null;
  source: string;
  quality: OverviewQuality;
  universe_count: number;
  history_ready_count: number;
  consecutive_limit_up: MarketReviewStock[];
  first_limit_up: MarketReviewStock[];
  volume_breakouts: MarketReviewStock[];
  previous_high_breakouts: MarketReviewStock[];
  low_position_volume: MarketReviewStock[];
  dragon_tiger: DragonTigerStock[];
  warnings: string[];
  formula_version: string;
};

export type OverviewRegimeMetrics = {
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

export type OverviewRegimeAssessment = {
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
  quality: OverviewQuality;
  formula_version: string;
};

export type MarketOverviewResponse = {
  status: "ready" | "partial" | "unavailable";
  as_of: string;
  observed_at: string;
  sentiment: OverviewSentiment;
  breadth: {
    rising_count: number;
    falling_count: number;
    flat_count: number;
    valid_count: number;
  };
  limit_ecology: {
    limit_up_count: number;
    limit_down_count: number;
    broken_limit_up_count: number;
    seal_rate_percent: string | null;
  };
  liquidity: {
    total_amount_yi: string | null;
    baseline_amount_yi: string | null;
    relative_amount: string | null;
  };
  market_data: {
    source: string;
    quality: OverviewQuality;
    observed_at: string | null;
    quote_count: number;
    universe_count: number;
  };
  indices: OverviewIndexQuote[];
  minute_series: OverviewMinutePoint[];
  anomalies: OverviewAnomaly[];
  live_feed: OverviewLiveFeedItem[];
  sectors: OverviewSector[];
  sector_stocks: Record<string, OverviewSectorStock[]>;
  market_stocks: OverviewFeatureStock[];
  review?: MarketReviewSnapshot | null;
  regime_metrics?: OverviewRegimeMetrics;
  regime?: OverviewRegimeAssessment;
  warnings: string[];
  sources: string[];
};

export type MarketOverviewLoader = (signal?: AbortSignal) => Promise<MarketOverviewResponse>;
