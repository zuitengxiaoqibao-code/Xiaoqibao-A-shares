export type BacktestStrategy = "sma_cross" | "momentum_breakout" | "low_volume_pullback";
export type BacktestRequest = {
  strategy: BacktestStrategy;
  fast_window?: number;
  slow_window?: number;
  lookback_window?: number;
  exit_window?: number;
  volume_window?: number;
  volume_ratio?: number;
  stop_loss_percent?: number;
  take_profit_percent?: number;
  initial_cash?: number;
  commission_rate?: number;
  slippage_rate?: number;
};
export type BacktestTrade = { side: "buy" | "sell"; signal_date: string; trade_date: string; price: string; shares: number; gross_amount: string; fees: string };
export type BacktestEquityPoint = { trade_date: string; equity: string; cash?: string; shares?: number; market_value?: string };
export type BacktestResult = {
  symbol: string;
  strategy: string;
  initial_cash: string;
  ending_equity: string;
  total_return: string;
  max_drawdown: string;
  total_cost: string;
  metrics: {
    annualized_return: string;
    annualized_volatility: string;
    sharpe_ratio: string | null;
    calmar_ratio: string | null;
    win_rate: string;
    profit_loss_ratio: string | null;
    turnover_rate: string;
    closed_trade_count: number;
  };
  segments: Array<{ name: "train" | "validation" | "out_of_sample"; start_date: string; end_date: string; bar_count: number; starting_equity: string; ending_equity: string; total_return: string; max_drawdown: string }>;
  market_regimes: Array<{ name: "bull" | "bear" | "sideways"; bar_count: number; total_return: string }>;
  trades: BacktestTrade[];
  equity_curve: BacktestEquityPoint[];
  warnings: string[];
};

export type BacktestRunner = (symbol: string, requestOrSignal?: BacktestRequest | AbortSignal, signal?: AbortSignal) => Promise<BacktestResult>;
