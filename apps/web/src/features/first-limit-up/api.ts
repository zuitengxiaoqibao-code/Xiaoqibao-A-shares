import type { FirstLimitUpBoard } from "./types";
import { apiClient } from "../../shared/apiClient";


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "首次涨停" })).data;
}

export function loadFirstLimitUp(asOf?: string): Promise<FirstLimitUpBoard> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/v1/a-shares/first-limit-up${query}`);
}

export function refreshFirstLimitUp(asOf?: string): Promise<FirstLimitUpBoard> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/v1/a-shares/first-limit-up/refresh${query}`, { method: "POST" });
}
