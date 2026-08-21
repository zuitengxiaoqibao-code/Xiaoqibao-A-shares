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
  DataImportPreview,
  DataImportTask,
} from "./types";

async function settingsRequest(path: string, init?: RequestInit): Promise<AISettingsView> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(`AI 设置请求失败 (${response.status})`);
  return response.json();
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
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `本地行情设置请求失败 (${response.status})`);
  }
  return response.json() as Promise<LocalSourceSettingsView>;
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

export const syncAShareUniverse = async (): Promise<AShareUniverseSyncResult> => {
  const response = await fetch("/api/v1/a-shares/universe/sync", { method: "POST" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: { message?: string } } | null;
    throw new Error(payload?.detail?.message ?? `A 股证券目录同步失败 (${response.status})`);
  }
  return response.json() as Promise<AShareUniverseSyncResult>;
};

export const loadSourceHealth = async (): Promise<SourceHealthResponse> => {
  const response = await fetch("/api/v1/operations/source-health");
  if (!response.ok) throw new Error(`数据源健康读取失败 (${response.status})`);
  return response.json() as Promise<SourceHealthResponse>;
};

export const inspectDataImport = async (file: File): Promise<DataImportPreview> => {
  const body = new FormData(); body.append("file", file);
  const response = await fetch("/api/data-import/inspect", { method: "POST", body });
  if (!response.ok) throw new Error("数据文件预览失败");
  return response.json() as Promise<DataImportPreview>;
};

export const ingestDataImport = async (file: File, mapping: Record<string, string>): Promise<DataImportTask> => {
  const body = new FormData(); body.append("file", file); body.append("mapping", JSON.stringify(mapping));
  const response = await fetch("/api/data-import/ingest", { method: "POST", body });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "数据导入失败");
  }
  return response.json() as Promise<DataImportTask>;
};

async function historySyncRequest(path: string, init?: RequestInit): Promise<HistorySyncJob> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `全市场日线同步失败 (${response.status})`);
  }
  return response.json() as Promise<HistorySyncJob>;
}

export const loadHistorySync = async (): Promise<HistorySyncJob | null> => {
  const response = await fetch("/api/v1/a-shares/history-sync/current");
  if (!response.ok) throw new Error(`日线同步进度读取失败 (${response.status})`);
  return response.json() as Promise<HistorySyncJob | null>;
};

export const loadHistoryCoverage = async (): Promise<HistoryCoverageSummary> => {
  const response = await fetch("/api/v1/a-shares/history-sync/coverage");
  if (!response.ok) throw new Error(`日线覆盖率读取失败 (${response.status})`);
  return response.json() as Promise<HistoryCoverageSummary>;
};

export const loadHistoryRepairCenter = async (): Promise<HistoryRepairCenter> => {
  const response = await fetch("/api/v1/a-shares/history-sync/repair-center?limit=100");
  if (!response.ok) throw new Error(`日线修复中心读取失败 (${response.status})`);
  return response.json() as Promise<HistoryRepairCenter>;
};

export const loadHistoryRepairAudits = async (): Promise<HistoryRepairAudit[]> => {
  const response = await fetch("/api/v1/a-shares/history-sync/repair-audits?limit=20");
  if (!response.ok) throw new Error(`日线修复审计读取失败 (${response.status})`);
  return response.json() as Promise<HistoryRepairAudit[]>;
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
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `官方日线补齐请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
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
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `通达信本地导入失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
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
