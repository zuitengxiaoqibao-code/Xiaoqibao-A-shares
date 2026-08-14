export type PortfolioPositionInput = { symbol: string; shares: string; cost_price: string };
export type PortfolioRiskRequest = { positions: PortfolioPositionInput[]; as_of?: string };

export type PortfolioRiskResponse = {
  status: "ready" | "partial" | "unavailable";
  as_of: string;
  observed_at: string;
  total_market_value: string | null;
  total_cost: string | null;
  total_pnl: string | null;
  total_pnl_percent: string | null;
  hhi: string | null;
  average_correlation: string | null;
  market_regime: string | null;
  market_position_cap_percent: string | null;
  positions: Array<{
    symbol: string; shares: string; cost_price: string; current_price: string | null;
    market_value: string | null; pnl: string | null; pnl_percent: string | null;
    weight_percent: string | null; industry: string | null; status: "ready" | "unavailable";
    limitations: string[];
  }>;
  industries: Array<{ industry: string; market_value: string; weight_percent: string; symbols: string[] }>;
  high_correlation_pairs: Array<{ left_symbol: string; right_symbol: string; correlation: string; overlap_days: number }>;
  stress_scenarios: Array<{
    key: "market_down_2" | "largest_industry_down_5" | "correlated_pair_down_7";
    label: string; shock_percent: string; estimated_loss: string | null;
    status: "ready" | "unavailable"; detail: string;
  }>;
  warnings: string[];
  sources: string[];
};

export type PortfolioRiskAnalyzer = (request: PortfolioRiskRequest) => Promise<PortfolioRiskResponse>;
export type PortfolioRiskLoader = () => Promise<PortfolioRiskResponse>;
export type PortfolioPositionSaver = (position: PortfolioPositionInput) => Promise<PortfolioRiskResponse>;
export type PortfolioPositionRemover = (symbol: string) => Promise<PortfolioRiskResponse>;
