import type { StockTimelineResponse } from "./types";


export async function loadStockTimeline(
  symbol: string,
  asOf?: string,
  signal?: AbortSignal,
): Promise<StockTimelineResponse> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const response = await fetch(`/api/v1/a-shares/${symbol}/timeline${query}`, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `事件 K 线请求失败 (${response.status})`);
  }
  return response.json();
}
