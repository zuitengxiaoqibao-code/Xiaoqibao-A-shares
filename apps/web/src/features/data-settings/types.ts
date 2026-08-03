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
};
export type HistorySyncLoader = () => Promise<HistorySyncJob | null>;
export type HistoryCoverageLoader = () => Promise<HistoryCoverageSummary>;
export type HistorySyncStarter = () => Promise<HistorySyncJob>;
export type HistorySyncController = (jobId: string) => Promise<HistorySyncJob>;
export type AISettingsLoader = (signal?: AbortSignal) => Promise<AISettingsView>;
export type AISettingsSaver = (input: AISettingsInput, signal?: AbortSignal) => Promise<AISettingsView>;
export type AISettingsDeleter = (signal?: AbortSignal) => Promise<AISettingsView>;
export type LocalSourceSettings = {
  auto_discovery: boolean;
  tdx_install_paths: string[];
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
};
export type LocalSourceSettingsView = {
  settings_state: "ready" | "default" | "invalid_local_config";
  settings: LocalSourceSettings;
  scanned_at: string;
  terminals: LocalTerminalStatus[];
  active_tdx_vipdoc: string | null;
  restart_required: boolean;
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
