import type { StockPreparation } from "../stock-cockpit/types";
export type {
  SpeechSettings,
  SpeechSettingsLoader,
  SpeechSettingsSaver,
  SpeechSynthesizer,
  SpeechVoiceLoader,
} from "../speech/types";

export type AISettingsView = {
  configured: boolean;
  state?: "unconfigured" | "configured_unverified" | "connected" | "connection_failed" | "timeout" | "rate_limited" | "model_not_found";
  message?: string;
  base_url: string | null;
  model: string | null;
  api_key_hint: string | null;
};

export type AISettingsInput = { base_url: string; model: string; api_key: string };
export type PreparationLoader = (symbol: string, signal?: AbortSignal) => Promise<StockPreparation>;
export type AShareUniverseSyncResult = { status: "ready"; count: number; observed_at: string; source: string };
export type AShareUniverseSyncLoader = () => Promise<AShareUniverseSyncResult>;
export type SourceHealthStatus = "ready" | "degraded" | "unavailable";
export type SourceHealthItem = {
  source: string;
  operation: string;
  target: string;
  status: SourceHealthStatus;
  attempts: number;
  successes: number;
  failures: number;
  empty_responses: number;
  success_rate: number;
  average_latency_ms: number;
  latest_latency_ms: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error_code: string | null;
  latest_trade_date: string | null;
  field_count: number | null;
  row_count: number | null;
  validation: string | null;
};
export type SourceHealthResponse = { generated_at: string; window_size: number; sources: SourceHealthItem[] };
export type SourceHealthLoader = () => Promise<SourceHealthResponse>;
export type DataImportPreview = {
  path: string;
  format: string;
  columns: string[];
  row_count: number;
  preview_rows: Array<Record<string, unknown>>;
  error: string | null;
};
export type DataImportTask = {
  task_id: string;
  state: string;
  stage: string;
  progress: number;
  processed: number;
  total: number;
  quarantined_rows: number;
  quality_status: "ready" | "partial" | "stale" | "unavailable";
  error_message: string | null;
  quarantine_reasons?: string[];
};
export type DataImportInspector = (file: File) => Promise<DataImportPreview>;
export type DataImportIngestor = (file: File, mapping: Record<string, string>) => Promise<DataImportTask>;
export type HistorySyncState = "pending" | "running" | "paused" | "completed" | "failed";
export type HistorySyncJob = {
  job_id: string;
  mode: "backfill" | "incremental";
  target_date: string;
  state: HistorySyncState;
  pause_requested: boolean;
  total_count: number;
  ready_count: number;
  failed_count: number;
  skipped_count: number;
  pending_count: number;
  tdx_ready_count: number;
  baidu_ready_count: number;
  created_at: string;
  updated_at: string;
};
export type HistoryCoverageSummary = {
  target_date: string;
  universe_count: number;
  backfill_complete_count: number;
  eligible_count: number;
  target_date_count: number;
  target_date_coverage_percent?: number | null;
  dominant_trade_date: string | null;
  dominant_date_count: number;
  dominant_date_coverage_percent: number | null;
  coverage_percent: number | null;
  fragmented_latest_count: number;
  missing_history_count: number;
  quality: "ready" | "partial" | "stale" | "unavailable" | "error";
  blockers: string[];
  lag_trading_days?: number;
  is_fresh?: boolean;
};
export type HistoryCoverageGap = {
  symbol: string;
  bar_count: number;
  latest_trade_date: string | null;
  gap_kind: "missing_history" | "insufficient_history" | "behind_dominant_date";
};
export type HistoryRepairCenter = {
  coverage: HistoryCoverageSummary;
  current_job: HistorySyncJob | null;
  gaps: HistoryCoverageGap[];
  total_gap_count: number;
  offset: number;
  limit: number;
};
export type HistoryRepairAudit = {
  audit_id: string;
  job_id: string;
  mode: "backfill" | "incremental";
  target_date: string;
  started_at: string;
  completed_at: string;
  source: string;
  gap_count_before: number;
  coverage_before_percent: number | null;
  written_rows: number;
  ready_count: number;
  failed_count: number;
  skipped_count: number;
  coverage_after_percent: number | null;
  final_state: "pending" | "running" | "paused" | "completed" | "failed";
  failure_reasons: string[];
};
export type HistorySyncLoader = () => Promise<HistorySyncJob | null>;
export type HistoryCoverageLoader = () => Promise<HistoryCoverageSummary>;
export type HistoryRepairCenterLoader = () => Promise<HistoryRepairCenter>;
export type HistoryRepairAuditLoader = () => Promise<HistoryRepairAudit[]>;
export type HistorySyncStarter = () => Promise<HistorySyncJob>;
export type HistorySyncController = (jobId: string) => Promise<HistorySyncJob>;
export type OfficialTdxPackageInfo = { size_label: string; modified_at: string };
export type HistorySupplementJob = {
  job_id: string; state: "pending" | "running" | "completed" | "partial" | "failed";
  stage: "queued" | "checking_metadata" | "checking_cache" | "validating_cache" | "downloading" | "validating" | "extracting" | "scanning" | "importing" | "online_repair" | "final_review" | "completed" | "partial" | "failed";
  percent: number; source_url: string; package_modified_at?: string | null;
  package_size_label?: string | null; downloaded_bytes: number; total_bytes?: number | null;
  package_sha256?: string | null; package_path?: string | null;
  day_file_count: number; supported_file_count: number; latest_trade_date?: string | null;
  imported_rows: number; replaced_rows: number; skipped_rows: number; failed_files: number;
  validated_bytes: number; total_validation_bytes: number; extracted_files: number; total_extract_files: number;
  processed_files: number; total_import_files: number; online_total: number; online_ready: number;
  online_failed: number; online_pending: number; final_target_date?: string | null;
  final_dominant_trade_date?: string | null; final_dominant_coverage_percent?: number | null;
  final_history_coverage_percent?: number | null; remaining_gap_count: number; final_quality?: string | null;
  final_blockers: string[]; result_detail?: string | null;
  source_attempts: Array<{ source: string; state: string; detail: string; observed_at: string }>;
  error_stage?: string | null; error_detail?: string | null;
  created_at: string; updated_at: string; finished_at?: string | null;
};
export type OfficialTdxInfoLoader = () => Promise<OfficialTdxPackageInfo>;
export type HistorySupplementLoader = () => Promise<HistorySupplementJob | null>;
export type HistorySupplementStarter = () => Promise<HistorySupplementJob>;
export type TdxImportError = { path: string; code: string; detail: string };
export type TdxImportJob = {
  job_id: string; state: "pending" | "running" | "paused" | "completed" | "failed";
  stage: string; paths: string[]; total_files: number; processed_files: number;
  imported_rows: number; replaced_rows: number; skipped_rows: number; failed_files: number;
  current_file: string | null; latest_trade_date: string | null; percent: number;
  errors: TdxImportError[]; created_at: string; updated_at: string; finished_at: string | null;
};
export type TdxImportScan = {
  scanned_paths: string[]; day_files: number; archive_files: number; readable_files: number;
  latest_trade_date: string | null; errors: TdxImportError[];
};
export type TdxImportLoader = () => Promise<TdxImportJob | null>;
export type TdxImportStarter = (paths?: string[]) => Promise<TdxImportJob>;
export type TdxImportScanner = (paths?: string[]) => Promise<TdxImportScan>;
export type TdxImportController = (jobId: string) => Promise<TdxImportJob>;
export type AISettingsLoader = (signal?: AbortSignal) => Promise<AISettingsView>;
export type AISettingsSaver = (input: AISettingsInput, signal?: AbortSignal) => Promise<AISettingsView>;
export type AISettingsDeleter = (signal?: AbortSignal) => Promise<AISettingsView>;
export type LocalSourceSettings = {
  auto_discovery: boolean;
  tdx_install_paths: string[];
  tdx_archive_paths?: string[];
  ths_install_paths: string[];
  tdx_rpc_enabled: boolean;
  tdx_rpc_url: string | null;
};
export type LocalTerminalStatus = {
  vendor: "tdx" | "ths";
  install_path: string;
  data_path: string | null;
  origin: "manual" | "process" | "registry" | "common";
  status: "ready" | "detected_only" | "invalid";
  sh_daily_count: number;
  sz_daily_count: number;
  latest_modified_at: string | null;
  professional_data_status?: "ready" | "detected_only" | "unavailable";
  professional_data_files?: string[];
  selection_eligible?: boolean;
  selection_note?: string | null;
};
export type LocalSourceSettingsView = {
  settings_state: "ready" | "default" | "invalid_local_config";
  settings: LocalSourceSettings;
  scanned_at: string;
  terminals: LocalTerminalStatus[];
  active_tdx_vipdoc: string | null;
  tdx_rpc: TdxRpcStatus;
  restart_required: boolean;
};
export type TdxRpcCapability = {
  key: string;
  label: string;
  method: string;
  status: "ready" | "unavailable" | "disabled";
  semantic_status?: "not_applicable" | "detected_only" | "verified";
  reason_code?: string;
  detail: string;
};
export type TdxRpcStatus = {
  status: "ready" | "partial" | "unavailable" | "disabled";
  reachable: boolean;
  endpoint: string | null;
  observed_at: string;
  capabilities: TdxRpcCapability[];
  direct_python: TdxDirectPythonStatus;
  client: TdxClientStatus;
  recovery_steps?: TdxRecoveryStep[];
};
export type TdxRecoveryStep = {
  key: string;
  label: string;
  status: "ready" | "detected_only" | "unavailable" | "disabled";
  detail: string;
};
export type TdxDirectPythonStatus = {
  status: "detected_only" | "unavailable";
  detail: string;
  module_path: string | null;
};
export type TdxClientStatus = {
  status: "running" | "not_running" | "unknown";
  executable_path: string | null;
  detail: string;
};
export type LocalSourceSettingsLoader = (signal?: AbortSignal) => Promise<LocalSourceSettingsView>;
export type LocalSourceSettingsWriter = (
  input: LocalSourceSettings,
  signal?: AbortSignal,
) => Promise<LocalSourceSettingsView>;
export type DataAsset = "a_share" | "convertible_bond";
export type ComplianceStatus = {
  policy_state: string;
  sources: Array<Record<string, string | null>>;
  features: Array<{ feature: string; allowed: boolean; blocked_reasons: string[] }>;
};
export type ComplianceLoader = (asset?: DataAsset) => Promise<ComplianceStatus>;
export type ComplianceAction = (
  source: string,
  action: "authorize" | "revoke" | "acknowledge",
  permissionReference?: string,
  asset?: DataAsset,
) => Promise<unknown>;
