import { apiClient } from "./apiClient";

export type MarketSession = {
  status: "ready" | "unavailable";
  trading_date: string;
  observed_at: string;
  is_trading_day: boolean | null;
  phase: "closed" | "pre_open" | "intraday" | "lunch_break" | "post_close" | "unknown";
};

export async function loadMarketStage(): Promise<string> {
  try {
    const session = await apiClient.get<MarketSession>("/api/v1/operations/market-session", {
      context: "交易状态", timeoutMs: 5_000,
    });
    if (session.status !== "ready" || session.phase === "unknown") return "状态未知";
    if (session.phase === "intraday") return "正在更新";
    if (session.phase === "lunch_break") return "已暂停";
    return "休市";
  } catch {
    return "状态未知";
  }
}
