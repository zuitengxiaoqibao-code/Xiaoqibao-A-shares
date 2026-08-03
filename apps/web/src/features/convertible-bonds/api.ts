import type { BondCandidates, BondDashboard, BondDiagnosis, BondDiagnosisBatch } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `请求失败 (${response.status})`);
  }
  return response.json();
}

export const loadBondDashboard = () => request<BondDashboard>("/api/v1/convertible-bonds/dashboard");
export const loadBondDiagnosis = (code: string) => request<BondDiagnosis>(`/api/v1/convertible-bonds/${code}/diagnosis`);
export async function loadCachedBondDiagnosis(code: string): Promise<BondDiagnosis | null> {
  const response = await fetch(`/api/v1/convertible-bonds/${code}/diagnosis/cached`);
  if (response.status === 404) return null;
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail ?? `请求失败 (${response.status})`);
  }
  return response.json();
}
export const loadBondCandidates = (filters?: Record<string, string>) => {
  const query = new URLSearchParams(Object.entries(filters ?? {}).filter(([, value]) => value !== ""));
  return request<BondCandidates>(`/api/v1/convertible-bonds/candidates${query.size ? `?${query}` : ""}`);
};
export const diagnoseBondBatch = (limit = 6) => request<BondDiagnosisBatch>(`/api/v1/convertible-bonds/diagnose-discovered?limit=${limit}`, { method: "POST" });
