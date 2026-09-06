import type { CompanyResearchAITaskSnapshot, CompanyResearchResponse, CompanyResearchTaskSnapshot } from "./types";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
import { requestLedger } from "../../shared/performance/requestLedger";
import { updateTaskActivity } from "../../shared/taskActivity";
import { apiClient } from "../../shared/apiClient";

function isResearchCache(value: unknown): value is CompanyResearchResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CompanyResearchResponse>;
  return typeof candidate.symbol === "string"
    && typeof candidate.name === "string"
    && typeof candidate.as_of === "string"
    && Array.isArray(candidate.dimensions)
    && typeof candidate.financial_history === "object"
    && candidate.financial_history !== null
    && typeof candidate.valuation === "object"
    && candidate.valuation !== null;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function loadCompanyResearch(symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback): Promise<CompanyResearchResponse> {
  return requestLedger.run(`company-research:${symbol}:${asOf ?? "latest"}`, async () => {
    const taskId = `company-research:${symbol}:${asOf ?? "latest"}`;
    updateTaskActivity({ id: taskId, label: `公司研究 ${symbol}`, stage: "正在建立研究任务", state: "running", percent: 1 });
    const startedAt = Date.now();
    let lastChangedAt = startedAt;
    let lastSignature = "";
    try {
      const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
      // Serve an existing verified snapshot before starting heavyweight
      // enrichment. A cache miss falls through to the progress task below.
      onProgress?.({ percent: 8, stage: "connecting", detail: "正在检查本地公司研究缓存", mode: "estimated" });
      let cached: CompanyResearchResponse | null = null;
      try {
        cached = await apiClient.getOptional<CompanyResearchResponse>(
          `/api/v1/a-shares/${encodeURIComponent(symbol)}/company-research${query}${query ? "&" : "?"}cache_only=true`,
          // The cache is an optional first-screen optimization. Never let a
          // locked or unavailable cache prevent the real research task from
          // starting; the task has its own progress and error reporting.
          { signal, context: "公司研究缓存", timeoutMs: 5_000 },
        );
      } catch (error) {
        if (signal?.aborted || isAbortError(error)) throw error;
        updateTaskActivity({
          id: taskId,
          label: `公司研究 ${symbol}`,
          stage: "缓存检查失败，继续建立研究任务",
          state: "running",
          percent: 8,
          detail: error instanceof Error ? error.message : "缓存暂不可用",
        });
        onProgress?.({ percent: 8, stage: "connecting", detail: "本地缓存暂不可用，继续连接实时研究任务", mode: "estimated" });
      }
      if (isResearchCache(cached)) {
        updateTaskActivity({ id: taskId, label: `公司研究 ${symbol}`, stage: "已展示缓存，后台刷新最新数据", state: "succeeded", percent: 100 });
        onProgress?.({ percent: 100, stage: "complete", detail: "已展示有效研究缓存，后台正在刷新", mode: "verified" });
        return cached;
      }
      let snapshot = await fetchJsonWithProgress<CompanyResearchTaskSnapshot>(
        `/api/v1/a-shares/${encodeURIComponent(symbol)}/company-research/tasks${query}`,
        { signal, method: "POST" }, undefined,
        (status) => `公司研究任务创建失败 (${status})`,
      );
      while (snapshot.progress.status === "queued" || snapshot.progress.status === "running") {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        const now = Date.now();
        const signature = [snapshot.progress.stage, snapshot.progress.processed, snapshot.progress.percent, snapshot.progress.detail].join("|");
        if (signature !== lastSignature) {
          lastSignature = signature;
          lastChangedAt = now;
        } else if (now - lastChangedAt > 60_000) {
          throw new Error(`公司研究停滞：${snapshot.progress.detail ?? snapshot.progress.stage}超过60秒无进展`);
        }
        if (now - startedAt > 180_000) throw new Error("公司研究超时：超过180秒仍未完成，请检查数据源");
        onProgress?.({
          percent: snapshot.progress.percent ?? 1,
          stage: snapshot.progress.status === "queued" ? "connecting" : "receiving",
          detail: snapshot.progress.detail ?? snapshot.progress.stage,
          mode: snapshot.progress.total ? "measured" : "estimated",
        });
        updateTaskActivity({ id: taskId, label: `公司研究 ${symbol}`, stage: snapshot.progress.detail ?? "正在读取研究数据", state: "running", percent: snapshot.progress.percent, detail: snapshot.progress.stage });
        await new Promise((resolve) => window.setTimeout(resolve, 180));
        snapshot = await fetchJsonWithProgress<CompanyResearchTaskSnapshot>(
          `/api/v1/a-shares/company-research/tasks/${encodeURIComponent(snapshot.progress.task_id)}`,
          { signal }, undefined,
          (status) => `公司研究进度读取失败 (${status})`,
        );
      }
      if (snapshot.progress.status !== "succeeded" || !snapshot.result) {
        throw new Error(snapshot.progress.detail ?? snapshot.progress.error ?? "公司研究任务失败");
      }
      updateTaskActivity({ id: taskId, label: `公司研究 ${symbol}`, stage: "公司研究已完成", state: "succeeded", percent: 100 });
      onProgress?.({ percent: 100, stage: "complete", detail: "六个研究区块已核验", mode: "verified" });
      return snapshot.result;
    } catch (error) {
      const aborted = error instanceof DOMException && error.name === "AbortError";
      updateTaskActivity({
        id: taskId,
        label: `公司研究 ${symbol}`,
        stage: aborted ? "公司研究已取消" : "公司研究失败",
        state: "failed",
        error: aborted ? "已取消本次请求" : error instanceof Error ? error.message : "网络或数据解析失败",
      });
      throw error;
    }
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
  return requestLedger.run(
    `company-research-compare:${[...symbols].sort().join(",")}:${asOf ?? "latest"}`,
    () => apiClient.post<CompanyResearchComparison>(
      "/api/v1/a-shares/company-research/compare",
      { symbols: [...new Set(symbols)].slice(0, 5), ...(asOf ? { as_of: asOf } : {}) },
      { context: "公司研究比较" },
    ),
    { domain: "company-research" },
  );
}
