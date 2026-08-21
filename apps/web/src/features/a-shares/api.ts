import type { AShareDiagnosis, CandidateBoard, CandidateScoreBoard } from "./types";
import { apiClient } from "../../shared/apiClient";


async function request<T>(path: string): Promise<T> {
  return apiClient.get<T>(path, { context: "A 股研究" });
}

export function loadAShareCandidates(asOf?: string, limit = 20): Promise<CandidateBoard> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (asOf) query.set("as_of", asOf);
  return request(`/api/v1/a-shares/candidates?${query}`);
}

export function loadAShareCandidateScores(
  symbols: string[], horizon: "short_term" | "swing" = "short_term",
): Promise<CandidateScoreBoard> {
  const query = new URLSearchParams({ horizon });
  symbols.forEach((symbol) => query.append("symbols", symbol));
  return request(`/api/v1/a-shares/candidate-scores?${query}`);
}

export function loadAShareDiagnosis(symbol: string, asOf?: string): Promise<AShareDiagnosis> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request(`/api/v1/a-shares/${symbol}/diagnosis${query}`);
}
