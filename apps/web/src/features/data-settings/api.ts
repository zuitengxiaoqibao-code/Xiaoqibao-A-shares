import type {
  AISettingsInput,
  AISettingsView,
  AShareUniverseSyncResult,
  HistoryCoverageSummary,
  HistoryRepairCenter,
  HistoryRepairAudit,
  HistorySyncJob,
  HistorySupplementJob,
  OfficialTdxPackageInfo,
  LocalSourceSettings,
  LocalSourceSettingsView,
  SourceHealthResponse,
  TdxImportJob,
  TdxImportScan,
  TdxDirectoriesView,
  DataImportPreview,
  DataImportTask,
} from "./types";
import { apiClient } from "../../shared/apiClient";

async function settingsRequest(path: string, init?: RequestInit): Promise<AISettingsView> {
  return (await apiClient.request<AISettingsView>(path, { ...init, context: "AI 设置" })).data;
}

export const loadAISettings = (signal?: AbortSignal) => settingsRequest("/api/v1/settings/ai", { signal });
export const saveAISettings = (input: AISettingsInput, signal?: AbortSignal) => settingsRequest("/api/v1/settings/ai", {
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal,
});
export const deleteAISettings = (signal?: AbortSignal) => settingsRequest("/api/v1/settings/ai", { method: "DELETE", signal });

async function localSourceRequest(
  path: string,
  init?: RequestInit,
): Promise<LocalSourceSettingsView> {
  return (await apiClient.request<LocalSourceSettingsView>(path, { ...init, context: "本地行情设置" })).data;
}

export const loadLocalSourceSettings = (signal?: AbortSignal) => localSourceRequest(
  "/api/v1/settings/data-sources",
  { signal },
);
export const detectLocalSourceSettings = (input: LocalSourceSettings, signal?: AbortSignal) => localSourceRequest(
  "/api/v1/settings/data-sources/detect",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal },
);
export const saveLocalSourceSettings = (input: LocalSourceSettings, signal?: AbortSignal) => localSourceRequest(
  "/api/v1/settings/data-sources",
  { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal },
);

export const loadTdxDirectories = (signal?: AbortSignal) => apiClient.get<TdxDirectoriesView>(
  "/api/v1/settings/tdx-directories",
  { signal, context: "通达信目录评分" },
);
export const selectTdxDirectory = (root: string | null, signal?: AbortSignal) => apiClient.request<TdxDirectoriesView>(
  "/api/v1/settings/tdx-directories/select",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ root }), signal, context: "通达信主源选择" },
).then((response) => response.data);

export const syncAShareUniverse = async (): Promise<AShareUniverseSyncResult> => {
  return apiClient.post<AShareUniverseSyncResult>("/api/v1/a-shares/universe/sync", undefined, { context: "A 股证券目录同步" });
};

export const loadSourceHealth = async (): Promise<SourceHealthResponse> => {
  return apiClient.get<SourceHealthResponse>("/api/v1/operations/source-health", { context: "数据源健康" });
};

export const inspectDataImport = async (file: File): Promise<DataImportPreview> => {
  const body = new FormData(); body.append("file", file);
  return (await apiClient.request<DataImportPreview>("/api/data-import/inspect", { method: "POST", body, context: "数据文件预览" })).data;
};

export const ingestDataImport = async (file: File, mapping: Record<string, string>): Promise<DataImportTask> => {
  const body = new FormData(); body.append("file", file); body.append("mapping", JSON.stringify(mapping));
  return (await apiClient.request<DataImportTask>("/api/data-import/ingest", { method: "POST", body, context: "数据导入" })).data;
};

async function historySyncRequest(path: string, init?: RequestInit): Promise<HistorySyncJob> {
  return (await apiClient.request<HistorySyncJob>(path, { ...init, context: "全市场日线同步" })).data;
}

export const loadHistorySync = async (): Promise<HistorySyncJob | null> => {
  return apiClient.get<HistorySyncJob | null>("/api/v1/a-shares/history-sync/current", { context: "日线同步进度" });
};

export const loadHistoryCoverage = async (): Promise<HistoryCoverageSummary> => {
  return apiClient.get<HistoryCoverageSummary>("/api/v1/a-shares/history-sync/coverage", { context: "日线覆盖率" });
};

export const loadHistoryRepairCenter = async (): Promise<HistoryRepairCenter> => {
  return apiClient.get<HistoryRepairCenter>("/api/v1/a-shares/history-sync/repair-center?limit=100", { context: "日线修复中心" });
};

export const loadHistoryRepairAudits = async (): Promise<HistoryRepairAudit[]> => {
  return apiClient.get<HistoryRepairAudit[]>("/api/v1/a-shares/history-sync/repair-audits?limit=20", { context: "日线修复审计" });
};

export const startHistoryBackfill = () => historySyncRequest(
  "/api/v1/a-shares/history-sync/backfill",
  { method: "POST" },
);
export const pauseHistorySync = (jobId: string) => historySyncRequest(
  `/api/v1/a-shares/history-sync/${encodeURIComponent(jobId)}/pause`,
  { method: "POST" },
);
export const resumeHistorySync = (jobId: string) => historySyncRequest(
  `/api/v1/a-shares/history-sync/${encodeURIComponent(jobId)}/resume`,
  { method: "POST" },
);
export const retryFailedHistory = (jobId: string) => historySyncRequest(
  `/api/v1/a-shares/history-sync/${encodeURIComponent(jobId)}/retry-failed`,
  { method: "POST" },
);
export const restartCurrentHistory = () => historySyncRequest(
  "/api/v1/a-shares/history-sync/restart-current",
  { method: "POST" },
);

async function historySupplementRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "官方日线补齐" })).data;
}

export const loadOfficialTdxInfo = () => historySupplementRequest<OfficialTdxPackageInfo>(
  "/api/v1/a-shares/history-supplement/official-info",
);
export const loadHistorySupplement = () => historySupplementRequest<HistorySupplementJob | null>(
  "/api/v1/a-shares/history-supplement/current",
);
export const startOfficialTdxSupplement = () => historySupplementRequest<HistorySupplementJob>(
  "/api/v1/a-shares/history-supplement/official/start", { method: "POST" },
);

async function tdxImportRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "通达信本地导入" })).data;
}

export const scanTdxImport = (paths: string[] = []) => tdxImportRequest<TdxImportScan>(
  "/api/v1/a-shares/tdx-import/scan",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ paths }) },
);
export const startTdxImport = (paths: string[] = []) => tdxImportRequest<TdxImportJob>(
  "/api/v1/a-shares/tdx-import/start",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ paths }) },
);
export const loadTdxImport = () => tdxImportRequest<TdxImportJob | null>("/api/v1/a-shares/tdx-import/current");
export const pauseTdxImport = (jobId: string) => tdxImportRequest<TdxImportJob>(
  `/api/v1/a-shares/tdx-import/${encodeURIComponent(jobId)}/pause`, { method: "POST" },
);
export const resumeTdxImport = (jobId: string) => tdxImportRequest<TdxImportJob>(
  `/api/v1/a-shares/tdx-import/${encodeURIComponent(jobId)}/resume`, { method: "POST" },
);
