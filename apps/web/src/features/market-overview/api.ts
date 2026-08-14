import type { MarketIntervalReviewLoader, MarketIntervalReviewSnapshot, MarketOverviewLoader, MarketOverviewResponse } from "./types";
import { coalescedFetch } from "../../shared/coalescedFetch";
import { requestLedger } from "../../shared/performance/requestLedger";

export const loadMarketOverview: MarketOverviewLoader = (signal) => requestLedger.run("overview:latest", async () => {
  let response: Response;
  try {
    response = await coalescedFetch("/api/v1/a-shares/market-overview", { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("信息总览数据暂不可用，请检查本地 API 后重试。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail?.message
      ?? body.detail?.code
      ?? body.detail
      ?? `信息总览请求失败 (${response.status})`,
    );
  }
  return response.json() as Promise<MarketOverviewResponse>;
}, { domain: "overview" });

export const loadMarketIntervalReview: MarketIntervalReviewLoader = async (startDate, endDate, signal) => {
  let response: Response;
  try {
    response = await coalescedFetch(`/api/v1/a-shares/market-overview/interval?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("区间统计数据暂不可用，请检查本地日线数据源。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail?.code ?? body.detail ?? `区间统计请求失败 (${response.status})`);
  }
  return response.json() as Promise<MarketIntervalReviewSnapshot>;
};
