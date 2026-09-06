export type StockTimelineBar = {
  symbol: string;
  trade_date: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
  amount: string;
  source: string;
};

export type StockTimelineEvent = {
  event_id: string;
  event_type: "market_news";
  occurred_at: string;
  mapped_trade_date: string | null;
  label: string;
  headline: string;
  direction: "positive" | "negative" | "neutral" | "uncertain";
  confidence: string | null;
  themes: string[];
  industries: string[];
  publisher: string;
  source_url: string;
  association_confidence: string;
  association_kind: "direct" | "context" | "theme" | "macro";
  association_reasons: string[];
  verification_state: "verified" | "multi_source_confirmed" | "pending" | "unverified";
  source_count: number;
  urgency: "breaking" | "tracking" | "normal";
  review_state: "verified";
  category: "policy_macro" | "industry_sector" | "company_announcement" | "earnings_financial" | "capital_dragon_tiger" | "price_volume_anomaly" | "risk_event" | "rumor_unverified";
  strength: "high" | "medium" | "low" | "unknown";
  credibility: "multi_source_verified" | "verified" | "pending" | "rejected";
  duration: "intraday" | "multi_day" | "long_term" | "unknown";
  price_reflection: "not_reflected" | "partially_reflected" | "fully_reflected" | "unknown";
  follow_up_indicators: string[];
};

export type StockTimelineResponse = {
  symbol: string;
  as_of: string;
  cutoff: string;
  status: "ready" | "unavailable";
  bars: StockTimelineBar[];
  events: StockTimelineEvent[];
  sources: string[];
  warnings: string[];
  intraday_status?: "ready" | "waiting" | "unavailable";
  intraday_points?: StockTimelineMinutePoint[];
  intraday_sources?: string[];
  intraday_warnings?: string[];
};

export type StockTimelineMinutePoint = {
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

export type StockTimelineLoader = (
  symbol: string,
  asOf?: string,
  signal?: AbortSignal,
) => Promise<StockTimelineResponse>;
