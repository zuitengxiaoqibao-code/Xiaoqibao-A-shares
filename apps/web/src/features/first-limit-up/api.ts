import type { FirstLimitUpBoard } from "./types";


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `首次涨停请求失败 (${response.status})`);
  }
  return response.json();
}

export function loadFirstLimitUp(asOf?: string): Promise<FirstLimitUpBoard> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/v1/a-shares/first-limit-up${query}`);
}

export function refreshFirstLimitUp(asOf?: string): Promise<FirstLimitUpBoard> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/v1/a-shares/first-limit-up/refresh${query}`, { method: "POST" });
}
