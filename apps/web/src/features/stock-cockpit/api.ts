import type { InstrumentSearchResponse, StockCockpitSnapshot, StockPreparation } from "./types";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `A 股请求失败 (${response.status})`);
  }
  return response.json();
}

export function searchAShareInstruments(query: string): Promise<InstrumentSearchResponse> {
  return request(`/api/v1/a-shares/search?q=${encodeURIComponent(query)}&limit=10`);
}

export function loadStockCockpit(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<StockCockpitSnapshot> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchJsonWithProgress(
    `/api/v1/a-shares/${symbol}/cockpit${query}`,
    { signal },
    onProgress,
    (status) => `A 股请求失败 (${status})`,
  );
}

export function loadStockCockpitAI(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<StockCockpitSnapshot> {
  const query = new URLSearchParams({ include_ai: "true" });
  if (asOf) query.set("as_of", asOf);
  return fetchJsonWithProgress(
    `/api/v1/a-shares/${symbol}/cockpit?${query}`,
    { signal },
    onProgress,
    (status) => `A 股请求失败 (${status})`,
  );
}

export function prepareStockData(symbol: string, signal?: AbortSignal): Promise<StockPreparation> {
  return fetch(`/api/v1/a-shares/${symbol}/prepare`, { method: "POST", signal }).then(async (response) => {
    if (!response.ok) throw new Error(`数据补齐失败 (${response.status})`);
    return response.json();
  });
}
