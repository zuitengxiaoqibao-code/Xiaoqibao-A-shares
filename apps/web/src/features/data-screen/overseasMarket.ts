import { apiClient } from "../../shared/apiClient";
import { requestLedger } from "../../shared/performance/requestLedger";

export type OverseasInstrumentQuote = {
  symbol: string;
  name: string;
  ticker: string;
  region: "index" | "mag7";
  price: string;
  change: string;
  change_percent: string;
  observed_at: string;
  trading_state: "盘中" | "最近收盘" | "休市中";
  quality: "ready" | "stale" | "unavailable";
};

export type OverseasMarketSnapshot = {
  indices: OverseasInstrumentQuote[];
  mag7: OverseasInstrumentQuote[];
  observed_at: string;
  source: string;
  source_trading_date: string | null;
  trading_label: string;
  quality: "ready" | "stale" | "unavailable";
  reason: string | null;
};

export const loadOverseasMarket = (signal?: AbortSignal) => requestLedger.run("overview:overseas", async () => {
  return apiClient.get<OverseasMarketSnapshot>("/api/v1/market/overseas", { signal, context: "美股风向标" });
}, { domain: "overview" });
