import type { ResearchCard } from "./types";
import { apiClient } from "../../shared/apiClient";

export async function loadSnapshot(symbol: string): Promise<ResearchCard> {
  return apiClient.get<ResearchCard>(`/api/v1/a-shares/${symbol}/snapshot`, { context: "行情快照" });
}
