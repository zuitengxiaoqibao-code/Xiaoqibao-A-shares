import { coalescedFetch } from "../../shared/coalescedFetch";
import type { LateSessionSelectionResponse } from "./types";

export async function loadLateSessionSelection(): Promise<LateSessionSelectionResponse> {
  const response = await coalescedFetch("/api/v1/a-shares/late-session-selection");
  if (!response.ok) throw new Error(`尾盘选股请求失败 (${response.status})`);
  return response.json() as Promise<LateSessionSelectionResponse>;
}
