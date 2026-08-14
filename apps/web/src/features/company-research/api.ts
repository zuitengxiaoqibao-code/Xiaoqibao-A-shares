import type { CompanyResearchAITaskSnapshot, CompanyResearchResponse, CompanyResearchTaskSnapshot } from "./types";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
import { requestLedger } from "../../shared/performance/requestLedger";

export function loadCompanyResearch(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<CompanyResearchResponse> {
  return requestLedger.run(`company-research:${symbol}:${asOf ?? "latest"}`, async () => {
    const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
    const started = await fetchJsonWithProgress<CompanyResearchTaskSnapshot>(
      `/api/v1/a-shares/${encodeURIComponent(symbol)}/company-research/tasks${query}`,
      { signal, method: "POST" },
      undefined,
      (status) => `公司研究任务创建失败 (${status})`,
    );
    let snapshot = started;
    while (snapshot.progress.status === "queued" || snapshot.progress.status === "running") {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      onProgress?.({
        percent: snapshot.progress.percent ?? 1,
        stage: snapshot.progress.status === "queued" ? "connecting" : "receiving",
        detail: snapshot.progress.detail ?? snapshot.progress.stage,
        mode: snapshot.progress.total ? "measured" : "estimated",
      });
      await new Promise((resolve) => window.setTimeout(resolve, 180));
      snapshot = await fetchJsonWithProgress<CompanyResearchTaskSnapshot>(
        `/api/v1/a-shares/company-research/tasks/${encodeURIComponent(snapshot.progress.task_id)}`,
        { signal },
        undefined,
        (status) => `公司研究进度读取失败 (${status})`,
      );
    }
    if (snapshot.progress.status !== "succeeded" || !snapshot.result) {
      throw new Error(snapshot.progress.detail ?? snapshot.progress.error ?? "公司研究任务失败");
    }
    onProgress?.({ percent: 100, stage: "complete", detail: "六个研究区块已核验", mode: "verified" });
    return snapshot.result;
  }, { domain: "company-research" });
}

export async function loadCompanyResearchAI(snapshotId: string, signal?: AbortSignal): Promise<CompanyResearchAITaskSnapshot> {
  const started = await fetchJsonWithProgress<CompanyResearchAITaskSnapshot>(
    `/api/v1/a-shares/company-research/versions/${encodeURIComponent(snapshotId)}/ai/tasks`,
    { signal, method: "POST" }, undefined,
    (status) => `公司研究 AI 任务创建失败 (${status})`,
  );
  let snapshot = started;
  while (snapshot.progress.status === "queued" || snapshot.progress.status === "running") {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    snapshot = await fetchJsonWithProgress<CompanyResearchAITaskSnapshot>(
      `/api/v1/a-shares/company-research/ai/tasks/${encodeURIComponent(snapshot.progress.task_id)}`,
      { signal }, undefined,
      (status) => `公司研究 AI 进度读取失败 (${status})`,
    );
  }
  return snapshot;
}

export type CompanyResearchComparison = {
  status: "ready" | "partial" | "unavailable";
  as_of: string;
  generated_at: string;
  companies: Array<{
    symbol: string;
    name: string;
    status: "ready" | "partial" | "unavailable";
    evidence_coverage_percent: string;
    final_score: string | null;
    business_model: string | null;
    industry_space: string | null;
    latest_revenue_yoy_percent: string | null;
    latest_net_profit_yoy_percent: string | null;
    latest_operating_cash_flow: string | null;
    pe_ttm: string | null;
    pb: string | null;
    catalysts: string[];
    risks: string[];
    limitations: string[];
  }>;
  sources: string[];
  limitations: string[];
};

export async function loadCompanyResearchComparison(symbols: string[], asOf?: string): Promise<CompanyResearchComparison> {
  const response = await requestLedger.run(`company-research-compare:${[...symbols].sort().join(",")}:${asOf ?? "latest"}`, async () => fetch("/api/v1/a-shares/company-research/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols: [...new Set(symbols)].slice(0, 5), ...(asOf ? { as_of: asOf } : {}) }),
  }), { domain: "company-research" });
  if (!response.ok) throw new Error(`公司研究比较请求失败 (${response.status})`);
  return response.json() as Promise<CompanyResearchComparison>;
}
