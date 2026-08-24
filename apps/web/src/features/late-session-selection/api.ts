import { apiClient } from "../../shared/apiClient";
import { fetchJsonWithProgress, type LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
import type { LateSessionAIAnalysis, LateSessionRuleSettings, LateSessionSelectionResponse } from "./types";

export async function loadLateSessionSelection(settings?: LateSessionRuleSettings, onProgress?: LoadProgressCallback): Promise<LateSessionSelectionResponse> {
  return fetchJsonWithProgress(
    settings ? "/api/v1/a-shares/late-session-selection/filter" : "/api/v1/a-shares/late-session-selection",
    settings ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings) } : undefined,
    onProgress,
    (status) => `尾盘选股请求失败 (${status})`,
  );
}

export async function loadLateSessionAIAnalysis(selection: LateSessionSelectionResponse): Promise<LateSessionAIAnalysis> {
  return apiClient.post<LateSessionAIAnalysis>(
    "/api/v1/a-shares/late-session-selection/ai-analysis",
    selection,
    { context: "尾盘选股 AI 分析" },
  );
}
