import type { PortfolioPositionInput, PortfolioRiskAnalyzer, PortfolioRiskResponse, WatchlistRiskLoader } from "./types";


async function responseJson(response: Response): Promise<PortfolioRiskResponse> {
  if (!response.ok) throw new Error(`组合风险请求失败 (${response.status})`);
  return response.json() as Promise<PortfolioRiskResponse>;
}


export async function loadPortfolioRisk(): Promise<PortfolioRiskResponse> {
  return responseJson(await fetch("/api/v1/a-shares/portfolio-risk"));
}


export async function savePortfolioPosition(position: PortfolioPositionInput): Promise<PortfolioRiskResponse> {
  return responseJson(await fetch(`/api/v1/a-shares/portfolio-risk/positions/${encodeURIComponent(position.symbol)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shares: position.shares, cost_price: position.cost_price }),
  }));
}


export async function removePortfolioPosition(symbol: string): Promise<PortfolioRiskResponse> {
  return responseJson(await fetch(`/api/v1/a-shares/portfolio-risk/positions/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  }));
}

export const analyzePortfolioRisk: PortfolioRiskAnalyzer = async (request) => {
  return responseJson(await fetch("/api/v1/a-shares/portfolio-risk", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }));
};

export const loadWatchlistRisk: WatchlistRiskLoader = async (symbols, asOf) => {
  const response = await fetch("/api/v1/a-shares/watchlist-risk", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbols, ...(asOf ? { as_of: asOf } : {}) }) });
  if (!response.ok) throw new Error(`观察篮子风险请求失败 (${response.status})`);
  return response.json();
};
