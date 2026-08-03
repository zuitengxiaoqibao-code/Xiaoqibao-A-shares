import { friendlyError } from "../../shared/friendlyError";
import type { MarketSentimentResponse, MarketSentimentSnapshot } from "./types";


async function request<T>(url: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, init);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        body.detail?.message
        ?? body.detail?.code
        ?? `市场情绪请求失败 (${response.status})`,
      );
    }
    return response.json();
  } catch (error) {
    throw new Error(friendlyError(error, "A 股市场情绪"));
  }
}

export const loadCurrentMarketSentiment = () =>
  request<MarketSentimentResponse>("/api/v1/a-shares/market-sentiment/current");

export const refreshMarketSentiment = () =>
  request<MarketSentimentSnapshot>("/api/v1/a-shares/market-sentiment/refresh", {
    method: "POST",
  });
