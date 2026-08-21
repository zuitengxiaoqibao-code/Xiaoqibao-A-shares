import type { BondCandidates, BondDashboard, BondDiagnosis, BondDiagnosisBatch } from "./types";
import { apiClient } from "../../shared/apiClient";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "可转债" })).data;
}

export const loadBondDashboard = () => request<BondDashboard>("/api/v1/convertible-bonds/dashboard");
export const loadBondDiagnosis = (code: string) => request<BondDiagnosis>(`/api/v1/convertible-bonds/${code}/diagnosis`);
export async function loadCachedBondDiagnosis(code: string): Promise<BondDiagnosis | null> {
  return apiClient.getOptional<BondDiagnosis>(
    `/api/v1/convertible-bonds/${code}/diagnosis/cached`,
    { context: "可转债缓存诊断" },
  );
}
export const loadBondCandidates = (filters?: Record<string, string>) => {
  const query = new URLSearchParams(Object.entries(filters ?? {}).filter(([, value]) => value !== ""));
  return request<BondCandidates>(`/api/v1/convertible-bonds/candidates${query.size ? `?${query}` : ""}`);
};
export const diagnoseBondBatch = (limit = 6) => request<BondDiagnosisBatch>(`/api/v1/convertible-bonds/diagnose-discovered?limit=${limit}`, { method: "POST" });
