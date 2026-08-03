import type { CompanyResearchResponse } from "./types";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";

export async function loadCompanyResearch(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<CompanyResearchResponse> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchJsonWithProgress(
    `/api/v1/a-shares/${encodeURIComponent(symbol)}/company-research${query}`,
    { signal },
    onProgress,
    (status) => `公司研究请求失败 (${status})`,
  );
}
