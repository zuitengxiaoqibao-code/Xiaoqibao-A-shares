import type { PortfolioPositionInput, PortfolioRiskAnalyzer, PortfolioRiskResponse, WatchlistRiskLoader } from "./types";
import { apiClient } from "../../shared/apiClient";


export async function loadPortfolioRisk(): Promise<PortfolioRiskResponse> {
  return apiClient.get("/api/v1/a-shares/portfolio-risk", { context: "组合风险" });
}


export async function savePortfolioPosition(position: PortfolioPositionInput): Promise<PortfolioRiskResponse> {
  return (await apiClient.request<PortfolioRiskResponse>(`/api/v1/a-shares/portfolio-risk/positions/${encodeURIComponent(position.symbol)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shares: position.shares, cost_price: position.cost_price }),
    context: "组合持仓保存",
  })).data;
}


export async function removePortfolioPosition(symbol: string): Promise<PortfolioRiskResponse> {
  return (await apiClient.request<PortfolioRiskResponse>(`/api/v1/a-shares/portfolio-risk/positions/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
    context: "组合持仓删除",
  })).data;
}

export const analyzePortfolioRisk: PortfolioRiskAnalyzer = async (request) => {
  return apiClient.post("/api/v1/a-shares/portfolio-risk", request, { context: "组合风险分析" });
};

export const loadWatchlistRisk: WatchlistRiskLoader = async (symbols, asOf) => {
  return apiClient.post("/api/v1/a-shares/watchlist-risk", { symbols, ...(asOf ? { as_of: asOf } : {}) }, { context: "观察篮子风险" });
};
