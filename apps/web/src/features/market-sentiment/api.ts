import { apiClient } from "../../shared/apiClient";
import type { MarketSentimentResponse, MarketSentimentSnapshot } from "./types";


async function request<T>(url: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(url, { ...init, context: "A 股市场情绪" })).data;
}

export const loadCurrentMarketSentiment = () =>
  request<MarketSentimentResponse>("/api/v1/a-shares/market-sentiment/current");

export const refreshMarketSentiment = () =>
  request<MarketSentimentSnapshot>("/api/v1/a-shares/market-sentiment/refresh", {
    method: "POST",
  });
