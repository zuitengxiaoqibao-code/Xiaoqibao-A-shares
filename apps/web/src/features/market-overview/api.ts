import type { MarketIntervalReviewLoader, MarketIntervalReviewSnapshot, MarketOverviewLoader, MarketOverviewResponse } from "./types";
import { apiClient } from "../../shared/apiClient";
import { requestLedger } from "../../shared/performance/requestLedger";

export const loadMarketOverview: MarketOverviewLoader = (signal) => requestLedger.run("overview:latest", async () => {
  return apiClient.get<MarketOverviewResponse>("/api/v1/a-shares/market-overview", { signal, context: "信息总览" });
}, { domain: "overview" });

export const loadMarketIntervalReview: MarketIntervalReviewLoader = async (startDate, endDate, signal) => {
  return apiClient.get<MarketIntervalReviewSnapshot>(
    `/api/v1/a-shares/market-overview/interval?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    { signal, context: "区间统计" },
  );
};
