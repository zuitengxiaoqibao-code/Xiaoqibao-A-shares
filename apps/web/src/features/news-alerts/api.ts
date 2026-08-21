import type { BreakingNewsAlertResponse } from "./types";
import { apiClient } from "../../shared/apiClient";


export async function loadBreakingNewsAlerts(
  symbol?: string | null,
  signal?: AbortSignal,
  limit = 30,
): Promise<BreakingNewsAlertResponse> {
  const params = new URLSearchParams();
  if (symbol) params.set("symbol", symbol);
  params.set("limit", String(limit));
  return apiClient.get<BreakingNewsAlertResponse>(
    `/api/v1/news/alerts?${params.toString()}`,
    { signal, context: "新闻提醒" },
  );
}
