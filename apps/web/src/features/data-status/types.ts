export type SyncAttempt = {
  source: string;
  status: "ready" | "error" | "empty";
  message: string;
};

export type SyncReport = {
  symbol: string;
  state: "ready" | "error" | "empty";
  written_rows: number;
  source: string;
  parquet_path: string | null;
  started_at: string;
  finished_at: string;
  message: string;
  attempts: SyncAttempt[];
};

export type DataStatusState =
  | { kind: "idle" }
  | { kind: "syncing" }
  | { kind: "ready"; report: SyncReport }
  | { kind: "error"; message: string };
