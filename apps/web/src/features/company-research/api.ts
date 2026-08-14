import type { CompanyResearchAITaskSnapshot, CompanyResearchResponse, CompanyResearchTaskSnapshot } from "./types";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";

export async function loadCompanyResearch(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<CompanyResearchResponse> {
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
