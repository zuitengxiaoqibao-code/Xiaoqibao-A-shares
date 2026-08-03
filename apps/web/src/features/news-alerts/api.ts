import type { BreakingNewsAlertResponse } from "./types";


export async function loadBreakingNewsAlerts(
  symbol?: string | null,
  signal?: AbortSignal,
  limit = 30,
): Promise<BreakingNewsAlertResponse> {
  const params = new URLSearchParams();
  if (symbol) params.set("symbol", symbol);
  params.set("limit", String(limit));
  const response = await fetch(`/api/v1/news/alerts?${params.toString()}`, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `新闻提醒请求失败 (${response.status})`);
  }
  return response.json();
}
