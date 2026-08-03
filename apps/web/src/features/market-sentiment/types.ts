export type SentimentPhase = "intraday" | "postclose";
export type SentimentQuality = "ready" | "partial" | "unavailable";
export type SentimentFreshness = "current" | "stale";
export type SentimentBand = "panic" | "cold" | "neutral" | "active" | "overheated" | "unavailable";
export type SentimentComponentName =
  | "volatility" | "activity" | "price_strength" | "risk_appetite"
  | "breadth" | "limit_ecology" | "money_making" | "sector_diffusion"
  | "style_risk_preference"
  | "liquidity" | "hotspot";

export type SentimentComponent = {
  name: SentimentComponentName;
  score: string | null;
  weight: string;
  coverage_percent: string;
  metrics: Record<string, string | number | null>;
  evidence_ids: string[];
};

export type MarketSentimentSnapshot = {
  snapshot_id: string;
  previous_snapshot_id: string | null;
  trading_date: string;
  phase: SentimentPhase;
  quality: SentimentQuality;
  freshness: SentimentFreshness;
  score: string | null;
  band: SentimentBand;
  coverage_percent: string;
  components: SentimentComponent[];
  drivers: string[];
  risks: string[];
  beginner_guidance: string;
  observed_at: string;
  generated_at: string;
  source_snapshot_ids: string[];
  formula_version: string;
};

export type MarketSentimentResponse = {
  trading_date: string;
  phase: "premarket" | SentimentPhase;
  display_mode: "current" | "previous_close_baseline" | "unavailable";
  current: MarketSentimentSnapshot | null;
  previous_close: MarketSentimentSnapshot | null;
  trajectory: MarketSentimentSnapshot[];
};
