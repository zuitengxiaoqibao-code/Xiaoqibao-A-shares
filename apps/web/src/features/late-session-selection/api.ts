import { coalescedFetch } from "../../shared/coalescedFetch";
import type { LateSessionRuleSettings, LateSessionSelectionResponse } from "./types";

export async function loadLateSessionSelection(settings?: LateSessionRuleSettings): Promise<LateSessionSelectionResponse> {
  const response = await coalescedFetch(
    settings ? "/api/v1/a-shares/late-session-selection/filter" : "/api/v1/a-shares/late-session-selection",
    settings ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings) } : undefined,
  );
  if (!response.ok) throw new Error(`尾盘选股请求失败 (${response.status})`);
  return response.json() as Promise<LateSessionSelectionResponse>;
}
