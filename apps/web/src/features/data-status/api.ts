import type { SyncReport } from "./types";
import { apiClient } from "../../shared/apiClient";

export async function syncHistory(symbol: string, limit = 250): Promise<SyncReport> {
  return apiClient.post<SyncReport>(
    `/api/v1/a-shares/${symbol}/history/sync?limit=${limit}`,
    undefined,
    { context: "历史数据同步" },
  );
}
